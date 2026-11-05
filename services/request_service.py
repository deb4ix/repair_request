from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

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


def format_datetime(value, timezone_name=None):
    """
    Преобразует дату из базы в локальное время пользователя.

    Если часовой пояс не передан, используется часовой пояс
    операционной системы, на которой запущена программа.

    Возвращает дату без обозначений часового пояса.
    """
    if value is None:
        return "Не указано"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value

    if value.tzinfo is None:
        # Если дата без часового пояса, считаем её временем UTC.
        value = value.replace(tzinfo=ZoneInfo("UTC"))

    if timezone_name:
        try:
            local_timezone = ZoneInfo(timezone_name)
        except Exception:
            local_timezone = datetime.now().astimezone().tzinfo
    else:
        local_timezone = datetime.now().astimezone().tzinfo

    local_datetime = value.astimezone(local_timezone)

    return local_datetime.strftime("%d.%m.%Y %H:%M:%S")


def get_all_requests(owner_id=None):
    """Возвращает список заявок со статусами на русском языке."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            query = """
                SELECT
                    rr.id,
                    rr.title,
                    rr.status,
                    COALESCE(au.username, 'Неизвестный пользователь')
                FROM repair_requests AS rr
                LEFT JOIN app_users AS au
                    ON au.id = rr.owner_id
            """

            if owner_id is not None:
                query += " WHERE rr.owner_id = %s"
                cursor.execute(
                    query + " ORDER BY rr.id ASC;",
                    (owner_id,),
                )
            else:
                cursor.execute(query + " ORDER BY rr.id ASC;")

            rows = cursor.fetchall()

    return [
        (
            request_id,
            title,
            STATUS_NAMES.get(status, status),
            owner_username,
        )
        for request_id, title, status, owner_username in rows
    ]


def get_request_by_id(request_id: int, owner_id=None):
    """Возвращает подробную информацию о заявке."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    """
                    SELECT
                        id,
                        title,
                        description,
                        status,
                        created_at,
                        updated_at,
                        owner_id,
                        COALESCE(
                            (SELECT username FROM app_users
                             WHERE app_users.id = repair_requests.owner_id),
                            'Неизвестный пользователь'
                        )
                    FROM repair_requests
                    WHERE id = %s;
                    """,
                    (request_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        title,
                        description,
                        status,
                        created_at,
                        updated_at,
                        owner_id,
                        COALESCE(
                            (SELECT username FROM app_users
                             WHERE app_users.id = repair_requests.owner_id),
                            'Неизвестный пользователь'
                        )
                    FROM repair_requests
                    WHERE id = %s
                      AND owner_id = %s;
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
        "status_name": STATUS_NAMES.get(
            request[3],
            request[3],
        ),
        "created_at": format_datetime(request[4]),
        "updated_at": format_datetime(request[5]),
        "owner_id": request[6],
        "owner_username": request[7],
    }


def update_request_status(
    request_id: int,
    new_status: str,
) -> bool:
    """Изменяет статус заявки с проверкой допустимости перехода."""

    # Преобразуем русское название статуса в системное.
    new_status = STATUS_VALUES.get(
        new_status,
        new_status,
    )

    # Проверяем существование такого статуса.
    if new_status not in STATUS_NAMES:
        raise ValueError(
            "Указан неизвестный статус заявки."
        )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status
                FROM repair_requests
                WHERE id = %s
                FOR UPDATE;
                """,
                (request_id,),
            )

            request = cursor.fetchone()

            if request is None:
                return False

            current_status = request[0]

            if (
                current_status != "new"
                and new_status == "new"
            ):
                raise ValueError(
                    "Нельзя вернуть заявку в статус "
                    "«Новая» после изменения её первоначального статуса."
                )

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
    """Синхронизирует последовательность идентификаторов."""
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
    """Удаляет заявку."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    """
                    DELETE FROM repair_requests
                    WHERE id = %s
                    RETURNING id;
                    """,
                    (request_id,),
                )
            else:
                cursor.execute(
                    """
                    DELETE FROM repair_requests
                    WHERE id = %s
                      AND owner_id = %s
                    RETURNING id;
                    """,
                    (request_id, owner_id),
                )

            deleted_request = cursor.fetchone()

    return deleted_request is not None


def create_request(
    title,
    description,
    photo_path=None,
    owner_id=None,
):
    """Создаёт заявку и сохраняет фотографию, если она указана."""
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
                    title,
                    description,
                    photo_data,
                    owner_id
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    title,
                    description,
                    photo_data,
                    owner_id,
                ),
            )

            created_request_id = cursor.fetchone()[0]

    return created_request_id


def get_request_photo(request_id: int, owner_id=None):
    """Возвращает фотографию заявки в виде байтов."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if owner_id is None:
                cursor.execute(
                    """
                    SELECT photo_data
                    FROM repair_requests
                    WHERE id = %s;
                    """,
                    (request_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT photo_data
                    FROM repair_requests
                    WHERE id = %s
                      AND owner_id = %s;
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
    """Обновляет заявку, сохраняя или удаляя фотографию по запросу."""
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

    owner_clause = (
        " AND owner_id = %s"
        if owner_id is not None
        else ""
    )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            if remove_photo:
                query = (
                    "UPDATE repair_requests "
                    "SET title = %s, description = %s, "
                    "photo_data = NULL, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s"
                    + owner_clause
                    + " RETURNING id;"
                )

                params = (
                    title,
                    description,
                    request_id,
                )

            elif photo_path:
                query = (
                    "UPDATE repair_requests "
                    "SET title = %s, description = %s, "
                    "photo_data = %s, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s"
                    + owner_clause
                    + " RETURNING id;"
                )

                params = (
                    title,
                    description,
                    photo_data,
                    request_id,
                )

            else:
                query = (
                    "UPDATE repair_requests "
                    "SET title = %s, description = %s, "
                    "updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s"
                    + owner_clause
                    + " RETURNING id;"
                )

                params = (
                    title,
                    description,
                    request_id,
                )

            if owner_id is not None:
                params += (owner_id,)

            cursor.execute(query, params)
            updated_request = cursor.fetchone()

    return updated_request is not None
