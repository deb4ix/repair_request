from getpass import getpass

import customtkinter as ctk  # ensures dependency is already part of the project

from services.auth_service import create_technician, ensure_auth_schema


def main():
    ensure_auth_schema()
    print("Создание аккаунта работника")
    username = input("Логин работника: ").strip()
    password = getpass("Пароль (минимум 8 символов): ")
    confirm = getpass("Повторите пароль: ")

    if password != confirm:
        print("Пароли не совпадают.")
        return

    try:
        user = create_technician(username, password)
        print(f"Аккаунт работника {user['username']} создан.")
    except Exception as error:
        print(f"Не удалось создать аккаунт: {error}")


if __name__ == "__main__":
    main()
