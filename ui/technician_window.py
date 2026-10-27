import io
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


class TechnicianWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Рабочее место специалиста")
        self.geometry("1100x700")
        self.minsize(850, 550)

        self.selected_request_id = None

        self.create_widgets()
        self.load_requests()

        # Автоматически обновляем список каждые 5 секунд.
        self.after(5000, self.auto_refresh)

    # --------------------------------------------------
    # Создание интерфейса
    # --------------------------------------------------

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(
            self,
            text="Заявки на ремонт",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(
            row=0,
            column=0,
            padx=20,
            pady=(20, 10),
            sticky="w",
        )

        # Панель поиска и фильтрации.
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
            values=[
                "Все статусы",
                "Новая",
                "В работе",
                "Завершена",
                "Отменена",
            ],
            command=lambda value: self.load_requests(show_errors=False),
        )
        self.status_filter.set("Все статусы")
        self.status_filter.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
        )

        # Таблица заявок.
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

        style = ttk.Style()
        style.configure(
            "Treeview",
            rowheight=30,
            font=("Arial", 10),
        )
        style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold"),
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=("id", "title", "status"),
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("id", text="№")
        self.tree.heading("title", text="Название заявки")
        self.tree.heading("status", text="Статус")

        self.tree.column("id", width=70, anchor="center")
        self.tree.column("title", width=600, anchor="w")
        self.tree.column("status", width=180, anchor="center")

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

        self.tree.bind(
            "<Double-1>",
            lambda event: self.show_request_details(),
        )

        # Кнопки управления.
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

    # --------------------------------------------------
    # Загрузка заявок
    # --------------------------------------------------

    def load_requests(self, show_errors=True):
        try:
            requests = get_all_requests()

            search_text = self.search_entry.get().strip().lower()
            selected_status = self.status_filter.get()

            # Удаляем старые строки из таблицы.
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

                self.tree.insert(
                    "",
                    "end",
                    iid=str(request_id),
                    values=(request_id, title, status),
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
        if not self.winfo_exists():
            return

        self.load_requests(show_errors=False)
        self.after(5000, self.auto_refresh)

    # --------------------------------------------------
    # Получение выбранной заявки
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
    # Подробности заявки
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
            details_window.geometry("650x520")
            details_window.minsize(500, 400)
            details_window.transient(self)

            details_window.grid_columnconfigure(0, weight=1)
            details_window.grid_rowconfigure(1, weight=1)

            ctk.CTkLabel(
                details_window,
                text=f"Заявка №{request['id']}",
                font=ctk.CTkFont(size=22, weight="bold"),
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

            ctk.CTkLabel(
                content_frame,
                text="Название:",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", pady=(5, 0))

            ctk.CTkLabel(
                content_frame,
                text=request["title"],
                wraplength=550,
                justify="left",
            ).pack(anchor="w", pady=(0, 10))

            ctk.CTkLabel(
                content_frame,
                text="Описание:",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", pady=(5, 0))

            ctk.CTkLabel(
                content_frame,
                text=request["description"],
                wraplength=550,
                justify="left",
            ).pack(anchor="w", pady=(0, 10))

            ctk.CTkLabel(
                content_frame,
                text=f"Статус: {request['status_name']}",
            ).pack(anchor="w", pady=5)

            ctk.CTkLabel(
                content_frame,
                text=f"Создана: {request['created_at']}",
                wraplength=550,
                justify="left",
            ).pack(anchor="w", pady=5)

            ctk.CTkLabel(
                content_frame,
                text=f"Последнее обновление: {request['updated_at']}",
                wraplength=550,
                justify="left",
            ).pack(anchor="w", pady=5)

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
    # Просмотр фотографии в отдельном окне
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

            # Сохраняем ссылку на изображение.
            photo_label.image = photo_image

        except Exception as error:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось открыть фотографию:\n{error}",
                parent=self,
            )

    # --------------------------------------------------
    # Изменение статуса
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

            status_menu = ctk.CTkOptionMenu(
                status_window,
                values=[
                    "Новая",
                    "В работе",
                    "Завершена",
                    "Отменена",
                ],
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
                        messagebox.showinfo(
                            "Успешно",
                            "Статус заявки изменён.",
                            parent=status_window,
                        )
                        status_window.destroy()
                        self.load_requests(show_errors=False)
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
