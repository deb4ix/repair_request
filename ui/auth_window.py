import customtkinter as ctk
import keyring

from tkinter import messagebox

from services.auth_service import (
    authenticate_user,
    ensure_auth_schema,
    register_user,
)


KEYRING_SERVICE = "RepairRequestApp"
SAVED_USERNAME_KEY = "saved_username"


class AuthWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Учёт заявок на ремонт — вход")
        self.geometry("430x640")
        self.resizable(False, False)

        self.active_window = None
        self.remember_var = ctk.BooleanVar(value=True)

        self.create_widgets()

        # При запуске проверяем сохранённый аккаунт.
        self.after(100, self.check_saved_account)

        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def create_widgets(self):

        ctk.CTkLabel(
            self,
            text="Учёт заявок на ремонт",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(padx=25, pady=(35, 8))

        ctk.CTkLabel(
            self,
            text="Войдите в аккаунт или зарегистрируйтесь",
            wraplength=350,
        ).pack(padx=25, pady=(0, 25))

        self.username_entry = ctk.CTkEntry(
            self,
            placeholder_text="Логин",
            height=40,
        )
        self.username_entry.pack(
            fill="x",
            padx=35,
            pady=8,
        )

        self.password_entry = ctk.CTkEntry(
            self,
            placeholder_text="Пароль",
            show="*",
            height=40,
        )
        self.password_entry.pack(
            fill="x",
            padx=35,
            pady=8,
        )

        self.password_entry.bind(
            "<Return>",
            lambda event: self.login(),
        )

        # Запоминание аккаунта.
        self.remember_checkbox = ctk.CTkCheckBox(
            self,
            text="Запомнить меня",
            variable=self.remember_var,
        )
        self.remember_checkbox.pack(
            anchor="w",
            padx=35,
            pady=(8, 12),
        )

        ctk.CTkLabel(
            self,
            text="Тип аккаунта",
        ).pack(
            padx=35,
            pady=(8, 2),
            anchor="w",
        )

        self.role_selector = ctk.CTkOptionMenu(
            self,
            values=["Пользователь", "Ремонтник"],
            height=36,
        )
        self.role_selector.set("Пользователь")
        self.role_selector.pack(
            fill="x",
            padx=35,
            pady=(0, 8),
        )

        ctk.CTkButton(
            self,
            text="Войти",
            height=40,
            command=self.login,
        ).pack(
            fill="x",
            padx=35,
            pady=(18, 8),
        )

        ctk.CTkButton(
            self,
            text="Зарегистрироваться",
            height=40,
            fg_color="#444444",
            hover_color="#303030",
            command=self.register,
        ).pack(
            fill="x",
            padx=35,
            pady=8,
        )

        ctk.CTkLabel(
            self,
            text=(
                "Выберите тип аккаунта перед регистрацией. "
                "Ремонтник сможет просматривать все заявки "
                "и менять их статусы."
            ),
            wraplength=340,
            text_color="gray",
        ).pack(
            padx=30,
            pady=(12, 0),
        )

    # ==========================================
    # СОХРАНЕНИЕ АККАУНТА
    # ==========================================

    def save_account(self, username, password):

        try:
            old_username = keyring.get_password(
                KEYRING_SERVICE,
                SAVED_USERNAME_KEY,
            )

            # Удаляем старый пароль, если логин изменился.
            if old_username and old_username != username:
                try:
                    keyring.delete_password(
                        KEYRING_SERVICE,
                        old_username,
                    )
                except keyring.errors.PasswordDeleteError:
                    pass

            keyring.set_password(
                KEYRING_SERVICE,
                username,
                password,
            )

            keyring.set_password(
                KEYRING_SERVICE,
                SAVED_USERNAME_KEY,
                username,
            )

        except Exception as error:
            messagebox.showwarning(
                "Предупреждение",
                (
                    "Вход выполнен, но сохранить аккаунт не удалось.\n\n"
                    f"{error}"
                ),
                parent=self,
            )

    def delete_saved_account(self):

        try:
            username = keyring.get_password(
                KEYRING_SERVICE,
                SAVED_USERNAME_KEY,
            )

            if username:
                try:
                    keyring.delete_password(
                        KEYRING_SERVICE,
                        username,
                    )
                except keyring.errors.PasswordDeleteError:
                    pass

                keyring.delete_password(
                    KEYRING_SERVICE,
                    SAVED_USERNAME_KEY,
                )

        except keyring.errors.PasswordDeleteError:
            pass

        except Exception as error:
            messagebox.showwarning(
                "Предупреждение",
                f"Не удалось удалить сохранённый аккаунт:\n{error}",
                parent=self,
            )

    # ==========================================
    # АВТОМАТИЧЕСКИЙ ВХОД
    # ==========================================

    def check_saved_account(self):

        try:
            username = keyring.get_password(
                KEYRING_SERVICE,
                SAVED_USERNAME_KEY,
            )

            if not username:
                return

            password = keyring.get_password(
                KEYRING_SERVICE,
                username,
            )

            if not password:
                self.delete_saved_account()
                return

            # Проверяем сохранённые данные через PostgreSQL.
            user = authenticate_user(username, password)

            if user is None:
                self.delete_saved_account()
                return

            # Аккаунт действителен — открываем нужную сторону.
            self.open_user_window(user)

        except Exception as error:
            # Если база недоступна, не удаляем сохранённые данные.
            # Пользователь сможет попробовать войти вручную.
            messagebox.showwarning(
                "Не удалось выполнить автоматический вход",
                (
                    "Не удалось проверить сохранённый аккаунт.\n\n"
                    "Проверь подключение к интернету и базе данных.\n\n"
                    f"Подробности: {error}"
                ),
                parent=self,
            )

    # ==========================================
    # ОТКРЫТИЕ ПРИЛОЖЕНИЯ
    # ==========================================

    def open_user_window(self, user):

        self.withdraw()

        try:

            if user["role"] == "technician":

                from ui.technician_window import TechnicianWindow

                app = TechnicianWindow(
                    user,
                    master=self,
                )

            else:

                from ui.main_window import MainWindow

                app = MainWindow(
                    user,
                    master=self,
                )

            self.active_window = app

        except Exception as error:

            self.deiconify()

            messagebox.showerror(
                "Ошибка запуска",
                f"Не удалось открыть приложение:\n{error}",
                parent=self,
            )

    # ==========================================
    # ОБЫЧНЫЙ ВХОД
    # ==========================================

    def login(self):

        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning(
                "Не заполнены поля",
                "Введите логин и пароль.",
                parent=self,
            )
            return

        try:
            user = authenticate_user(username, password)

        except Exception as error:
            messagebox.showerror(
                "Ошибка подключения",
                f"Не удалось выполнить вход:\n{error}",
                parent=self,
            )
            return

        if user is None:
            messagebox.showerror(
                "Вход не выполнен",
                "Неверный логин или пароль.",
                parent=self,
            )
            return

        # Сохраняем аккаунт только после успешного входа.
        if self.remember_var.get():
            self.save_account(username, password)
        else:
            self.delete_saved_account()

        self.open_user_window(user)

    # ==========================================
    # РЕГИСТРАЦИЯ
    # ==========================================

    def register(self):

        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning(
                "Не заполнены поля",
                "Введите логин и пароль для регистрации.",
                parent=self,
            )
            return

        selected_role = self.role_selector.get()

        role = (
            "technician"
            if selected_role == "Ремонтник"
            else "user"
        )

        try:
            user = register_user(
                username,
                password,
                role,
            )

        except ValueError as error:
            messagebox.showwarning(
                "Не удалось зарегистрироваться",
                str(error),
                parent=self,
            )
            return

        except Exception as error:
            messagebox.showerror(
                "Ошибка регистрации",
                f"Не удалось создать аккаунт:\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Регистрация завершена",
            (
                "Аккаунт ремонтника создан."
                if user["role"] == "technician"
                else "Аккаунт пользователя создан."
            ) + "\nТеперь можно войти.",
            parent=self,
        )

        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)

        self.password_entry.delete(0, "end")
        self.password_entry.focus_set()

    # ==========================================
    # ЗАКРЫТИЕ ПРОГРАММЫ
    # ==========================================

    def close_app(self):

        try:
            if self.active_window is not None:
                try:
                    self.active_window.destroy()
                except Exception:
                    pass

        finally:
            self.destroy()


def main():

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    ensure_auth_schema()

    app = AuthWindow()
    app.mainloop()


if __name__ == "__main__":
    main()