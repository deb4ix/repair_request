from database.connection import get_connection


def add_test_request():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO repair_requests (title, description)
                VALUES (%s, %s)
                RETURNING id, title, description, status, created_at;
                """,
                (
                    "Тестовая заявка из Python",
                    "Проверка добавления заявки в PostgreSQL",
                ),
            )

            request = cursor.fetchone()

    print("Заявка успешно добавлена!")
    print("ID:", request[0])
    print("Название:", request[1])
    print("Описание:", request[2])
    print("Статус:", request[3])
    print("Дата создания:", request[4])


if __name__ == "__main__":
    add_test_request()