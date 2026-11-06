import customtkinter as ctk

from tkinter import messagebox

from services.auth_service import register_technician


class TechnicianRegistrationWindow(ctk.CTkToplevel):

    def __init__(self, master=None):
        super().__init__(master)

        self.title("Регистрация ремонтника")
        self.geometry("430x570")
        self.resizable(False, False)

        self.transient(master)
        self.grab_set()

        self.create_widgets()

        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def create_widgets(self):
        ctk.CTkLabel(
            self,
            text="Регистрация ремонтника",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(padx=25, pady=(30, 10))

        ctk.CTkLabel(
            self,
            text=(
                "Создайте аккаунт для работы с заявками.\n"
                "Для регистрации потребуется код приглашения."
            ),
            justify="center",
            wraplength=350,
            text_color="gray",
        ).pack(padx=25, pady=(0, 20))

        self.username_entry = ctk.CTkEntry(
            self,
            placeholder_text="Логин",
            height=42,
        )
        self.username_entry.pack(fill="x", padx=35, pady=8)

        self.password_entry = ctk.CTkEntry(
            self,
            placeholder_text="Пароль (минимум 8 символов)",
            show="*",
            height=42,
        )
        self.password_entry.pack(fill="x", padx=35, pady=8)

        self.confirm_password_entry = ctk.CTkEntry(
            self,
            placeholder_text="Повторите пароль",
            show="*",
            height=42,
        )
        self.confirm_password_entry.pack(fill="x", padx=35, pady=8)

        self.invitation_entry = ctk.CTkEntry(
            self,
            placeholder_text="Код приглашения",
            show="*",
            height=42,
        )
        self.invitation_entry.pack(fill="x", padx=35, pady=8)

        self.confirm_password_entry.bind(
            "<Return>",
            lambda event: self.register(),
        )

        ctk.CTkButton(
            self,
            text="Создать аккаунт ремонтника",
            height=42,
            command=self.register,
        ).pack(fill="x", padx=35, pady=(22, 8))

        ctk.CTkButton(
            self,
            text="Назад",
            height=38,
            fg_color="transparent",
            border_width=1,
            text_color=("black", "white"),
            command=self.close_window,
        ).pack(fill="x", padx=35, pady=8)

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        invitation_code = self.invitation_entry.get()

        if not username or not password or not confirm_password:
            messagebox.showwarning(
                "Не заполнены поля",
                "Заполните все поля.",
                parent=self,
            )
            return

        if not invitation_code:
            messagebox.showwarning(
                "Нет кода приглашения",
                "Введите код приглашения.",
                parent=self,
            )
            return

        if password != confirm_password:
            messagebox.showwarning(
                "Пароли не совпадают",
                "Проверьте пароль и его подтверждение.",
                parent=self,
            )
            return

        try:
            user = register_technician(
                username,
                password,
                invitation_code,
            )

        except ValueError as error:
            messagebox.showwarning(
                "Регистрация не выполнена",
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
                f"Аккаунт ремонтника «{user['username']}» создан.\n\n"
                "Теперь можно вернуться к окну входа."
            ),
            parent=self,
        )

        self.destroy()

    def close_window(self):
        self.grab_release()
        self.destroy()