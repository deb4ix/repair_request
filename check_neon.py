from database.connection import get_connection

try:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_database(), current_user;"
            )
            print("Подключение успешно!")
            print(cursor.fetchone())

except Exception as error:
    print("Ошибка подключения:")
    print(error)

input("Нажми Enter для выхода...")