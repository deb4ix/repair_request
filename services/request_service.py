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
            # Находим первый свободный номер
            cursor.execute(
                """
                SELECT MIN(candidate_id)
                FROM generate_series(
                    1,
                    COALESCE(
                        (SELECT MAX(id) + 1 FROM repair_requests),
                        1
                    )
                ) AS candidate_id
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM repair_requests
                    WHERE id = candidate_id
                );
                """
            )

            request_id = cursor.fetchone()[0]

            # Создаём заявку с найденным номером
            cursor.execute(
                """
                INSERT INTO repair_requests
                    (id, title, description)
                VALUES (%s, %s, %s);
                """,
                (request_id, title, description),
            )

            return request_id