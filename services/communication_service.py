from database.connection import get_connection


def _role(cursor, user_id):
    cursor.execute('SELECT role FROM app_users WHERE id = %s', (user_id,))
    row = cursor.fetchone()
    if not row:
        raise PermissionError('Пользователь не найден.')
    return row[0]


def _access(cursor, request_id, user_id):
    role = _role(cursor, user_id)
    cursor.execute('SELECT owner_id FROM repair_requests WHERE id = %s', (request_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError('Заявка не найдена.')
    if role != 'technician' and row[0] != user_id:
        raise PermissionError('Нет доступа к этой заявке.')
    return role, row[0]


def send_message(request_id, sender_id, body):
    body = body.strip()
    if not body or len(body) > 4000:
        raise ValueError('Сообщение должно содержать от 1 до 4000 символов.')
    with get_connection() as connection:
        with connection.cursor() as cur:
            role, owner_id = _access(cur, request_id, sender_id)
            cur.execute('INSERT INTO request_messages(request_id,sender_id,body) VALUES (%s,%s,%s) RETURNING id', (request_id,sender_id,body))
            message_id = cur.fetchone()[0]
            if role == 'technician' and owner_id is not None and owner_id != sender_id:
                cur.execute('INSERT INTO request_notifications(user_id,request_id,kind,text) VALUES (%s,%s,%s,%s)', (owner_id,request_id,'message','Новое сообщение от ремонтника'))
            elif role == 'user':
                cur.execute("INSERT INTO request_notifications(user_id,request_id,kind,text) SELECT id,%s,'message','Новое сообщение от клиента' FROM app_users WHERE role='technician'", (request_id,))
            return message_id


def get_messages(request_id, user_id):
    with get_connection() as connection:
        with connection.cursor() as cur:
            _access(cur, request_id, user_id)
            cur.execute('''SELECT m.id,u.username,u.role,m.body,m.created_at
                FROM request_messages m JOIN app_users u ON u.id=m.sender_id
                WHERE m.request_id=%s ORDER BY m.id''', (request_id,))
            return cur.fetchall()


def get_notifications(user_id, limit=50):
    with get_connection() as connection:
        with connection.cursor() as cur:
            _role(cur, user_id)
            cur.execute('''SELECT id,request_id,kind,text,created_at,is_read
                FROM request_notifications WHERE user_id=%s ORDER BY id DESC LIMIT %s''', (user_id,min(max(int(limit),1),100)))
            return cur.fetchall()


def mark_notification_read(notification_id, user_id):
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute('UPDATE request_notifications SET is_read=TRUE WHERE id=%s AND user_id=%s', (notification_id,user_id))


def change_status_with_event(request_id, technician_id, new_status):
    from services.request_service import STATUS_NAMES, STATUS_VALUES
    new_status = STATUS_VALUES.get(new_status,new_status)
    if new_status not in STATUS_NAMES:
        raise ValueError('Неизвестный статус.')
    with get_connection() as connection:
        with connection.cursor() as cur:
            if _role(cur, technician_id) != 'technician':
                raise PermissionError('Статус может менять только ремонтник.')
            cur.execute('SELECT status,owner_id FROM repair_requests WHERE id=%s FOR UPDATE', (request_id,))
            row = cur.fetchone()
            if not row:
                return False
            old_status, owner_id = row
            if old_status != 'new' and new_status == 'new':
                raise ValueError('Нельзя вернуть заявку в статус «Новая».')
            if old_status == new_status:
                return True
            cur.execute('UPDATE repair_requests SET status=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s', (new_status,request_id))
            cur.execute('''INSERT INTO request_status_history(request_id,actor_id,old_status,new_status)
                VALUES (%s,%s,%s,%s)''', (request_id,technician_id,old_status,new_status))
            if owner_id is not None:
                label = f'Статус изменён: {STATUS_NAMES.get(old_status,old_status)} → {STATUS_NAMES[new_status]}'
                cur.execute('''INSERT INTO request_notifications(user_id,request_id,kind,text)
                    VALUES (%s,%s,%s,%s)''', (owner_id,request_id,'status',label))
            return True


def get_status_history(request_id,user_id):
    with get_connection() as connection:
        with connection.cursor() as cur:
            _access(cur,request_id,user_id)
            cur.execute('''SELECT u.username,h.old_status,h.new_status,h.created_at
                FROM request_status_history h JOIN app_users u ON u.id=h.actor_id
                WHERE h.request_id=%s ORDER BY h.id''', (request_id,))
            return cur.fetchall()
