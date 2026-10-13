from database.connection import get_connection


def test_connection():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                # Проверяем соединение
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]

                print("Подключение к PostgreSQL успешно!")
                print("Версия сервера:", version)

                # Проверяем наличие таблицы
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = 'repair_requests'
                    );
                """)

                table_exists = cursor.fetchone()[0]

                if table_exists:
                    print("Таблица repair_requests найдена!")

                    cursor.execute("""
                        SELECT id, title, status
                        FROM public.repair_requests
                        ORDER BY id DESC;
                    """)

                    requests = cursor.fetchall()

                    print(f"Количество заявок: {len(requests)}")

                    for request in requests:
                        print(request)

                else:
                    print(
                        "Таблица не найдена в базе данных. "
                        "Проверь DB_NAME и схему таблицы."
                    )

    except Exception as error:
        print("Не удалось подключиться к PostgreSQL.")
        print("Ошибка:", error)


if __name__ == "__main__":
    test_connection()