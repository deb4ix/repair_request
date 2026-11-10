
import io
from pathlib import Path

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from PIL import Image

from services.request_service import (
    get_all_requests,
    get_request_by_id,
    get_request_photo,
    get_categories,
    create_request,
    update_request,
    delete_request,
)


PRIORITY_OPTIONS = {
    "Низкий": "low",
    "Обычный": "normal",
    "Высокий": "high",
    "Критический": "critical",
}

PRIORITY_NAMES = {
    value: key for key, value in PRIORITY_OPTIONS.items()
}

STATUS_FILTER_VALUES = [
    "Все статусы",
    "Новая",
    "В работе",
    "Завершена",
    "Отменена",
]


class MainWindow(ctk.CTkToplevel):
    def __init__(self, user, master=None):
        super().__init__(master)

        self.current_user = user
        self.title(f"Учёт заявок на ремонт — {user['username']}")
        self.geometry("1200x720")
        self.minsize(850, 600)
        self.protocol("WM_DELETE_WINDOW", self.logout)

        self.selected_photo_path = None
        self.remove_existing_photo = False

        self.categories = []
        self.category_name_to_id = {}
        self.category_id_to_name = {}

        self.create_widgets()
        self.update_table_theme()
        self.show_requests()
        self.load_requests()

    # --------------------------------------------------
    # Категории
    # --------------------------------------------------

    def load_categories(self):
        categories = get_categories()

        if not categories:
            raise ValueError(
                "В базе данных нет категорий заявок. "
                "Проверьте таблицу request_categories."
            )

        self.categories = categories
        self.category_name_to_id = {
            name: category_id
            for category_id, name in categories
        }
        self.category_id_to_name = {
            category_id: name
            for category_id, name in categories
        }

        return categories

    def get_category_values(self):
        return [name for _, name in self.categories]

    def update_category_filter(self):
        """Обновляет значения фильтра категорий."""
        try:
            self.load_categories()
            values = ["Все категории"] + self.get_category_values()

            current = self.category_filter.get()
            self.category_filter.configure(values=values)

            if current not in values:
                self.category_filter.set("Все категории")

        except Exception as error:
            self.category_filter.configure(
                values=["Все категории"]
            )
            self.category_filter.set("Все категории")
            raise error

    # --------------------------------------------------
    # Оформление таблицы
    # --------------------------------------------------

    def update_table_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        if ctk.get_appearance_mode() == "Dark":
            background = "#242424"
            foreground = "#FFFFFF"
            heading_background = "#333333"
            selected_background = "#1F6AA5"
            border_color = "#444444"

            status_colors = {
                "new": ("#183B2A", "#B7F7CC"),
                "in_progress": ("#193653", "#BFDBFE"),
                "completed": ("#383838", "#E5E7EB"),
                "cancelled": ("#4A2222", "#FECACA"),
            }
        else:
            background = "#FFFFFF"
            foreground = "#000000"
            heading_background = "#E5E5E5"
            selected_background = "#3B8ED0"
            border_color = "#D0D0D0"

            status_colors = {
                "new": ("#D9F2DF", "#14532D"),
                "in_progress": ("#DCEBFA", "#1E40AF"),
                "completed": ("#E5E7EB", "#374151"),
                "cancelled": ("#FADBD8", "#991B1B"),
            }

        style.configure(
            "Treeview",
            background=background,
            foreground=foreground,
            fieldbackground=background,
            rowheight=32,
            bordercolor=border_color,
            borderwidth=0,
        )

        style.configure(
            "Treeview.Heading",
            background=heading_background,
            foreground=foreground,
            font=("Arial", 10, "bold"),
            relief="flat",
        )

        style.map(
            "Treeview",
            background=[("selected", selected_background)],
            foreground=[("selected", "#FFFFFF")],
        )

        style.map(
            "Treeview.Heading",
            background=[("active", heading_background)],
        )

        for tag_name, colors in status_colors.items():
            self.request_table.tag_configure(
                tag_name,
                background=colors[0],
                foreground=colors[1],
            )

    @staticmethod
    def get_status_tag(status):
        normalized = (status or "").strip().casefold()

        status_tags = {
            "новая": "new",
            "new": "new",
            "в работе": "in_progress",
            "in progress": "in_progress",
            "in_progress": "in_progress",
            "завершена": "completed",
            "завершено": "completed",
            "completed": "completed",
            "отменена": "cancelled",
            "отменено": "cancelled",
            "cancelled": "cancelled",
            "canceled": "cancelled",
        }

        return status_tags.get(normalized, "")

    # --------------------------------------------------
    # Создание интерфейса
    # --------------------------------------------------

    def create_widgets(self):
        self.sidebar = ctk.CTkFrame(self, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = ctk.CTkFrame(self)
        self.content.pack(
            side="right",
            fill="both",
            expand=True,
        )

        self.sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="Учёт заявок на ремонт",
            font=("Arial", 18, "bold"),
            wraplength=180,
        )
        self.sidebar_title.pack(padx=15, pady=(25, 30))

        self.requests_button = ctk.CTkButton(
            self.sidebar,
            text="Заявки",
            command=self.show_requests,
        )
        self.requests_button.pack(fill="x", padx=15, pady=5)

        self.settings_button = ctk.CTkButton(
            self.sidebar,
            text="Настройки",
            command=self.show_settings,
        )
        self.settings_button.pack(fill="x", padx=15, pady=5)

        self.account_label = ctk.CTkLabel(
            self.sidebar,
            text=f"Вход: {self.current_user['username']}",
            wraplength=185,
        )
        self.account_label.pack(
            side="bottom",
            padx=12,
            pady=(5, 10),
        )

        self.logout_button = ctk.CTkButton(
            self.sidebar,
            text="Выйти из аккаунта",
            command=self.logout,
            fg_color="#555555",
            hover_color="#333333",
        )
        self.logout_button.pack(
            side="bottom",
            fill="x",
            padx=15,
            pady=(5, 0),
        )

        self.page_title = ctk.CTkLabel(
            self.content,
            text="Заявки на ремонт",
            font=("Arial", 26, "bold"),
        )
        self.page_title.pack(
            anchor="w",
            padx=30,
            pady=(25, 5),
        )

        self.page_description = ctk.CTkLabel(
            self.content,
            text="Просмотр и управление собственными заявками",
        )
        self.page_description.pack(
            anchor="w",
            padx=30,
            pady=(0, 20),
        )

        self.requests_frame = ctk.CTkFrame(self.content)

        search_frame = ctk.CTkFrame(
            self.requests_frame,
            fg_color="transparent",
        )
        search_frame.pack(
            fill="x",
            padx=10,
            pady=(10, 5),
        )

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Поиск по названию заявки...",
        )
        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5),
            pady=5,
        )
        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_requests(),
        )

        self.status_filter = ctk.CTkComboBox(
            search_frame,
            values=STATUS_FILTER_VALUES,
            command=lambda value: self.load_requests(),
            width=150,
            state="readonly",
        )
        self.status_filter.pack(
            side="left",
            padx=5,
            pady=5,
        )
        self.status_filter.set("Все статусы")

        self.category_filter = ctk.CTkComboBox(
            search_frame,
            values=["Все категории"],
            command=lambda value: self.load_requests(),
            width=210,
            state="readonly",
        )
        self.category_filter.pack(
            side="left",
            padx=(5, 0),
            pady=5,
        )
        self.category_filter.set("Все категории")

        self.request_actions = ctk.CTkFrame(
            self.requests_frame,
            fg_color="transparent",
        )
        self.request_actions.pack(
            fill="x",
            padx=10,
            pady=10,
        )

        ctk.CTkButton(
            self.request_actions,
            text="Добавить заявку",
            command=self.open_create_request,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            self.request_actions,
            text="Обновить",
            command=self.load_requests,
            fg_color="gray",
            hover_color="#555555",
        ).pack(side="left")

        ctk.CTkButton(
            self.request_actions,
            text="Подробнее",
            command=self.show_request_details,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            self.request_actions,
            text="Удалить заявку",
            command=self.delete_selected_request,
            fg_color="#C62828",
            hover_color="#8E0000",
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            self.request_actions,
            text="Редактировать",
            command=self.open_edit_request,
        ).pack(side="left", padx=(10, 0))

        self.request_table = ttk.Treeview(
            self.requests_frame,
            columns=(
                "id",
                "title",
                "category",
                "status",
                "author",
            ),
            show="headings",
            selectmode="browse",
        )

        self.request_table.heading("id", text="Номер")
        self.request_table.heading("title", text="Название заявки")
        self.request_table.heading("category", text="Категория")
        self.request_table.heading("status", text="Статус")
        self.request_table.heading("author", text="Отправитель")

        self.request_table.column(
            "id", width=65, anchor="center", stretch=False
        )
        self.request_table.column(
            "title", width=300, anchor="w"
        )
        self.request_table.column(
            "category", width=190, anchor="center"
        )
        self.request_table.column(
            "status", width=125, anchor="center"
        )
        self.request_table.column(
            "author", width=150, anchor="center"
        )

        self.request_table.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )

        self.request_table.bind(
            "<Double-1>",
            lambda event: self.show_request_details(),
        )

    # --------------------------------------------------
    # Страницы
    # --------------------------------------------------

    def show_requests(self):
        self.page_title.configure(text="Заявки на ремонт")
        self.page_description.configure(
            text="Просмотр и управление собственными заявками"
        )

        if hasattr(self, "settings_frame"):
            self.settings_frame.pack_forget()

        if not self.requests_frame.winfo_manager():
            self.requests_frame.pack(
                fill="both",
                expand=True,
                padx=30,
                pady=(0, 30),
            )

    # --------------------------------------------------
    # Загрузка и фильтрация заявок
    # --------------------------------------------------

    def load_requests(self):
        try:
            requests = get_all_requests(
                owner_id=self.current_user["id"]
            )

            # Справочник категорий нужен также для фильтра.
            self.update_category_filter()

            search_text = (
                self.search_entry.get().strip().casefold()
            )
            selected_status = (
                self.status_filter.get().strip().casefold()
            )
            selected_category = self.category_filter.get()

            for item in self.request_table.get_children():
                self.request_table.delete(item)

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
                    and status.casefold() != selected_status
                ):
                    continue

                if (
                    selected_category != "Все категории"
                    and category_name != selected_category
                ):
                    continue

                status_tag = self.get_status_tag(status)
                tags = (status_tag,) if status_tag else ()

                self.request_table.insert(
                    "",
                    "end",
                    iid=str(request_id),
                    values=(
                        request_id,
                        title,
                        category_name,
                        status,
                        author,
                    ),
                    tags=tags,
                )

        except Exception as error:
            messagebox.showerror(
                "Ошибка загрузки",
                f"Не удалось загрузить заявки:\n{error}",
                parent=self,
            )

    def get_selected_request_id(self):
        selected_items = self.request_table.selection()

        if not selected_items:
            messagebox.showwarning(
                "Заявка не выбрана",
                "Сначала выберите заявку в таблице.",
                parent=self,
            )
            return None

        return int(selected_items[0])

    # --------------------------------------------------
    # Подробности заявки
    # --------------------------------------------------

    def show_request_details(self):
        request_id = self.get_selected_request_id()

        if request_id is None:
            return

        try:
            request = get_request_by_id(
                request_id,
                self.current_user["id"],
            )

            if request is None:
                messagebox.showwarning(
                    "Заявка не найдена",
                    "Возможно, заявка уже была удалена.",
                    parent=self,
                )
                self.load_requests()
                return

            details_window = ctk.CTkToplevel(self)
            details_window.title(f"Заявка №{request_id}")
            details_window.geometry("700x650")
            details_window.minsize(500, 400)
            details_window.transient(self)

            details_window.grid_columnconfigure(0, weight=1)
            details_window.grid_rowconfigure(1, weight=1)

            ctk.CTkLabel(
                details_window,
                text=f"Заявка №{request_id}",
                font=ctk.CTkFont(size=24, weight="bold"),
            ).grid(
                row=0,
                column=0,
                padx=20,
                pady=(20, 10),
                sticky="w",
            )

            content = ctk.CTkScrollableFrame(details_window)
            content.grid(
                row=1,
                column=0,
                padx=20,
                pady=10,
                sticky="nsew",
            )
            content.grid_columnconfigure(0, weight=1)

            fields = [
                ("Название", request["title"]),
                (
                    "Отправитель",
                    request.get(
                        "owner_username",
                        "Неизвестный пользователь",
                    ),
                ),
                ("Описание", request["description"]),
                ("Категория", request.get("category_name", "Не указана")),
                ("Приоритет", request.get("priority_name", "Обычный")),
                ("Статус", request["status_name"]),
                ("Создана", request["created_at"]),
                ("Последнее обновление", request["updated_at"]),
            ]

            for label_text, value in fields:
                ctk.CTkLabel(
                    content,
                    text=f"{label_text}:",
                    font=ctk.CTkFont(weight="bold"),
                ).pack(anchor="w", pady=(10, 2))

                ctk.CTkLabel(
                    content,
                    text=str(value or "Не указано"),
                    wraplength=580,
                    justify="left",
                ).pack(anchor="w", pady=(0, 5))

            ctk.CTkButton(
                details_window,
                text="Просмотреть фотографию",
                command=lambda rid=request_id: self.show_request_photo(rid),
            ).grid(
                row=2,
                column=0,
                padx=20,
                pady=15,
            )

        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось открыть заявку:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # Фотографии
    # --------------------------------------------------

    def show_request_photo(self, request_id):
        try:
            photo_data = get_request_photo(
                request_id,
                self.current_user["id"],
            )

            if not photo_data:
                messagebox.showinfo(
                    "Фотография",
                    "У этой заявки нет фотографии.",
                    parent=self,
                )
                return

            image = Image.open(io.BytesIO(photo_data))
            image.load()
            image.thumbnail((900, 650))

            photo_window = ctk.CTkToplevel(self)
            photo_window.title(f"Фотография заявки №{request_id}")
            photo_window.geometry("950x750")
            photo_window.minsize(400, 300)
            photo_window.transient(self)

            photo_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=image.size,
            )

            image_label = ctk.CTkLabel(
                photo_window,
                text="",
                image=photo_image,
            )
            image_label.pack(
                expand=True,
                fill="both",
                padx=15,
                pady=15,
            )
            image_label.image = photo_image

        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось открыть фотографию:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # Удаление заявки
    # --------------------------------------------------

    def delete_selected_request(self):
        request_id = self.get_selected_request_id()

        if request_id is None:
            return

        selected = self.request_table.selection()
        values = self.request_table.item(selected[0], "values")
        request_title = values[1]

        confirmed = messagebox.askyesno(
            "Подтверждение удаления",
            f"Удалить заявку №{request_id} "
            f"«{request_title}»?\n\n"
            "Это действие нельзя отменить.",
            parent=self,
        )

        if not confirmed:
            return

        try:
            deleted = delete_request(
                request_id,
                self.current_user["id"],
            )

            if deleted:
                self.load_requests()
                messagebox.showinfo(
                    "Удаление выполнено",
                    f"Заявка №{request_id} удалена.",
                    parent=self,
                )
            else:
                messagebox.showwarning(
                    "Заявка не найдена",
                    "Возможно, заявка уже была удалена.",
                    parent=self,
                )
                self.load_requests()

        except Exception as error:
            messagebox.showerror(
                "Ошибка удаления",
                f"Не удалось удалить заявку:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # Поля категории и приоритета
    # --------------------------------------------------

    def create_category_controls(
        self,
        parent,
        category_id=None,
        priority="normal",
    ):
        ctk.CTkLabel(
            parent,
            text="Категория заявки",
        ).pack(anchor="w", padx=25, pady=(0, 5))

        category_names = self.get_category_values()

        self.category_selector = ctk.CTkComboBox(
            parent,
            values=category_names,
            state="readonly",
        )
        self.category_selector.pack(
            fill="x",
            padx=25,
            pady=(0, 15),
        )

        selected_category = self.category_id_to_name.get(
            category_id,
            category_names[0],
        )
        self.category_selector.set(selected_category)

        ctk.CTkLabel(
            parent,
            text="Приоритет заявки",
        ).pack(anchor="w", padx=25, pady=(0, 5))

        self.priority_selector = ctk.CTkComboBox(
            parent,
            values=list(PRIORITY_OPTIONS.keys()),
            state="readonly",
        )
        self.priority_selector.pack(
            fill="x",
            padx=25,
            pady=(0, 15),
        )
        self.priority_selector.set(
            PRIORITY_NAMES.get(priority, "Обычный")
        )

    def get_form_category_id(self):
        category_name = self.category_selector.get()
        category_id = self.category_name_to_id.get(category_name)

        if category_id is None:
            raise ValueError("Выберите категорию заявки.")

        return category_id

    def get_form_priority(self):
        priority_name = self.priority_selector.get()
        priority = PRIORITY_OPTIONS.get(priority_name)

        if priority is None:
            raise ValueError("Выберите приоритет заявки.")

        return priority

    # --------------------------------------------------
    # Редактирование заявки
    # --------------------------------------------------

    def open_edit_request(self):
        request_id = self.get_selected_request_id()

        if request_id is None:
            return

        try:
            request = get_request_by_id(
                request_id,
                self.current_user["id"],
            )

            if request is None:
                messagebox.showwarning(
                    "Нет доступа",
                    "Вы можете редактировать только собственные заявки.",
                    parent=self,
                )
                return

            self.load_categories()

            self.editing_request_id = request_id
            self.selected_photo_path = None
            self.remove_existing_photo = False

            has_photo = (
                get_request_photo(
                    request_id,
                    self.current_user["id"],
                ) is not None
            )

            self.request_window = ctk.CTkToplevel(self)
            self.request_window.title(
                f"Редактирование заявки №{request_id}"
            )
            self.request_window.geometry("500x850")
            self.request_window.minsize(450, 750)
            self.request_window.transient(self)
            self.request_window.grab_set()

            ctk.CTkLabel(
                self.request_window,
                text=f"Редактирование заявки №{request_id}",
                font=("Arial", 22, "bold"),
            ).pack(anchor="w", padx=25, pady=(25, 20))

            ctk.CTkLabel(
                self.request_window,
                text="Название заявки",
            ).pack(anchor="w", padx=25, pady=(0, 5))

            self.request_title_entry = ctk.CTkEntry(
                self.request_window,
                placeholder_text="Название заявки",
            )
            self.request_title_entry.pack(
                fill="x",
                padx=25,
                pady=(0, 15),
            )
            self.request_title_entry.insert(0, request["title"] or "")

            self.create_category_controls(
                self.request_window,
                category_id=request.get("category_id"),
                priority=request.get("priority", "normal"),
            )

            ctk.CTkLabel(
                self.request_window,
                text="Описание проблемы",
            ).pack(anchor="w", padx=25, pady=(0, 5))

            self.request_description_entry = ctk.CTkTextbox(
                self.request_window,
                height=130,
            )
            self.request_description_entry.pack(
                fill="both",
                expand=True,
                padx=25,
                pady=(0, 15),
            )
            self.request_description_entry.insert(
                "1.0",
                request["description"] or "",
            )

            ctk.CTkLabel(
                self.request_window,
                text="Фотография поломки",
                font=("Arial", 15, "bold"),
            ).pack(anchor="w", padx=25, pady=(0, 5))

            self.edit_photo_label = ctk.CTkLabel(
                self.request_window,
                text=(
                    "Фотография прикреплена"
                    if has_photo
                    else "Фотография отсутствует"
                ),
                wraplength=400,
            )
            self.edit_photo_label.pack(
                anchor="w",
                padx=25,
                pady=(0, 8),
            )

            ctk.CTkButton(
                self.request_window,
                text="Выбрать новую фотографию",
                command=self.choose_edit_photo,
            ).pack(anchor="w", padx=25, pady=(0, 5))

            ctk.CTkButton(
                self.request_window,
                text="Удалить фотографию",
                command=self.remove_edit_photo,
                fg_color="#C62828",
                hover_color="#8E0000",
            ).pack(anchor="w", padx=25, pady=(0, 15))

            ctk.CTkButton(
                self.request_window,
                text="Сохранить изменения",
                command=self.save_edit_request,
            ).pack(fill="x", padx=25, pady=(0, 25))

            self.request_title_entry.focus()

        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось открыть заявку:\n{error}",
                parent=self,
            )

    def choose_edit_photo(self):
        file_path = filedialog.askopenfilename(
            parent=self.request_window,
            title="Выберите новую фотографию",
            filetypes=[
                ("Фотографии", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("Все файлы", "*.*"),
            ],
        )

        if not file_path:
            return

        photo_path = Path(file_path)
        allowed_extensions = {
            ".png", ".jpg", ".jpeg", ".webp", ".bmp"
        }

        if photo_path.suffix.lower() not in allowed_extensions:
            messagebox.showwarning(
                "Неверный формат",
                "Выберите PNG, JPG, JPEG, WEBP или BMP.",
                parent=self.request_window,
            )
            return

        self.selected_photo_path = str(photo_path)
        self.remove_existing_photo = False
        self.edit_photo_label.configure(
            text=f"Новая фотография: {photo_path.name}"
        )

    def remove_edit_photo(self):
        self.selected_photo_path = None
        self.remove_existing_photo = True
        self.edit_photo_label.configure(
            text="Фотография будет удалена после сохранения"
        )

    def save_edit_request(self):
        title = self.request_title_entry.get().strip()
        description = (
            self.request_description_entry.get("1.0", "end").strip()
        )

        try:
            updated = update_request(
                self.editing_request_id,
                title,
                description,
                photo_path=self.selected_photo_path,
                remove_photo=self.remove_existing_photo,
                owner_id=self.current_user["id"],
                category_id=self.get_form_category_id(),
                priority=self.get_form_priority(),
            )

            if not updated:
                messagebox.showwarning(
                    "Заявка не найдена",
                    "Не удалось найти заявку для обновления.",
                    parent=self.request_window,
                )
                return

            messagebox.showinfo(
                "Успешно",
                f"Заявка №{self.editing_request_id} обновлена.",
                parent=self.request_window,
            )

            self.request_window.destroy()
            self.load_requests()

        except ValueError as error:
            messagebox.showwarning(
                "Проверьте данные",
                str(error),
                parent=self.request_window,
            )

        except Exception as error:
            messagebox.showerror(
                "Ошибка сохранения",
                f"Не удалось обновить заявку:\n{error}",
                parent=self.request_window,
            )

    # --------------------------------------------------
    # Создание заявки
    # --------------------------------------------------

    def open_create_request(self):
        try:
            self.load_categories()
        except Exception as error:
            messagebox.showerror(
                "Ошибка категорий",
                f"Не удалось загрузить категории:\n{error}",
                parent=self,
            )
            return

        self.selected_photo_path = None

        self.request_window = ctk.CTkToplevel(self)
        self.request_window.title("Новая заявка")
        self.request_window.geometry("500x850")
        self.request_window.minsize(450, 750)
        self.request_window.transient(self)
        self.request_window.grab_set()

        ctk.CTkLabel(
            self.request_window,
            text="Создание заявки",
            font=("Arial", 22, "bold"),
        ).pack(anchor="w", padx=25, pady=(25, 20))

        ctk.CTkLabel(
            self.request_window,
            text="Название заявки",
        ).pack(anchor="w", padx=25, pady=(0, 5))

        self.request_title_entry = ctk.CTkEntry(
            self.request_window,
            placeholder_text="Например, ремонт компьютера",
        )
        self.request_title_entry.pack(
            fill="x",
            padx=25,
            pady=(0, 15),
        )

        self.create_category_controls(
            self.request_window,
            priority="normal",
        )

        ctk.CTkLabel(
            self.request_window,
            text="Фотография поломки",
        ).pack(anchor="w", padx=25, pady=(0, 5))

        ctk.CTkButton(
            self.request_window,
            text="Выбрать фотографию",
            command=self.select_photo,
        ).pack(anchor="w", padx=25, pady=(0, 5))

        self.photo_label = ctk.CTkLabel(
            self.request_window,
            text="Фотография не выбрана",
            wraplength=400,
        )
        self.photo_label.pack(anchor="w", padx=25, pady=(0, 5))

        ctk.CTkButton(
            self.request_window,
            text="Убрать фотографию",
            command=self.remove_photo,
            fg_color="gray",
            hover_color="#555555",
        ).pack(anchor="w", padx=25, pady=(0, 15))

        ctk.CTkLabel(
            self.request_window,
            text="Описание проблемы",
        ).pack(anchor="w", padx=25, pady=(0, 5))

        self.request_description_entry = ctk.CTkTextbox(
            self.request_window,
            height=130,
        )
        self.request_description_entry.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=(0, 20),
        )

        ctk.CTkButton(
            self.request_window,
            text="Сохранить заявку",
            command=self.save_request,
        ).pack(fill="x", padx=25, pady=(0, 25))

        self.request_title_entry.focus()

    def select_photo(self):
        file_path = filedialog.askopenfilename(
            parent=self.request_window,
            title="Выберите фотографию поломки",
            filetypes=[
                ("Фотографии", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("Все файлы", "*.*"),
            ],
        )

        if not file_path:
            return

        photo_path = Path(file_path)
        allowed_extensions = {
            ".png", ".jpg", ".jpeg", ".webp", ".bmp"
        }

        if photo_path.suffix.lower() not in allowed_extensions:
            messagebox.showwarning(
                "Неверный формат",
                "Выберите PNG, JPG, JPEG, WEBP или BMP.",
                parent=self.request_window,
            )
            return

        self.selected_photo_path = str(photo_path)
        self.photo_label.configure(
            text=f"Выбрано: {photo_path.name}"
        )

    def remove_photo(self):
        self.selected_photo_path = None
        self.photo_label.configure(text="Фотография не выбрана")

    def save_request(self):
        title = self.request_title_entry.get().strip()
        description = (
            self.request_description_entry.get("1.0", "end").strip()
        )

        try:
            request_id = create_request(
                title,
                description,
                photo_path=self.selected_photo_path,
                owner_id=self.current_user["id"],
                category_id=self.get_form_category_id(),
                priority=self.get_form_priority(),
            )

            messagebox.showinfo(
                "Успешно",
                f"Заявка №{request_id} создана.",
                parent=self.request_window,
            )

            self.request_window.destroy()
            self.show_requests()
            self.load_requests()

        except ValueError as error:
            messagebox.showwarning(
                "Проверьте данные",
                str(error),
                parent=self.request_window,
            )

        except Exception as error:
            messagebox.showerror(
                "Ошибка сохранения",
                f"Не удалось сохранить заявку:\n{error}",
                parent=self.request_window,
            )

    # --------------------------------------------------
    # Настройки и выход
    # --------------------------------------------------

    def show_settings(self):
        self.page_title.configure(text="Настройки")
        self.page_description.configure(
            text="Настройки приложения"
        )
        self.requests_frame.pack_forget()

        if hasattr(self, "settings_frame"):
            self.settings_frame.destroy()

        self.settings_frame = ctk.CTkFrame(self.content)
        self.settings_frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 30),
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Внешний вид",
            font=("Arial", 20, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            self.settings_frame,
            text="Цветовая тема приложения",
        ).pack(anchor="w", padx=20, pady=(0, 15))

        self.theme_selector = ctk.CTkSegmentedButton(
            self.settings_frame,
            values=["Светлая", "Тёмная"],
            command=self.change_theme,
        )
        self.theme_selector.pack(anchor="w", padx=20, pady=10)

        self.theme_selector.set(
            "Светлая"
            if ctk.get_appearance_mode() == "Light"
            else "Тёмная"
        )

    def logout(self):
        self.withdraw()

        if self.master is not None and self.master.winfo_exists():
            self.master.deiconify()
            self.master.lift()

    def change_theme(self, selected_theme):
        themes = {
            "Светлая": "Light",
            "Тёмная": "Dark",
        }

        ctk.set_appearance_mode(themes[selected_theme])
        self.update_table_theme()
