from database.connection import get_connection


def get_all_requests():
    """Возвращает все заявки из базы данных."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, status
                FROM repair_requests
                ORDER BY id DESC;
                """
            )
            return cursor.fetchall()


def create_request(title, description):
    """Создаёт новую заявку в базе данных."""
    title = title.strip()
    description = description.strip()

    if not title:
        raise ValueError("Введите название заявки.")

    if not description:
        raise ValueError("Введите описание заявки.")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO repair_requests (title, description)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (title, description),
            )
            return cursor.fetchone()[0]