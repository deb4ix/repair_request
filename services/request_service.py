from database.connection import get_connection
from pathlib import Path

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


def get_all_requests():

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, status
                FROM repair_requests
                ORDER BY id DESC;
                """
            )

            rows = cursor.fetchall()

    return [
        (request_id, title, STATUS_NAMES.get(status, status))
        for request_id, title, status in rows
    ]


def get_request_by_id(request_id: int):

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    title,
                    description,
                    status,
                    created_at,
                    updated_at
                FROM repair_requests
                WHERE id = %s;
                """,
                (request_id,),
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

    if new_status in STATUS_VALUES:
        new_status = STATUS_VALUES[new_status]

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


def delete_request(request_id: int) -> bool:

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM repair_requests
                WHERE id = %s
                RETURNING id;
                """,
                (request_id,),
            )

            deleted_request = cursor.fetchone()

    return deleted_request is not None


def create_request(title, description, photo_path=None):
    """Создаёт заявку и при наличии сохраняет фотографию."""

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

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO repair_requests (
                    title,
                    description,
                    photo_data
                )
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (title, description, photo_data),
            )

            return cursor.fetchone()[0]

def get_request_photo(request_id: int):
    """Возвращает фотографию заявки или None, если её нет."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT photo_data
                FROM repair_requests
                WHERE id = %s;
                """,
                (request_id,),
            )

            result = cursor.fetchone()

    if result is None:
        return None

    return result[0]

def get_request_photo(request_id: int):
    """Возвращает фотографию заявки из базы данных."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT photo_data
                FROM repair_requests
                WHERE id = %s;
            """, (request_id,))
            result = cursor.fetchone()

    if result is None:
        return None

    return result[0]

