
import io
from pathlib import Path
from datetime import datetime

import customtkinter as ctk
from tkinter import ttk, messagebox
from PIL import Image

from services.request_service import (
    get_all_requests,
    get_request_by_id,
    get_categories,
    update_request_status,
    delete_request,
    get_request_photo,
)


STATUS_FILTER_VALUES = [
    "Все статусы",
    "Новая",
    "В работе",
    "Завершена",
    "Отменена",
]


def format_datetime(value):
    """Форматирует дату без секунд, микросекунд и часового пояса."""
    if value is None:
        return "Не указано"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return value

    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")

    return str(value)


class TechnicianWindow(ctk.CTkToplevel):

    def __init__(self, user, master=None):
        super().__init__(master)

        self.current_user = user
        self.title(
            f"Рабочее место специалиста — {user['username']}"
        )
        self.geometry("1200x720")
        self.minsize(900, 580)
        self.protocol("WM_DELETE_WINDOW", self.logout)

        self._auto_refresh_id = None
        self._current_table_theme = None

        self.categories = []
        self.category_names = []

        # ID заявок, которые уже были загружены.
        # Первый запуск формирует базовый список без уведомлений.
        self._known_request_ids = None
        self._notification_windows = []

        self.create_widgets()
        self.load_requests()

        self._auto_refresh_id = self.after(
            5000,
            self.auto_refresh,
        )

    def load_logo(self):
        project_root = Path(__file__).resolve().parent.parent
        logo_path = project_root / "assets" / "logo.png"

        if not logo_path.exists():
            messagebox.showwarning(
                "Логотип не найден",
                f"Не удалось найти файл:\n{logo_path}",
                parent=self,
            )
            return

        image = Image.open(logo_path).convert("RGBA")
        image.thumbnail((165, 165), Image.Resampling.LANCZOS)

        self.logo_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size,
        )

        self.logo_label = ctk.CTkLabel(
            self,
            text="",
            image=self.logo_image,
        )
        self.logo_label.grid(
            row=0,
            column=0,
            padx=20,
            pady=(15, 0),
            sticky="w",
        )

    
    # Категории
    

    def load_categories(self):
        self.categories = get_categories()
        self.category_names = [
            name for category_id, name in self.categories
        ]

    def update_category_filter(self):
        self.load_categories()

        values = ["Все категории"] + self.category_names
        current = self.category_filter.get()

        self.category_filter.configure(values=values)

        if current not in values:
            self.category_filter.set("Все категории")

    
    # Интерфейс
    

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.load_logo()

        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(
            row=1,
            column=0,
            padx=20,
            pady=10,
            sticky="ew",
        )
        filter_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Поиск по названию заявки...",
        )
        self.search_entry.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="ew",
        )
        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_requests(show_errors=False),
        )

        self.status_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=STATUS_FILTER_VALUES,
            command=lambda value: self.load_requests(
                show_errors=False
            ),
            width=150,
        )
        self.status_filter.set("Все статусы")
        self.status_filter.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
        )

        self.category_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=["Все категории"],
            command=lambda value: self.load_requests(
                show_errors=False
            ),
            width=210,
        )
        self.category_filter.set("Все категории")
        self.category_filter.grid(
            row=0,
            column=2,
            padx=10,
            pady=10,
        )

        table_frame = ctk.CTkFrame(self)
        table_frame.grid(
            row=2,
            column=0,
            padx=20,
            pady=10,
            sticky="nsew",
        )
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=(
                "id",
                "title",
                "category",
                "status",
                "author",
            ),
            show="headings",
            selectmode="browse",
            style="Technician.Treeview",
        )

        self.tree.heading("id", text="№")
        self.tree.heading("title", text="Название заявки")
        self.tree.heading("category", text="Категория")
        self.tree.heading("status", text="Статус")
        self.tree.heading("author", text="Отправитель")

        self.tree.column(
            "id",
            width=65,
            anchor="center",
            stretch=False,
        )
        self.tree.column(
            "title",
            width=330,
            anchor="w",
        )
        self.tree.column(
            "category",
            width=210,
            anchor="center",
        )
        self.tree.column(
            "status",
            width=130,
            anchor="center",
        )
        self.tree.column(
            "author",
            width=180,
            anchor="center",
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.update_table_theme()

        self.tree.bind(
            "<Double-1>",
            lambda event: self.show_request_details(),
        )

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.grid(
            row=3,
            column=0,
            padx=20,
            pady=(5, 20),
            sticky="ew",
        )

        ctk.CTkButton(
            buttons_frame,
            text="Обновить список",
            command=self.load_requests,
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            buttons_frame,
            text="Подробнее",
            command=self.show_request_details,
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            buttons_frame,
            text="Изменить статус",
            command=self.change_request_status,
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            buttons_frame,
            text="Удалить заявку",
            fg_color="#b22222",
            hover_color="#8b0000",
            command=self.delete_selected_request,
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            buttons_frame,
            text="Настройки",
            command=self.show_settings,
        ).pack(side="right", padx=8, pady=10)

        ctk.CTkButton(
            buttons_frame,
            text="Выйти из аккаунта",
            fg_color="#555555",
            hover_color="#333333",
            command=self.logout,
        ).pack(side="right", padx=8, pady=10)

    
    # Оформление таблицы
    

    def update_table_theme(self):
        appearance = ctk.get_appearance_mode()
        is_dark = appearance.lower() == "dark"

        if is_dark:
            background = "#242424"
            foreground = "#F2F2F2"
            heading_background = "#333333"
            heading_foreground = "#FFFFFF"
            selected_background = "#1F538D"

            status_colors = {
                "new": ("#183B2A", "#B7F7CC"),
                "in_progress": ("#193653", "#BFDBFE"),
                "completed": ("#383838", "#E5E7EB"),
                "cancelled": ("#4A2222", "#FECACA"),
            }
        else:
            background = "#FFFFFF"
            foreground = "#202020"
            heading_background = "#E5E5E5"
            heading_foreground = "#202020"
            selected_background = "#A9CFF5"

            status_colors = {
                "new": ("#D9F2DF", "#14532D"),
                "in_progress": ("#DCEBFA", "#1E40AF"),
                "completed": ("#E5E7EB", "#374151"),
                "cancelled": ("#FADBD8", "#991B1B"),
            }

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Technician.Treeview",
            background=background,
            foreground=foreground,
            fieldbackground=background,
            rowheight=34,
            font=("Arial", 10),
            borderwidth=0,
        )

        style.configure(
            "Technician.Treeview.Heading",
            background=heading_background,
            foreground=heading_foreground,
            font=("Arial", 10, "bold"),
            relief="flat",
            padding=(8, 8),
        )

        style.map(
            "Technician.Treeview",
            background=[("selected", selected_background)],
            foreground=[
                ("selected", "#FFFFFF" if is_dark else "#202020")
            ],
        )

        style.map(
            "Technician.Treeview.Heading",
            background=[("active", heading_background)],
            foreground=[("active", heading_foreground)],
        )

        for status, colors in status_colors.items():
            self.tree.tag_configure(
                status,
                background=colors[0],
                foreground=colors[1],
            )

        self._current_table_theme = appearance

    @staticmethod
    def get_status_tag(status):
        normalized = (status or "").strip().casefold()

        status_tags = {
            "new": "new",
            "новая": "new",
            "in_progress": "in_progress",
            "в работе": "in_progress",
            "completed": "completed",
            "завершена": "completed",
            "cancelled": "cancelled",
            "canceled": "cancelled",
            "отменена": "cancelled",
        }

        return status_tags.get(normalized, "")

    
    # Загрузка и фильтрация заявок
    

    def load_requests(self, show_errors=True):
        try:
            current_theme = ctk.get_appearance_mode()

            if current_theme != self._current_table_theme:
                self.update_table_theme()

            requests = get_all_requests()
            display_numbers = {
                int(request[0]): index
                for index, request in enumerate(requests, start=1)
            }

            # Определяем новые заявки по ID до применения фильтров интерфейса.
            current_requests_by_id = {
                int(request[0]): request
                for request in requests
            }
            current_request_ids = set(current_requests_by_id)
            self._display_numbers = display_numbers

            if self._known_request_ids is None:
                # При первом открытии запоминаем уже существующие заявки.
                self._known_request_ids = current_request_ids
            else:
                new_request_ids = current_request_ids - self._known_request_ids
                self._known_request_ids = current_request_ids

                for new_request_id in sorted(new_request_ids):
                    self.show_new_request_notification(
                        current_requests_by_id[new_request_id]
                    )

            self.update_category_filter()

            search_text = (
                self.search_entry.get().strip().casefold()
            )
            selected_status = (
                self.status_filter.get().strip().casefold()
            )
            selected_category = self.category_filter.get()

            status_codes = {
                "новая": "new",
                "в работе": "in_progress",
                "завершена": "completed",
                "отменена": "cancelled",
            }

            normalized_status = status_codes.get(
                selected_status,
                selected_status,
            )

            for item in self.tree.get_children():
                self.tree.delete(item)

            for request in requests:
                (
                    request_id,
                    title,
                    status,
                    author,
                    category_id,
                    category_name,
                    priority,
                ) = request

                title = title or ""
                status = status or ""
                author = author or "Неизвестный пользователь"
                category_name = category_name or "Не указана"

                if (
                    search_text
                    and search_text not in title.casefold()
                ):
                    continue

                if (
                    selected_status != "все статусы"
                    and status.casefold() != normalized_status
                ):
                    continue

                if (
                    selected_category != "Все категории"
                    and category_name != selected_category
                ):
                    continue

                status_tag = self.get_status_tag(status)

                self.tree.insert(
                    "",
                    "end",
                    iid=str(request_id),
                    values=(
                        display_numbers[int(request_id)],
                        title,
                        category_name,
                        status,
                        author,
                    ),
                    tags=(status_tag,) if status_tag else (),
                )

        except Exception as error:
            if show_errors:
                messagebox.showerror(
                    "Ошибка",
                    f"Не удалось загрузить заявки:\n{error}",
                    parent=self,
                )

    
    # Уведомления о новых заявках
    

    def show_new_request_notification(self, request):
        """Показывает ненавязчивое всплывающее уведомление о новой заявке."""
        request_id = request[0]
        display_number = getattr(
            self,
            "_display_numbers",
            {},
        ).get(int(request_id), request_id)
        title = request[1] or "Без названия"
        author = request[3] or "Неизвестный пользователь"

        try:
            notification = ctk.CTkToplevel(self)
            notification.title("Новая заявка")
            notification.geometry("360x145")
            notification.resizable(False, False)
            notification.transient(self)
            notification.attributes("-topmost", True)

            frame = ctk.CTkFrame(notification, corner_radius=12)
            frame.pack(fill="both", expand=True, padx=8, pady=8)

            ctk.CTkLabel(
                frame,
                text="Поступила новая заявка",
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=14, pady=(12, 4))

            ctk.CTkLabel(
                frame,
                text=f"№{display_number} · {title}",
                wraplength=315,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=14, pady=2)

            ctk.CTkLabel(
                frame,
                text=f"Отправитель: {author}",
                text_color="gray",
                anchor="w",
            ).pack(fill="x", padx=14, pady=(2, 10))

            # Размещаем уведомление в правом верхнем углу окна приложения.
            notification.update_idletasks()
            x = self.winfo_rootx() + self.winfo_width() - 380
            y = self.winfo_rooty() + 20
            notification.geometry(f"360x145+{max(x, 0)}+{max(y, 0)}")

            self._notification_windows.append(notification)

            def close_notification():
                if notification in self._notification_windows:
                    self._notification_windows.remove(notification)
                if notification.winfo_exists():
                    notification.destroy()

            notification.protocol("WM_DELETE_WINDOW", close_notification)
            notification.after(10000, close_notification)

            # Звуковой сигнал средствами Tkinter.
            self.bell()

        except Exception:
            # Ошибка отображения уведомления не должна ломать обновление заявок.
            pass

    
    # Автоматическое обновление
    

    def auto_refresh(self):
        if not self.winfo_exists() or not self.winfo_viewable():
            self._auto_refresh_id = None
            return

        self.load_requests(show_errors=False)

        self._auto_refresh_id = self.after(
            5000,
            self.auto_refresh,
        )

    
    # Настройки
    

    def show_settings(self):
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("Настройки")
        settings_window.geometry("380x230")
        settings_window.resizable(False, False)
        settings_window.transient(self)
        settings_window.grab_set()

        ctk.CTkLabel(
            settings_window,
            text="Настройки",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(24, 12))

        ctk.CTkLabel(
            settings_window,
            text="Цветовая тема приложения",
        ).pack(anchor="w", padx=24, pady=(4, 8))

        theme_selector = ctk.CTkSegmentedButton(
            settings_window,
            values=["Светлая", "Тёмная"],
            command=self.change_theme,
        )
        theme_selector.pack(anchor="w", padx=24, pady=8)

        theme_selector.set(
            "Тёмная"
            if ctk.get_appearance_mode() == "Dark"
            else "Светлая"
        )

    def change_theme(self, selected_theme):
        themes = {
            "Светлая": "Light",
            "Тёмная": "Dark",
        }

        ctk.set_appearance_mode(themes[selected_theme])
        self.update_table_theme()

    
    # Выход из аккаунта
    

    def logout(self):
        if self._auto_refresh_id is not None:
            try:
                self.after_cancel(self._auto_refresh_id)
            except Exception:
                pass

            self._auto_refresh_id = None

        for notification in self._notification_windows[:]:
            try:
                if notification.winfo_exists():
                    notification.destroy()
            except Exception:
                pass
        self._notification_windows.clear()

        self.withdraw()

        if self.master is not None and self.master.winfo_exists():
            self.master.deiconify()
            self.master.lift()

    
    # Выбор заявки
    

    def get_selected_request_id(self):
        selected_items = self.tree.selection()

        if not selected_items:
            messagebox.showwarning(
                "Внимание",
                "Сначала выберите заявку в таблице.",
                parent=self,
            )
            return None

        return int(selected_items[0])

    
    # Подробности заявки и фотография
    

    def show_request_details(self):
        request_id = self.get_selected_request_id()

        if request_id is None:
            return

        try:
            request = get_request_by_id(request_id)

            if request is None:
                messagebox.showwarning(
                    "Заявка не найдена",
                    "Возможно, заявка была удалена.",
                    parent=self,
                )
                self.load_requests(show_errors=False)
                return

            details_window = ctk.CTkToplevel(self)
            details_window.title(f"Заявка №{request_id}")
            details_window.geometry("720x700")
            details_window.minsize(500, 450)
            details_window.transient(self)

            details_window.grid_columnconfigure(0, weight=1)
            details_window.grid_rowconfigure(1, weight=1)

            ctk.CTkLabel(
                details_window,
                text=f"Заявка №{request['id']}",
                font=ctk.CTkFont(size=24, weight="bold"),
            ).grid(
                row=0,
                column=0,
                padx=20,
                pady=(20, 10),
                sticky="w",
            )

            content_frame = ctk.CTkScrollableFrame(details_window)
            content_frame.grid(
                row=1,
                column=0,
                padx=20,
                pady=10,
                sticky="nsew",
            )
            content_frame.grid_columnconfigure(0, weight=1)

            fields = [
                ("Название", request.get("title")),
                (
                    "Отправитель",
                    request.get(
                        "owner_username",
                        "Неизвестный пользователь",
                    ),
                ),
                ("Описание", request.get("description")),
                (
                    "Категория",
                    request.get("category_name", "Не указана"),
                ),
                (
                    "Приоритет",
                    request.get("priority_name", "Обычный"),
                ),
                (
                    "Статус",
                    request.get("status_name", "Не указан"),
                ),
                (
                    "Создана",
                    format_datetime(request.get("created_at")),
                ),
                (
                    "Последнее обновление",
                    format_datetime(request.get("updated_at")),
                ),
            ]

            for label_text, value in fields:
                ctk.CTkLabel(
                    content_frame,
                    text=f"{label_text}:",
                    font=ctk.CTkFont(weight="bold"),
                ).pack(anchor="w", pady=(7, 0))

                ctk.CTkLabel(
                    content_frame,
                    text=str(value or "Не указано"),
                    wraplength=620,
                    justify="left",
                ).pack(anchor="w", pady=(0, 7))

            ctk.CTkLabel(
                content_frame,
                text="Фотография:",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", pady=(15, 5))

            photo_data = get_request_photo(request_id)

            if photo_data:
                image = Image.open(
                    io.BytesIO(photo_data)
                ).convert("RGB")
                image.thumbnail((320, 220))

                preview_image = ctk.CTkImage(
                    light_image=image,
                    dark_image=image,
                    size=image.size,
                )

                preview_label = ctk.CTkLabel(
                    content_frame,
                    text="",
                    image=preview_image,
                    cursor="hand2",
                )
                preview_label.image = preview_image
                preview_label.pack(anchor="w", pady=5)

                ctk.CTkLabel(
                    content_frame,
                    text="Нажмите на фотографию, чтобы увеличить",
                    text_color="gray",
                ).pack(anchor="w", pady=(0, 10))

                preview_label.bind(
                    "<Button-1>",
                    lambda event, rid=request_id:
                    self.show_request_photo(rid),
                )
            else:
                ctk.CTkLabel(
                    content_frame,
                    text="К заявке не прикреплена фотография.",
                    text_color="gray",
                ).pack(anchor="w", pady=5)

        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось открыть заявку:\n{error}",
                parent=self,
            )

    
    # Полноразмерный просмотр фотографии
    

    def show_request_photo(self, request_id: int):
        try:
            photo_data = get_request_photo(request_id)

            if not photo_data:
                messagebox.showinfo(
                    "Фотография",
                    "У этой заявки нет прикреплённой фотографии.",
                    parent=self,
                )
                return

            image = Image.open(
                io.BytesIO(photo_data)
            ).convert("RGB")

            photo_window = ctk.CTkToplevel(self)
            photo_window.title(
                f"Фотография заявки №{request_id}"
            )
            photo_window.geometry("950x750")
            photo_window.minsize(400, 300)
            photo_window.transient(self)

            image.thumbnail((900, 650))

            photo_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=image.size,
            )

            photo_label = ctk.CTkLabel(
                photo_window,
                text="",
                image=photo_image,
            )
            photo_label.pack(
                expand=True,
                fill="both",
                padx=15,
                pady=15,
            )
            photo_label.image = photo_image

        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось открыть фотографию:\n{error}",
                parent=self,
            )

    
    # Изменение статуса
    

    def change_request_status(self):
        request_id = self.get_selected_request_id()

        if request_id is None:
            return

        try:
            request = get_request_by_id(request_id)

            if request is None:
                messagebox.showwarning(
                    "Заявка не найдена",
                    "Возможно, заявка была удалена.",
                    parent=self,
                )
                self.load_requests(show_errors=False)
                return

            status_window = ctk.CTkToplevel(self)
            status_window.title("Изменение статуса")
            status_window.geometry("350x250")
            status_window.resizable(False, False)
            status_window.transient(self)
            status_window.grab_set()

            ctk.CTkLabel(
                status_window,
                text=f"Заявка №{request_id}",
                font=ctk.CTkFont(size=18, weight="bold"),
            ).pack(padx=20, pady=(20, 10))

            ctk.CTkLabel(
                status_window,
                text="Выберите новый статус:",
            ).pack(padx=20, pady=5)

            available_statuses = [
                "Новая",
                "В работе",
                "Завершена",
                "Отменена",
            ]

            if request["status"] != "new":
                available_statuses.remove("Новая")

            status_menu = ctk.CTkOptionMenu(
                status_window,
                values=available_statuses,
            )
            status_menu.set(request["status_name"])
            status_menu.pack(padx=20, pady=10)

            def save_status():
                try:
                    success = update_request_status(
                        request_id,
                        status_menu.get(),
                    )

                    if success:
                        status_window.destroy()
                        self.load_requests(show_errors=False)

                        messagebox.showinfo(
                            "Успешно",
                            "Статус заявки изменён.",
                            parent=self,
                        )
                    else:
                        messagebox.showwarning(
                            "Внимание",
                            "Заявка не найдена.",
                            parent=status_window,
                        )

                except Exception as error:
                    messagebox.showerror(
                        "Ошибка",
                        f"Не удалось изменить статус:\n{error}",
                        parent=status_window,
                    )

            ctk.CTkButton(
                status_window,
                text="Сохранить",
                command=save_status,
            ).pack(padx=20, pady=15)

        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось изменить статус:\n{error}",
                parent=self,
            )

    
    # Удаление заявки
    

    def delete_selected_request(self):
        request_id = self.get_selected_request_id()

        if request_id is None:
            return

        confirmed = messagebox.askyesno(
            "Подтверждение удаления",
            f"Вы действительно хотите удалить заявку №{request_id}?",
            parent=self,
        )

        if not confirmed:
            return

        try:
            success = delete_request(request_id)

            if success:
                self.load_requests(show_errors=False)
                messagebox.showinfo(
                    "Успешно",
                    "Заявка удалена.",
                    parent=self,
                )
            else:
                messagebox.showwarning(
                    "Внимание",
                    "Заявка не найдена или уже удалена.",
                    parent=self,
                )

        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось удалить заявку:\n{error}",
                parent=self,
            )

