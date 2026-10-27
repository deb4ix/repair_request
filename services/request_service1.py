from database.connection import get_connection

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


def get_all_requests():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    id,
                    title,
                    CASE status
                        WHEN 'new' THEN 'Новая'
                        WHEN 'in_progress' THEN 'В работе'
                        WHEN 'completed' THEN 'Завершена'
                        WHEN 'cancelled' THEN 'Отменена'
                        ELSE status
                    END AS status
                FROM repair_requests
                ORDER BY id DESC;
            """)
            return cursor.fetchall()


def create_request(title, description):
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