from getpass import getpass

from services.auth_service import (
    create_technician,
    ensure_auth_schema,
)


def main():
    print("=" * 45)
    print("СОЗДАНИЕ АККАУНТА РЕМОНТНИКА")
    print("=" * 45)

    try:
        ensure_auth_schema()

        username = input("Логин ремонтника: ").strip()
        password = getpass("Пароль (минимум 8 символов): ")
        confirm = getpass("Повторите пароль: ")

        if password != confirm:
            print("Ошибка: пароли не совпадают.")
            return

        user = create_technician(username, password)

        print()
        print("Аккаунт ремонтника успешно создан.")
        print(f"Логин: {user['username']}")
        print(f"Роль: {user['role']}")

    except ValueError as error:
        print(f"Ошибка: {error}")

    except Exception as error:
        print(f"Не удалось создать аккаунт: {error}")


if __name__ == "__main__":
    main()