
from pathlib import Path
from time import monotonic
from threading import Lock
from datetime import datetime
from zoneinfo import ZoneInfo

from database.connection import get_connection


STATUS_NAMES = {
    "new": "Новая",
    "in_progress": "В работе",
    "completed": "Завершена",
    "pending_confirmation": "Ожидает подтверждения",
    "cancelled": "Отменена",
}

STATUS_VALUES = {
    "Новая": "new",
    "В работе": "in_progress",
    "Завершена": "completed",
    "Ожидает подтверждения": "pending_confirmation",
    "Отменена": "cancelled",
}

PRIORITY_NAMES = {
    "low": "Низкий",
    "normal": "Обычный",
    "high": "Высокий",
    "critical": "Критический",
}

PRIORITY_VALUES = {
    "Низкий": "low",
    "Обычный": "normal",
    "Высокий": "high",
    "Критический": "critical",
}


def _normalize_priority(priority):
    priority = PRIORITY_VALUES.get(priority, priority)

    if priority not in PRIORITY_NAMES:
        raise ValueError("Указан неизвестный приоритет заявки.")

    return priority


def _normalize_category_id(category_id):
    if category_id in (None, ""):
        return None

    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        raise ValueError("Выберите корректную категорию заявки.")

    if category_id <= 0:
        raise ValueError("Выберите корректную категорию заявки.")

    return category_id


def format_datetime(value, timezone_name=None):
    if value is None:
        return "Не указано"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value

    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))

    if timezone_name:
        try:
            local_timezone = ZoneInfo(timezone_name)
        except Exception:
            local_timezone = datetime.now().astimezone().tzinfo
    else:
        local_timezone = datetime.now().astimezone().tzinfo

    return value.astimezone(local_timezone).strftime(
        "%d.%m.%Y %H:%M:%S"
    )


_categories_cache = None
_categories_cached_at = 0.0
_categories_lock = Lock()
_CATEGORIES_TTL_SECONDS = 300


def get_categories():
    """Возвращает список категорий в формате (id, название)."""
    global _categories_cache, _categories_cached_at
    with _categories_lock:
        if (_categories_cache is not None and
                monotonic() - _categories_cached_at < _CATEGORIES_TTL_SECONDS):
            return list(_categories_cache)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name
                FROM request_categories
                ORDER BY id ASC;
                """
            )
            categories = cursor.fetchall()

    with _categories_lock:
        _categories_cache = tuple(categories)
        _categories_cached_at = monotonic()
    return list(categories)


def invalidate_categories_cache():
    """Сбрасывает кэш после изменения справочника категорий."""
    global _categories_cache, _categories_cached_at
    with _categories_lock:
        _categories_cache = None
        _categories_cached_at = 0.0


def get_all_requests(owner_id=None):
    """
    Возвращает заявки в формате:
    (
        id,
        название,
        статус,
        автор,
        category_id,
        category_name,
        priority
    )
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            query = """
                SELECT
                    rr.id,
                    rr.title,
                    rr.status,
                    COALESCE(
                        au.username,
                        'Неизвестный пользователь'
                    ),
                    rr.category_id,
                    COALESCE(rc.name, 'Не указана'),
                    rr.priority
                FROM repair_requests AS rr
                LEFT JOIN app_users AS au
                    ON au.id = rr.owner_id
                LEFT JOIN request_categories AS rc
                    ON rc.id = rr.category_id
            """

            if owner_id is not None:
                query += """
                    WHERE rr.owner_id = %s
                """
                cursor.execute(
                    query + " ORDER BY rr.created_at ASC, rr.id ASC;",
                    (owner_id,),
                )
            else:
                cursor.execute(
                    query + " ORDER BY rr.created_at ASC, rr.id ASC;"
                )

            rows = cursor.fetchall()

    return [
        (
            request_id,
            title,
            STATUS_NAMES.get(status, status),
            author,
            category_id,
            category_name,
            priority,
        )
        for (
            request_id,
            title,
            status,
            author,
            category_id,
            category_name,
            priority,
        ) in rows
    ]


def get_request_by_id(request_id: int, owner_id=None):
    """Возвращает подробную информацию о заявке."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            query = """
                SELECT
                    rr.id,
                    rr.title,
                    rr.description,
                    rr.status,
                    rr.created_at,
                    rr.updated_at,
                    rr.owner_id,
                    COALESCE(
                        au.username,
                        'Неизвестный пользователь'
                    ),
                    rr.category_id,
                    rc.name,
                    rr.priority
                FROM repair_requests AS rr
                LEFT JOIN app_users AS au
                    ON au.id = rr.owner_id
                LEFT JOIN request_categories AS rc
                    ON rc.id = rr.category_id
                WHERE rr.id = %s
            """

            params = [request_id]

            if owner_id is not None:
                query += " AND rr.owner_id = %s"
                params.append(owner_id)

            cursor.execute(
                query + ";",
                tuple(params),
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
        "category_id": request[8],
        "category_name": request[9] or "Не указана",
        "priority": request[10],
        "priority_name": PRIORITY_NAMES.get(
            request[10],
            request[10],
        ),
    }


def update_request_status(request_id: int, new_status: str) -> bool:
    """Старый небезопасный путь отключён. Используйте change_status_with_event."""
    raise PermissionError("Изменяйте статус через change_status_with_event или подтверждение отчёта.")


def delete_request(request_id: int, owner_id=None) -> bool:
    """Удаляет заявку."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM repair_requests WHERE id=%s FOR UPDATE", (request_id,))
            state = cursor.fetchone()
            if state and state[0] != "new":
                raise ValueError("Удалять можно только новые заявки. Остальные сохраняются для истории.")
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
    category_id=None,
    priority="normal",
):
    """Создаёт заявку с категорией, приоритетом и фотографией."""

    title = title.strip()
    description = description.strip()

    if not title:
        raise ValueError("Введите название заявки.")

    if not description:
        raise ValueError("Введите описание заявки.")

    category_id = _normalize_category_id(category_id)
    priority = _normalize_priority(priority)

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
                    owner_id,
                    category_id,
                    priority
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    title,
                    description,
                    photo_data,
                    owner_id,
                    category_id,
                    priority,
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
    category_id=None,
    priority="normal",
) -> bool:
    """Обновляет заявку, категорию, приоритет и фотографию."""

    title = title.strip()
    description = description.strip()

    if not title:
        raise ValueError("Введите название заявки.")

    if not description:
        raise ValueError("Введите описание заявки.")

    category_id = _normalize_category_id(category_id)
    priority = _normalize_priority(priority)

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

    if remove_photo:
        photo_clause = "photo_data = NULL, "
        photo_params = ()
    elif photo_path:
        photo_clause = "photo_data = %s, "
        photo_params = (photo_data,)
    else:
        photo_clause = ""
        photo_params = ()

    query = (
        "UPDATE repair_requests SET "
        "title = %s, "
        "description = %s, "
        + photo_clause
        + "category_id = %s, "
        "priority = %s, "
        "updated_at = CURRENT_TIMESTAMP "
        "WHERE id = %s"
        + owner_clause
        + " RETURNING id;"
    )

    params = (
        title,
        description,
        *photo_params,
        category_id,
        priority,
        request_id,
    )

    if owner_id is not None:
        params += (owner_id,)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM repair_requests WHERE id=%s FOR UPDATE", (request_id,))
            state = cursor.fetchone()
            if state and state[0] != "new":
                raise ValueError("Редактирование доступно только для новых заявок.")
            cursor.execute(query, params)
            updated_request = cursor.fetchone()

    return updated_request is not None

