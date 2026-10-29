import io
from pathlib import Path

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from PIL import Image

from services.request_service import (
    get_all_requests,
    get_request_by_id,
    get_request_photo,
    create_request,
    update_request,
    delete_request,
)


class MainWindow(ctk.CTkToplevel):
    def __init__(self, user, master=None):
        super().__init__(master)

        self.current_user = user
        self.title(
            f"Учёт заявок на ремонт — {user['username']}"
        )
        self.geometry("1100x700")
        self.minsize(800, 600)
        self.protocol("WM_DELETE_WINDOW", self.logout)

        self.selected_photo_path = None
        self.remove_existing_photo = False

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
            text="Просмотр и управление заявками",
        )
        self.page_description.pack(
            anchor="w",
            padx=30,
            pady=(0, 20),
        )

        self.requests_frame = ctk.CTkFrame(
            self.content
        )

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
            values=[
                "Все статусы",
                "Новая",
                "В работе",
                "Завершена",
                "Отменена",
            ],
            command=lambda value: self.load_requests(),
            width=160,
        )
        self.status_filter.pack(
            side="left",
            padx=(5, 0),
            pady=5,
        )
        self.status_filter.set("Все статусы")

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
            columns=("id", "title", "status"),
            show="headings",
            selectmode="browse",
        )

        self.request_table.heading("id", text="Номер")
        self.request_table.heading(
            "title",
            text="Название заявки",
        )
        self.request_table.heading("status", text="Статус")

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

        self.request_table.bind(
            "<Double-1>",
            lambda event: self.show_request_details(),
        )

    def show_requests(self):
        self.page_title.configure(
            text="Заявки на ремонт"
        )
        self.page_description.configure(
            text="Просмотр и управление заявками"
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

    def load_requests(self):
        try:
            requests = get_all_requests(
                self.current_user["id"]
            )

            search_text = (
                self.search_entry.get().strip().casefold()
            )
            selected_status = (
                self.status_filter.get().strip().casefold()
            )

            for item in self.request_table.get_children():
                self.request_table.delete(item)

            for request_id, title, status in requests:
                title = title or ""
                status = status or ""

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

                self.request_table.insert(
                    "",
                    "end",
                    iid=str(request_id),
                    values=(request_id, title, status),
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
            details_window.title(
                f"Заявка №{request_id}"
            )
            details_window.geometry("700x600")
            details_window.minsize(500, 400)
            details_window.transient(self)

            details_window.grid_columnconfigure(
                0,
                weight=1,
            )
            details_window.grid_rowconfigure(
                1,
                weight=1,
            )

            ctk.CTkLabel(
                details_window,
                text=f"Заявка №{request_id}",
                font=ctk.CTkFont(
                    size=24,
                    weight="bold",
                ),
            ).grid(
                row=0,
                column=0,
                padx=20,
                pady=(20, 10),
                sticky="w",
            )

            content = ctk.CTkScrollableFrame(
                details_window
            )
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
                ("Описание", request["description"]),
                ("Статус", request["status_name"]),
                ("Создана", request["created_at"]),
                (
                    "Последнее обновление",
                    request["updated_at"],
                ),
            ]

            for label_text, value in fields:
                ctk.CTkLabel(
                    content,
                    text=f"{label_text}:",
                    font=ctk.CTkFont(weight="bold"),
                ).pack(
                    anchor="w",
                    pady=(10, 2),
                )

                ctk.CTkLabel(
                    content,
                    text=str(value or "Не указано"),
                    wraplength=580,
                    justify="left",
                ).pack(
                    anchor="w",
                    pady=(0, 5),
                )

            ctk.CTkButton(
                details_window,
                text="Просмотреть фотографию",
                command=lambda rid=request_id: (
                    self.show_request_photo(rid)
                ),
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
            photo_window.title(
                f"Фотография заявки №{request_id}"
            )
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

    def delete_selected_request(self):
        request_id = self.get_selected_request_id()

        if request_id is None:
            return

        selected = self.request_table.selection()
        values = self.request_table.item(
            selected[0],
            "values",
        )
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
                    "Заявка не найдена",
                    "Возможно, заявка уже была удалена.",
                    parent=self,
                )
                self.load_requests()
                return

            self.editing_request_id = request_id
            self.selected_photo_path = None
            self.remove_existing_photo = False

            has_photo = (
                get_request_photo(
                    request_id,
                    self.current_user["id"],
                )
                is not None
            )

            self.request_window = ctk.CTkToplevel(self)
            self.request_window.title(
                f"Редактирование заявки №{request_id}"
            )
            self.request_window.geometry("500x700")
            self.request_window.minsize(450, 600)
            self.request_window.transient(self)
            self.request_window.grab_set()

            ctk.CTkLabel(
                self.request_window,
                text=f"Редактирование заявки №{request_id}",
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
                placeholder_text="Название заявки",
            )
            self.request_title_entry.pack(
                fill="x",
                padx=25,
                pady=(0, 15),
            )
            self.request_title_entry.insert(
                0,
                request["title"] or "",
            )

            ctk.CTkLabel(
                self.request_window,
                text="Описание проблемы",
            ).pack(
                anchor="w",
                padx=25,
                pady=(0, 5),
            )

            self.request_description_entry = (
                ctk.CTkTextbox(
                    self.request_window,
                    height=150,
                )
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
            ).pack(
                anchor="w",
                padx=25,
                pady=(0, 5),
            )

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
            ).pack(
                anchor="w",
                padx=25,
                pady=(0, 5),
            )

            ctk.CTkButton(
                self.request_window,
                text="Удалить фотографию",
                command=self.remove_edit_photo,
                fg_color="#C62828",
                hover_color="#8E0000",
            ).pack(
                anchor="w",
                padx=25,
                pady=(0, 15),
            )

            ctk.CTkButton(
                self.request_window,
                text="Сохранить изменения",
                command=self.save_edit_request,
            ).pack(
                fill="x",
                padx=25,
                pady=(0, 25),
            )

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
                (
                    "Фотографии",
                    "*.png *.jpg *.jpeg *.webp *.bmp",
                ),
                ("Все файлы", "*.*"),
            ],
        )

        if not file_path:
            return

        photo_path = Path(file_path)
        allowed_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
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
            self.request_description_entry
            .get("1.0", "end")
            .strip()
        )

        try:
            updated = update_request(
                self.editing_request_id,
                title,
                description,
                photo_path=self.selected_photo_path,
                remove_photo=self.remove_existing_photo,
                owner_id=self.current_user["id"],
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

        ctk.CTkButton(
            self.request_window,
            text="Выбрать фотографию",
            command=self.select_photo,
        ).pack(
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

        ctk.CTkButton(
            self.request_window,
            text="Убрать фотографию",
            command=self.remove_photo,
            fg_color="gray",
            hover_color="#555555",
        ).pack(
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

        ctk.CTkButton(
            self.request_window,
            text="Сохранить заявку",
            command=self.save_request,
        ).pack(
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

        photo_path = Path(file_path)
        allowed_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
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
        self.photo_label.configure(
            text="Фотография не выбрана"
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
                photo_path=self.selected_photo_path,
                owner_id=self.current_user["id"],
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
