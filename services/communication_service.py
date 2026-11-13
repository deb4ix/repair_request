"""Сообщения, события и уведомления. Запустите migration_communication.sql перед использованием."""
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
    if new_status in ('completed','pending_confirmation'):
        raise PermissionError('Для завершения используйте отчёт и подтверждение клиента.')
    with get_connection() as connection:
        with connection.cursor() as cur:
            if _role(cur, technician_id) != 'technician':
                raise PermissionError('Статус может менять только ремонтник.')
            cur.execute('SELECT status,owner_id FROM repair_requests WHERE id=%s FOR UPDATE', (request_id,))
            row = cur.fetchone()
            if not row:
                return False
            old_status, owner_id = row
            if old_status in ('completed','pending_confirmation','cancelled'):
                raise ValueError('Статус закрытой заявки нельзя изменить напрямую.')
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


# Вложения к сообщениям используют существующую таблицу request_attachments V3.
# Требуется migration_chat_attachments.sql.
from pathlib import Path as _Path
from io import BytesIO as _BytesIO
from PIL import Image as _Image, UnidentifiedImageError as _UnidentifiedImageError

_CHAT_TYPES = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png',
               '.webp':'image/webp','.mp4':'video/mp4','.pdf':'application/pdf',
               '.txt':'text/plain','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
_CHAT_IMAGE_LIMIT = 10 * 1024 * 1024
_CHAT_OTHER_LIMIT = 20 * 1024 * 1024


def _read_chat_file(path):
    file = _Path(path)
    ext = file.suffix.lower()
    if ext not in _CHAT_TYPES or not file.is_file():
        raise ValueError('Разрешены JPG, PNG, WEBP, MP4, PDF, TXT, DOCX.')
    size = file.stat().st_size
    limit = _CHAT_IMAGE_LIMIT if ext in ('.jpg','.jpeg','.png','.webp') else _CHAT_OTHER_LIMIT
    if size < 1 or size > limit:
        raise ValueError(f'{file.name}: максимальный размер {limit // 1048576} МБ.')
    data = file.read_bytes()
    if len(data) != size:
        raise ValueError('Файл изменился во время загрузки.')
    if ext in ('.jpg','.jpeg','.png','.webp'):
        try:
            with _Image.open(_BytesIO(data)) as img:
                fmt = img.format
                img.verify()
            expected = 'JPEG' if ext in ('.jpg','.jpeg') else ext[1:].upper()
            if fmt != expected:
                raise ValueError('Содержимое изображения не соответствует расширению.')
        except (_UnidentifiedImageError, OSError) as exc:
            raise ValueError('Некорректный файл изображения.') from exc
    elif ext == '.mp4' and (len(data) < 12 or data[4:8] != b'ftyp'):
        raise ValueError('Некорректный MP4.')
    elif ext == '.pdf' and not data.startswith(b'%PDF-'):
        raise ValueError('Некорректный PDF.')
    elif ext == '.docx' and not data.startswith(b'PK'):
        raise ValueError('Некорректный DOCX.')
    return file.name, _CHAT_TYPES[ext], data


def send_chat_message(request_id, sender_id, body='', paths=()):
    body = (body or '').strip()
    paths = list(paths)
    if len(body) > 4000 or (not body and not paths):
        raise ValueError('Введите сообщение или прикрепите файл (до 4000 символов).')
    if len(paths) > 5:
        raise ValueError('За раз можно прикрепить не более 5 файлов.')
    # Проверяем файлы до транзакции, чтобы не держать блокировки при чтении диска.
    files = [_read_chat_file(p) for p in paths]
    with get_connection() as connection:
        with connection.cursor() as cur:
            role, owner_id = _access(cur,request_id,sender_id)
            cur.execute('INSERT INTO request_messages(request_id,sender_id,body) VALUES (%s,%s,%s) RETURNING id',
                        (request_id,sender_id,body))
            message_id = cur.fetchone()[0]
            for filename,mime,data in files:
                cur.execute('''INSERT INTO request_attachments
                  (request_id,uploader_id,report_id,message_id,filename,mime_type,file_size,file_data)
                  VALUES (%s,%s,NULL,%s,%s,%s,%s,%s)''',
                  (request_id,sender_id,message_id,filename,mime,len(data),data))
            label = 'Новое сообщение с вложениями' if files else 'Новое сообщение'
            if role == 'technician' and owner_id is not None and owner_id != sender_id:
                cur.execute('''INSERT INTO request_notifications(user_id,request_id,kind,text)
                               VALUES (%s,%s,'message',%s)''',(owner_id,request_id,label+' от ремонтника'))
            elif role == 'user':
                cur.execute('''INSERT INTO request_notifications(user_id,request_id,kind,text)
                               SELECT id,%s,'message',%s FROM app_users WHERE role='technician' ''',
                            (request_id,label+' от клиента'))
            return message_id


def get_chat_attachments(request_id,user_id):
    with get_connection() as connection:
        with connection.cursor() as cur:
            _access(cur,request_id,user_id)
            cur.execute('''SELECT a.id,a.message_id,a.filename,a.mime_type,a.file_size
                           FROM request_attachments a WHERE a.request_id=%s
                           AND a.message_id IS NOT NULL ORDER BY a.id''',(request_id,))
            return cur.fetchall()


def download_chat_attachment(attachment_id,user_id):
    with get_connection() as connection:
        with connection.cursor() as cur:
            cur.execute('''SELECT request_id,filename,mime_type,file_data FROM request_attachments
                           WHERE id=%s AND message_id IS NOT NULL''',(attachment_id,))
            row=cur.fetchone()
            if not row:
                raise ValueError('Вложение не найдено.')
            _access(cur,row[0],user_id)
            return row[1],row[2],bytes(row[3])
