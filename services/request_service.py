
from pathlib import Path

from database.connection import get_connection


STATUS_NAMES = {
    "new": "Новая",
    "in_progress": "В работе",
    "completed": "Завершена",
    "cancelled": "Отменена",
}

STATUS_VALUES = {
    "Новая": "new",
    "В работе": "in_progress",
    "Завершена": "completed",
    "Отменена": "cancelled",
}


def get_all_requests(owner_id=None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            query = """
                SELECT id, title,
                    CASE status
                        WHEN 'new' THEN 'Новая'
                        WHEN 'in_progress' THEN 'В работе'
                        WHEN 'completed' THEN 'Завершена'
                        WHEN 'cancelled' THEN 'Отменена'
                        ELSE status
                    END AS status_name
                FROM repair_requests
            """
            if owner_id is not None:
                query += " WHERE owner_id = %s"
                cursor.execute(query + " ORDER BY id ASC;", (owner_id,))
            else:
                cursor.execute(query + " ORDER BY id ASC;")
            return cursor.fetchall()


def get_request_by_id(request_id: int, owner_id=None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    """
                    SELECT id, title, description, status, created_at, updated_at
                    FROM repair_requests WHERE id = %s;
                    """,
                    (request_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, title, description, status, created_at, updated_at
                    FROM repair_requests WHERE id = %s AND owner_id = %s;
                    """,
                    (request_id, owner_id),
                )
            request = cursor.fetchone()

    if request is None:
        return None

    return {
        "id": request[0],
        "title": request[1],
        "description": request[2],
        "status": request[3],
        "status_name": STATUS_NAMES.get(request[3], request[3]),
        "created_at": request[4],
        "updated_at": request[5],
    }


def update_request_status(request_id: int, new_status: str) -> bool:
    new_status = STATUS_VALUES.get(new_status, new_status)

    if new_status not in STATUS_NAMES:
        raise ValueError("Указан неизвестный статус заявки.")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE repair_requests
                SET
                    status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id;
                """,
                (new_status, request_id),
            )
            updated_request = cursor.fetchone()

    return updated_request is not None


def _sync_request_sequence(cursor):
    cursor.execute(
        """
        SELECT pg_get_serial_sequence(
            'repair_requests',
            'id'
        );
        """
    )
    result = cursor.fetchone()
    sequence_name = result[0] if result else None

    if sequence_name is not None:
        cursor.execute(
            """
            SELECT setval(
                %s,
                COALESCE(
                    (SELECT MAX(id) FROM repair_requests),
                    1
                ),
                EXISTS (
                    SELECT 1 FROM repair_requests
                )
            );
            """,
            (sequence_name,),
        )


def delete_request(request_id: int, owner_id=None) -> bool:
    """Удаляет заявку, не перенумеровывая остальные заявки."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    "DELETE FROM repair_requests WHERE id = %s RETURNING id;",
                    (request_id,),
                )
            else:
                cursor.execute(
                    """
                    DELETE FROM repair_requests
                    WHERE id = %s AND owner_id = %s
                    RETURNING id;
                    """,
                    (request_id, owner_id),
                )
            return cursor.fetchone() is not None


def create_request(title, description, photo_path=None, owner_id=None):
    title = title.strip()
    description = description.strip()

    if not title:
        raise ValueError("Введите название заявки.")

    if not description:
        raise ValueError("Введите описание заявки.")

    photo_data = None

    if photo_path:
        photo_file = Path(photo_path)

        if not photo_file.is_file():
            raise ValueError(
                "Выбранный файл фотографии не найден."
            )

        photo_data = photo_file.read_bytes()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO repair_requests (
                    title, description, photo_data, owner_id
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (title, description, photo_data, owner_id),
            )
            created_request_id = cursor.fetchone()[0]

    return created_request_id


def get_request_photo(request_id: int, owner_id=None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    "SELECT photo_data FROM repair_requests WHERE id = %s;",
                    (request_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT photo_data FROM repair_requests
                    WHERE id = %s AND owner_id = %s;
                    """,
                    (request_id, owner_id),
                )
            result = cursor.fetchone()

    if result is None:
        return None

    return result[0]


def update_request(
    request_id: int,
    title: str,
    description: str,
    photo_path=None,
    remove_photo: bool = False,
    owner_id=None,
) -> bool:
    title = title.strip()
    description = description.strip()

    if not title:
        raise ValueError("Введите название заявки.")
    if not description:
        raise ValueError("Введите описание заявки.")

    photo_data = None
    if photo_path:
        photo_file = Path(photo_path)
        if not photo_file.is_file():
            raise ValueError("Выбранный файл фотографии не найден.")
        photo_data = photo_file.read_bytes()

    owner_clause = " AND owner_id = %s" if owner_id is not None else ""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            if remove_photo:
                query = (
                    "UPDATE repair_requests SET title = %s, description = %s, "
                    "photo_data = NULL, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s" + owner_clause + " RETURNING id;"
                )
                params = (title, description, request_id)
            elif photo_path:
                query = (
                    "UPDATE repair_requests SET title = %s, description = %s, "
                    "photo_data = %s, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s" + owner_clause + " RETURNING id;"
                )
                params = (title, description, photo_data, request_id)
            else:
                query = (
                    "UPDATE repair_requests SET title = %s, description = %s, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s" + owner_clause + " RETURNING id;"
                )
                params = (title, description, request_id)

            if owner_id is not None:
                params += (owner_id,)

            cursor.execute(query, params)
            updated_request = cursor.fetchone()

    return updated_request is not None
