import io
from datetime import datetime

import customtkinter as ctk
from tkinter import ttk, messagebox
from PIL import Image

from services.request_service import (
    get_all_requests,
    get_request_by_id,
    update_request_status,
    delete_request,
    get_request_photo,
)


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
        self.geometry("1100x700")
        self.minsize(850, 550)
        self.protocol("WM_DELETE_WINDOW", self.logout)

        self._auto_refresh_id = None
        self._current_table_theme = None

        self.create_widgets()
        self.load_requests()

        self._auto_refresh_id = self.after(
            5000, self.auto_refresh
        )

    # --------------------------------------------------
    # Интерфейс
    # --------------------------------------------------

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self,
            text="Заявки на ремонт",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(
            row=0, column=0,
            padx=20, pady=(20, 10),
            sticky="w",
        )

        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(
            row=1, column=0,
            padx=20, pady=10,
            sticky="ew",
        )
        filter_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Поиск по названию заявки...",
        )
        self.search_entry.grid(
            row=0, column=0,
            padx=10, pady=10,
            sticky="ew",
        )
        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.load_requests(show_errors=False),
        )

        self.status_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=[
                "Все статусы",
                "Новая",
                "В работе",
                "Завершена",
                "Отменена",
            ],
            command=lambda value: self.load_requests(
                show_errors=False
            ),
        )
        self.status_filter.set("Все статусы")
        self.status_filter.grid(
            row=0, column=1,
            padx=10, pady=10,
        )

        table_frame = ctk.CTkFrame(self)
        table_frame.grid(
            row=2, column=0,
            padx=20, pady=10,
            sticky="nsew",
        )
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("id", "title", "status"),
            show="headings",
            selectmode="browse",
            style="Technician.Treeview",
        )

        self.tree.heading("id", text="№")
        self.tree.heading("title", text="Название заявки")
        self.tree.heading("status", text="Статус")

        self.tree.column("id", width=70, anchor="center")
        self.tree.column("title", width=600, anchor="w")
        self.tree.column("status", width=180, anchor="center")

        self.tree.grid(
            row=0, column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Настраиваем цвета таблицы сразу при создании.
        self.update_table_theme()

        self.tree.bind(
            "<Double-1>",
            lambda event: self.show_request_details(),
        )

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.grid(
            row=3, column=0,
            padx=20, pady=(5, 20),
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
            text="Выйти из аккаунта",
            fg_color="#555555",
            hover_color="#333333",
            command=self.logout,
        ).pack(side="right", padx=8, pady=10)

    # --------------------------------------------------
    # Оформление таблицы и цвета статусов
    # --------------------------------------------------

    def update_table_theme(self):
        """Применяет оформление Treeview под текущую тему CustomTkinter."""
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
        # Тема clam позволяет корректно задавать фон и цвета текста.
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
            foreground=[("selected", "#FFFFFF" if is_dark else "#202020")],
        )
        style.map(
            "Technician.Treeview.Heading",
            background=[("active", heading_background)],
            foreground=[("active", heading_foreground)],
        )

        # Цветные строки для каждого статуса.
        for status, (row_background, row_foreground) in status_colors.items():
            self.tree.tag_configure(
                status,
                background=row_background,
                foreground=row_foreground,
            )

        self._current_table_theme = appearance

    @staticmethod
    def get_status_tag(status):
        """Преобразует статус из БД или интерфейса в тег таблицы."""
        status_tags = {
            "new": "new",
            "Новая": "new",
            "in_progress": "in_progress",
            "В работе": "in_progress",
            "completed": "completed",
            "Завершена": "completed",
            "cancelled": "cancelled",
            "Отменена": "cancelled",
        }
        return status_tags.get(status, "")

    # --------------------------------------------------
    # Выход из аккаунта
    # --------------------------------------------------

    def logout(self):
        if self._auto_refresh_id is not None:
            try:
                self.after_cancel(self._auto_refresh_id)
            except Exception:
                pass
            self._auto_refresh_id = None

        self.withdraw()

        if self.master is not None and self.master.winfo_exists():
            self.master.deiconify()
            self.master.lift()

    # --------------------------------------------------
    # Загрузка заявок
    # --------------------------------------------------

    def load_requests(self, show_errors=True):
        try:
            # Если пользователь переключил тему в другом окне,
            # обновляем оформление таблицы и здесь.
            current_theme = ctk.get_appearance_mode()
            if current_theme != self._current_table_theme:
                self.update_table_theme()

            requests = get_all_requests()

            search_text = self.search_entry.get().strip().lower()
            selected_status = self.status_filter.get()

            for item in self.tree.get_children():
                self.tree.delete(item)

            for request in requests:
                request_id, title, status = request

                if search_text and search_text not in title.lower():
                    continue

                if (
                    selected_status != "Все статусы"
                    and status != selected_status
                ):
                    continue

                status_tag = self.get_status_tag(status)

                self.tree.insert(
                    "",
                    "end",
                    iid=str(request_id),
                    values=(request_id, title, status),
                    tags=(status_tag,) if status_tag else (),
                )

        except Exception as error:
            if show_errors:
                messagebox.showerror(
                    "Ошибка",
                    f"Не удалось загрузить заявки:\n{error}",
                    parent=self,
                )

    # --------------------------------------------------
    # Автоматическое обновление
    # --------------------------------------------------

    def auto_refresh(self):
        if not self.winfo_exists() or not self.winfo_viewable():
            self._auto_refresh_id = None
            return

        self.load_requests(show_errors=False)

        self._auto_refresh_id = self.after(
            5000, self.auto_refresh
        )

    # --------------------------------------------------
    # Выбор заявки
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Подробности заявки и предпросмотр фото
    # --------------------------------------------------

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
                row=0, column=0,
                padx=20, pady=(20, 10),
                sticky="w",
            )

            content_frame = ctk.CTkScrollableFrame(details_window)
            content_frame.grid(
                row=1, column=0,
                padx=20, pady=10,
                sticky="nsew",
            )
            content_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                content_frame,
                text="Название:",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", pady=(5, 0))

            ctk.CTkLabel(
                content_frame,
                text=request["title"],
                wraplength=620,
                justify="left",
            ).pack(anchor="w", pady=(0, 12))

            ctk.CTkLabel(
                content_frame,
                text="Описание:",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", pady=(5, 0))

            ctk.CTkLabel(
                content_frame,
                text=request["description"],
                wraplength=620,
                justify="left",
            ).pack(anchor="w", pady=(0, 12))

            ctk.CTkLabel(
                content_frame,
                text=f"Статус: {request['status_name']}",
            ).pack(anchor="w", pady=5)

            ctk.CTkLabel(
                content_frame,
                text=f"Создана: {format_datetime(request['created_at'])}",
            ).pack(anchor="w", pady=5)

            ctk.CTkLabel(
                content_frame,
                text=(
                    "Последнее обновление: "
                    f"{format_datetime(request['updated_at'])}"
                ),
                wraplength=620,
                justify="left",
            ).pack(anchor="w", pady=5)

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

    # --------------------------------------------------
    # Полноразмерный просмотр фотографии
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Изменение статуса заявки
    # --------------------------------------------------

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

            if request["status"] == "in_progress":
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

    # --------------------------------------------------
    # Удаление заявки
    # --------------------------------------------------

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
