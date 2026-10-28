import customtkinter as ctk
from tkinter import messagebox

from services.auth_service import (
    authenticate_user,
    ensure_auth_schema,
    register_user,
)


class AuthWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Учёт заявок на ремонт — вход")
        self.geometry("430x600")
        self.resizable(False, False)

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
            self, placeholder_text="Логин", height=40
        )
        self.username_entry.pack(fill="x", padx=35, pady=8)

        self.password_entry = ctk.CTkEntry(
            self, placeholder_text="Пароль", show="*", height=40
        )
        self.password_entry.pack(fill="x", padx=35, pady=8)
        self.password_entry.bind("<Return>", lambda event: self.login())

        ctk.CTkLabel(self, text="Тип аккаунта").pack(
            padx=35, pady=(8, 2), anchor="w"
        )
        self.role_selector = ctk.CTkOptionMenu(
            self,
            values=["Пользователь", "Ремонтник"],
            height=36,
        )
        self.role_selector.set("Пользователь")
        self.role_selector.pack(fill="x", padx=35, pady=(0, 8))

        ctk.CTkButton(
            self,
            text="Войти",
            height=40,
            command=self.login,
        ).pack(fill="x", padx=35, pady=(20, 8))

        ctk.CTkButton(
            self,
            text="Зарегистрироваться",
            height=40,
            fg_color="#444444",
            hover_color="#303030",
            command=self.register,
        ).pack(fill="x", padx=35, pady=8)

        ctk.CTkLabel(
            self,
            text=(
                "Выберите тип аккаунта перед регистрацией. "
                "Ремонтник сможет просматривать все заявки и менять их статусы."
            ),
            wraplength=340,
            text_color="gray",
        ).pack(padx=30, pady=(12, 0))

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

        # Оставляем корневое окно живым: это предотвращает ошибки Tcl
        # "invalid command name" от отложенных callbacks CustomTkinter.
        self.withdraw()
        if user["role"] == "technician":
            from ui.technician_window import TechnicianWindow
            app = TechnicianWindow(user, master=self)
        else:
            from ui.main_window import MainWindow
            app = MainWindow(user, master=self)
        self.active_window = app

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

        try:
            selected_role = self.role_selector.get()
            role = "technician" if selected_role == "Ремонтник" else "user"
            user = register_user(username, password, role)
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
                "Аккаунт ремонтника создан. Теперь можно войти."
                if user["role"] == "technician"
                else "Аккаунт пользователя создан. Теперь можно войти."
            ),
            parent=self,
        )
        self.password_entry.delete(0, "end")
        self.username_entry.focus_set()


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    ensure_auth_schema()
    app = AuthWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
