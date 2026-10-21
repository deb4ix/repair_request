import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from services.request_service import (
    get_all_requests,
    create_request,
    delete_request,
)

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Учёт заявок на ремонт")
        self.geometry("1100x700")
        self.minsize(800, 600)

        self.create_widgets()
        self.show_requests()
        self.load_requests()

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
        self.sidebar_title.pack(
            padx=15,
            pady=(25, 30),
        )

        self.requests_button = ctk.CTkButton(
            self.sidebar,
            text="Заявки",
            command=self.show_requests,
        )
        self.requests_button.pack(
            fill="x",
            padx=15,
            pady=5,
        )

        self.settings_button = ctk.CTkButton(
            self.sidebar,
            text="Настройки",
            command=self.show_settings,
        )
        self.settings_button.pack(
            fill="x",
            padx=15,
            pady=5,
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
            text="Просмотр и управление заявками",
        )
        self.page_description.pack(
            anchor="w",
            padx=30,
            pady=(0, 20),
        )

        self.requests_frame = ctk.CTkFrame(
            self.content,
        )

        self.request_actions = ctk.CTkFrame(
            self.requests_frame,
            fg_color="transparent",
        )
        self.request_actions.pack(
            fill="x",
            padx=10,
            pady=10,
        )

        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=(10, 5))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Поиск по названию заявки..."
        )
        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(10, 5),
            pady=10
        )

        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_requests()
        )

        self.status_filter = ctk.CTkComboBox(
            search_frame,
            values=[
                "Все статусы",
                "Новая",
                "В работе",
                "Завершена"
            ],
            command=lambda value: self.load_requests(),
            width=160
        )
        self.status_filter.pack(
            side="left",
            padx=(5, 10),
            pady=10
        )
        self.status_filter.set("Все статусы")

        self.add_request_button = ctk.CTkButton(
            self.request_actions,
            text="Добавить заявку",
            command=self.open_create_request,
        )
        self.add_request_button.pack(
            side="left",
            padx=(0, 10),
        )

        self.refresh_button = ctk.CTkButton(
            self.request_actions,
            text="Обновить",
            command=self.load_requests,
            fg_color="gray",
            hover_color="#555555",
        )
        self.refresh_button.pack(
            side="left",
        )

        self.delete_button = ctk.CTkButton(
            self.request_actions,
            text="Удалить заявку",
            command=self.delete_selected_request,
            fg_color="#C62828",
            hover_color="#8E0000",
        )
        self.delete_button.pack(
            side="left",
            padx=(10, 0),
        )

        self.request_table = ttk.Treeview(
            self.requests_frame,
            columns=("id", "title", "status"),
            show="headings",
            selectmode="browse",
        )

        self.request_table.heading(
            "id",
            text="Номер",
        )
        self.request_table.heading(
            "title",
            text="Название заявки",
        )
        self.request_table.heading(
            "status",
            text="Статус",
        )

        self.request_table.column(
            "id",
            width=70,
            anchor="center",
            stretch=False,
        )
        self.request_table.column(
            "title",
            width=400,
            anchor="w",
        )
        self.request_table.column(
            "status",
            width=150,
            anchor="center",
        )

        self.request_table.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 10),
        )

    def show_requests(self):
        self.page_title.configure(
            text="Заявки на ремонт",
        )
        self.page_description.configure(
            text="Просмотр и управление заявками",
        )

        if hasattr(self, "settings_frame"):
            self.settings_frame.pack_forget()

        self.requests_frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 30),
        )

    def load_requests(self):
        requests = get_all_requests()

        search_text = self.search_entry.get().strip().lower()

        selected_status = self.status_filter.get()

        for item in self.request_table.get_children():
            self.request_table.delete(item)

        for request in requests:
            request_id, title, status = request

            if search_text and search_text not in title.lower():
                continue

            if (
                    selected_status != "Все статусы"
                    and status != selected_status
            ):
                continue

            self.request_table.insert(
                "",
                "end",
                values=(request_id, title, status),
            )

    def delete_selected_request(self):
        selected_items = self.request_table.selection()

        if not selected_items:
            messagebox.showwarning(
                "Заявка не выбрана",
                "Сначала выберите заявку в таблице.",
                parent=self,
            )
            return

        selected_item = selected_items[0]
        values = self.request_table.item(
            selected_item,
            "values",
        )

        if not values or len(values) < 2:
            messagebox.showerror(
                "Ошибка",
                "Не удалось получить данные выбранной заявки.",
                parent=self,
            )
            return

        try:
            request_id = int(values[0])
        except (ValueError, TypeError):
            messagebox.showerror(
                "Ошибка",
                "Не удалось определить номер заявки.",
                parent=self,
            )
            return

        request_title = values[1]

        confirmed = messagebox.askyesno(
            "Подтверждение удаления",
            f"Вы действительно хотите удалить заявку "
            f"№{request_id} «{request_title}»?\n\n"
            "Это действие нельзя отменить.",
            parent=self,
        )

        if not confirmed:
            return

        try:
            deleted = delete_request(request_id)

            if deleted:
                self.load_requests()

                messagebox.showinfo(
                    "Удаление выполнено",
                    f"Заявка №{request_id} успешно удалена.",
                    parent=self,
                )
            else:
                messagebox.showwarning(
                    "Заявка не найдена",
                    f"Заявка №{request_id} не найдена в базе данных.",
                    parent=self,
                )

                self.load_requests()

        except Exception as error:
            messagebox.showerror(
                "Ошибка удаления",
                f"Не удалось удалить заявку:\n{error}",
                parent=self,
            )

    def open_create_request(self):
        self.selected_photo_path = None
        self.request_window = ctk.CTkToplevel(self)
        self.request_window.title("Новая заявка")
        self.request_window.geometry("500x700")
        self.request_window.minsize(500, 650)
        self.request_window.transient(self)
        self.request_window.grab_set()

        ctk.CTkLabel(
            self.request_window,
            text="Создание заявки",
            font=("Arial", 22, "bold"),
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 20),
        )

        ctk.CTkLabel(
            self.request_window,
            text="Название заявки",
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 5),
        )

        self.request_title_entry = ctk.CTkEntry(
            self.request_window,
            placeholder_text="Например, ремонт компьютера",
        )
        self.request_title_entry.pack(
            fill="x",
            padx=25,
            pady=(0, 15),
        )

        ctk.CTkLabel(
            self.request_window,
            text="Фотография поломки",
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 5),
        )

        self.select_photo_button = ctk.CTkButton(
            self.request_window,
            text="Выбрать фотографию",
            command=self.select_photo,
        )
        self.select_photo_button.pack(
            anchor="w",
            padx=25,
            pady=(0, 5),
        )

        self.photo_label = ctk.CTkLabel(
            self.request_window,
            text="Фотография не выбрана",
            wraplength=400,
        )
        self.photo_label.pack(
            anchor="w",
            padx=25,
            pady=(0, 5),
        )

        self.remove_photo_button = ctk.CTkButton(
            self.request_window,
            text="Убрать фотографию",
            command=self.remove_photo,
            fg_color="gray",
            hover_color="#555555",
        )
        self.remove_photo_button.pack(
            anchor="w",
            padx=25,
            pady=(0, 15),
        )

        ctk.CTkLabel(
            self.request_window,
            text="Описание проблемы",
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 5),
        )

        self.request_description_entry = ctk.CTkTextbox(
            self.request_window,
            height=150,
        )
        self.request_description_entry.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=(0, 20),
        )

        self.save_request_button = ctk.CTkButton(
            self.request_window,
            text="Сохранить заявку",
            command=self.save_request,
        )
        self.save_request_button.pack(
            fill="x",
            padx=25,
            pady=(0, 25),
        )

        self.request_title_entry.focus()

    def select_photo(self):
        file_path = filedialog.askopenfilename(
            parent=self.request_window,
            title="Выберите фотографию поломки",
            filetypes=[
                (
                    "Фотографии",
                    "*.png *.jpg *.jpeg *.webp *.bmp",
                ),
                ("Все файлы", "*.*"),
            ],
        )

        if not file_path:
            return

        allowed_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
        }

        photo_path = Path(file_path)

        if photo_path.suffix.lower() not in allowed_extensions:
            messagebox.showwarning(
                "Неверный формат",
                "Выберите изображение PNG, JPG, JPEG, WEBP или BMP.",
                parent=self.request_window,
            )
            return

        self.selected_photo_path = str(photo_path)

        self.photo_label.configure(
            text=f"Выбрано: {photo_path.name}",
        )

    def remove_photo(self):
        self.selected_photo_path = None

        self.photo_label.configure(
            text="Фотография не выбрана",
        )

    def save_request(self):
        title = self.request_title_entry.get().strip()

        description = (
            self.request_description_entry
            .get("1.0", "end")
            .strip()
        )

        try:
            request_id = create_request(
                title,
                description,
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

    def show_settings(self):
        self.page_title.configure(
            text="Настройки",
        )
        self.page_description.configure(
            text="Настройки приложения",
        )

        self.requests_frame.pack_forget()

        if hasattr(self, "settings_frame"):
            self.settings_frame.destroy()

        self.settings_frame = ctk.CTkFrame(
            self.content,
        )
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
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 10),
        )

        ctk.CTkLabel(
            self.settings_frame,
            text="Цветовая тема приложения",
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 15),
        )

        self.theme_selector = ctk.CTkSegmentedButton(
            self.settings_frame,
            values=["Светлая", "Тёмная"],
            command=self.change_theme,
        )
        self.theme_selector.pack(
            anchor="w",
            padx=20,
            pady=10,
        )

        if ctk.get_appearance_mode() == "Light":
            self.theme_selector.set("Светлая")
        else:
            self.theme_selector.set("Тёмная")

    def change_theme(self, selected_theme):
        themes = {
            "Светлая": "Light",
            "Тёмная": "Dark",
        }

        ctk.set_appearance_mode(
            themes[selected_theme],
        )