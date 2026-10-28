import customtkinter as ctk

from services.auth_service import ensure_auth_schema
from ui.auth_window import AuthWindow


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # Создаём таблицу аккаунтов и добавляем owner_id в repair_requests.
    ensure_auth_schema()

    app = AuthWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
