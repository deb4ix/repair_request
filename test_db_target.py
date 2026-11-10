from database.connection import get_connection


def main():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute("""
                    SELECT
                        current_database(),
                        current_schema(),
                        current_user,
                        inet_server_addr(),
                        inet_server_port();
                """)

                info = cursor.fetchone()

                print("=== ПОДКЛЮЧЕНИЕ ПРИЛОЖЕНИЯ ===")
                print("База данных:", info[0])
                print("Схема:", info[1])
                print("Пользователь:", info[2])
                print("Адрес сервера:", info[3])
                print("Порт:", info[4])

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM public.repair_requests;
                """)

                print(
                    "Количество заявок:",
                    cursor.fetchone()[0]
                )

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM public.request_categories;
                """)

                print(
                    "Количество категорий:",
                    cursor.fetchone()[0]
                )

    except Exception as error:
        print("ОШИБКА ПОДКЛЮЧЕНИЯ:")
        print(type(error).__name__, error)


if __name__ == "__main__":
    main()