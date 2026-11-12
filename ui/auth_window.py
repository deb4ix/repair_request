"""Авторизация с заставкой и выполнением сетевых запросов вне Tk-потока."""
import queue
import threading
import customtkinter as ctk
import keyring
from tkinter import messagebox

from services.auth_service import authenticate_user, register_user
from ui.technician_registration_window import TechnicianRegistrationWindow

KEYRING_SERVICE = 'RepairRequestApp'
SAVED_USERNAME_KEY = 'saved_username'


class AuthWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Учёт заявок на ремонт — вход')
        self.geometry('430x590')
        self.resizable(False, False)
        self.active_window = None
        self.technician_registration_window = None
        self.remember_var = ctk.BooleanVar(value=True)
        self.busy = False
        self.closed = False
        self.result_queue = queue.Queue()
        self.splash = None
        self.create_widgets()
        self.withdraw()
        self.protocol('WM_DELETE_WINDOW', self.close_app)
        self.after(30, self._poll_results)
        self.after(60, self._start_auto_login)

    def create_widgets(self):
        ctk.CTkLabel(self, text='Учёт заявок на ремонт',
                     font=ctk.CTkFont(size=24, weight='bold')).pack(padx=25, pady=(35, 8))
        ctk.CTkLabel(self, text='Войдите в аккаунт или создайте новый',
                     wraplength=350).pack(padx=25, pady=(0, 25))
        self.username_entry = ctk.CTkEntry(self, placeholder_text='Логин', height=40)
        self.username_entry.pack(fill='x', padx=35, pady=8)
        self.password_entry = ctk.CTkEntry(self, placeholder_text='Пароль', show='*', height=40)
        self.password_entry.pack(fill='x', padx=35, pady=8)
        self.password_entry.bind('<Return>', lambda event: self.login())
        ctk.CTkCheckBox(self, text='Запомнить меня', variable=self.remember_var).pack(
            anchor='w', padx=35, pady=(8, 12))
        self.login_button = ctk.CTkButton(self, text='Войти', height=42, command=self.login)
        self.login_button.pack(fill='x', padx=35, pady=(15, 8))
        self.register_button = ctk.CTkButton(
            self, text='Регистрация пользователя', height=42,
            fg_color='#444444', hover_color='#303030', command=self.register_user)
        self.register_button.pack(fill='x', padx=35, pady=8)
        self.technician_button = ctk.CTkButton(
            self, text='Регистрация ремонтника', height=42,
            fg_color='#8B3434', hover_color='#702929',
            command=self.open_technician_registration)
        self.technician_button.pack(fill='x', padx=35, pady=8)
        ctk.CTkLabel(self, text='Ремонтник регистрируется отдельно с помощью кода приглашения.',
                     wraplength=340, text_color='gray').pack(padx=30, pady=(12, 0))
        self.status_label = ctk.CTkLabel(self, text='', text_color='gray')
        self.status_label.pack(padx=20, pady=10)

    def _show_splash(self):
        self.splash = ctk.CTkToplevel(self)
        self.splash.title('Учёт заявок на ремонт')
        self.splash.geometry('390x170')
        self.splash.resizable(False, False)
        self.splash.protocol('WM_DELETE_WINDOW', self.close_app)
        ctk.CTkLabel(self.splash, text='Учёт заявок на ремонт',
                     font=ctk.CTkFont(size=21, weight='bold')).pack(pady=(25, 10))
        ctk.CTkLabel(self.splash, text='Выполняется автоматический вход...',
                     text_color='gray').pack(pady=(0, 12))
        bar = ctk.CTkProgressBar(self.splash, mode='indeterminate', width=270)
        bar.pack(pady=(0, 15))
        bar.start()
        self.splash.lift()

    def _hide_splash(self):
        if self.splash is not None:
            try:
                if self.splash.winfo_exists():
                    self.splash.destroy()
            except Exception:
                pass
            self.splash = None

    def _run_background(self, work, done):
        if self.busy or self.closed:
            return
        self.busy = True
        for button in (self.login_button, self.register_button, self.technician_button):
            button.configure(state='disabled')

        def worker():
            try:
                self.result_queue.put((done, work(), None))
            except Exception as exc:
                self.result_queue.put((done, None, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_results(self):
        if self.closed:
            return
        try:
            while True:
                done, result, error = self.result_queue.get_nowait()
                self.busy = False
                for button in (self.login_button, self.register_button, self.technician_button):
                    button.configure(state='normal')
                done(result, error)
        except queue.Empty:
            pass
        if not self.closed:
            self.after(50, self._poll_results)

    @staticmethod
    def _delete_saved_account():
        username = keyring.get_password(KEYRING_SERVICE, SAVED_USERNAME_KEY)
        if username:
            for name in (username, SAVED_USERNAME_KEY):
                try:
                    keyring.delete_password(KEYRING_SERVICE, name)
                except keyring.errors.PasswordDeleteError:
                    pass

    @staticmethod
    def _save_account(username, password):
        old = keyring.get_password(KEYRING_SERVICE, SAVED_USERNAME_KEY)
        if old and old != username:
            try:
                keyring.delete_password(KEYRING_SERVICE, old)
            except keyring.errors.PasswordDeleteError:
                pass
        keyring.set_password(KEYRING_SERVICE, username, password)
        keyring.set_password(KEYRING_SERVICE, SAVED_USERNAME_KEY, username)

    # Сохраняем публичные методы для совместимости с другими окнами.
    def delete_saved_account(self):
        self._delete_saved_account()

    def save_account(self, username, password):
        self._save_account(username, password)

    def _start_auto_login(self):
        self._show_splash()
        self.check_saved_account()

    def check_saved_account(self):
        def work():
            username = keyring.get_password(KEYRING_SERVICE, SAVED_USERNAME_KEY)
            if not username:
                return None
            password = keyring.get_password(KEYRING_SERVICE, username)
            if not password:
                self._delete_saved_account()
                return None
            user = authenticate_user(username, password)
            if user is None:
                self._delete_saved_account()
            return user

        def done(user, error):
            self._hide_splash()
            if self.closed:
                return
            if error:
                self.deiconify()
                self.lift()
                messagebox.showwarning(
                    'Не удалось выполнить автоматический вход',
                    f'Проверь подключение к Neon PostgreSQL.\n\n{error}', parent=self)
            elif user:
                self.open_user_window(user)
            else:
                self.deiconify()
                self.lift()

        self._run_background(work, done)

    def open_user_window(self, user):
        self._hide_splash()
        self.withdraw()
        try:
            if user['role'] == 'technician':
                from ui.technician_window import TechnicianWindow
                app = TechnicianWindow(user, master=self)
            else:
                from ui.main_window import MainWindow
                app = MainWindow(user, master=self)
            self.active_window = app
            app.lift()
        except Exception as exc:
            self.deiconify()
            messagebox.showerror('Ошибка запуска', f'Не удалось открыть приложение:\n{exc}', parent=self)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        remember = self.remember_var.get()
        if not username or not password:
            messagebox.showwarning('Не заполнены поля', 'Введите логин и пароль.', parent=self)
            return
        self.status_label.configure(text='Вход в аккаунт...')

        def work():
            user = authenticate_user(username, password)
            if user is None:
                return (None, None)
            warning = None
            try:
                if remember:
                    self._save_account(username, password)
                else:
                    self._delete_saved_account()
            except Exception as exc:
                warning = str(exc)
            return (user, warning)

        def done(result, error):
            self.status_label.configure(text='')
            if error:
                messagebox.showerror('Ошибка подключения', str(error), parent=self)
                return
            user, warning = result
            if user is None:
                messagebox.showerror('Вход не выполнен', 'Неверный логин или пароль.', parent=self)
                return
            if warning:
                messagebox.showwarning('Предупреждение', 'Не удалось сохранить аккаунт:\n' + warning, parent=self)
            self.open_user_window(user)

        self._run_background(work, done)

    def register_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning('Не заполнены поля', 'Введите логин и пароль.', parent=self)
            return
        self.status_label.configure(text='Регистрация...')

        def done(user, error):
            self.status_label.configure(text='')
            if error:
                kind = messagebox.showwarning if isinstance(error, ValueError) else messagebox.showerror
                kind('Ошибка регистрации', str(error), parent=self)
                return
            messagebox.showinfo('Регистрация завершена',
                                f'Аккаунт «{user["username"]}» создан. Теперь можно войти.', parent=self)
            self.username_entry.delete(0, 'end')
            self.username_entry.insert(0, username)
            self.password_entry.delete(0, 'end')
            self.password_entry.focus_set()

        self._run_background(lambda: register_user(username, password), done)

    def open_technician_registration(self):
        if self.busy:
            return
        if (self.technician_registration_window is not None
                and self.technician_registration_window.winfo_exists()):
            self.technician_registration_window.focus()
            return
        self.technician_registration_window = TechnicianRegistrationWindow(self)

    def close_app(self):
        self.closed = True
        if self.active_window is not None:
            try:
                self.active_window.destroy()
            except Exception:
                pass
        self.destroy()


def main():
    ctk.set_appearance_mode('System')
    ctk.set_default_color_theme('blue')
    app = AuthWindow()
    app.mainloop()


if __name__ == '__main__':
    main()
