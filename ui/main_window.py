import customtkinter as ctk
from tkinter import ttk

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Учёт заявок на ремонт")
        self.geometry = ("1100x700")
        self.minsize(800, 600)

        self.create_widgets()

    def create_widgets(self):
        self.sidebar = ctk.CTkFrame(self, width=220)
        self.sidebar.pack(side="left", fill="y")

        self.content = ctk.CTkFrame(self)
        self.content.pack(side="right", fill="both", expand=True)

        self.sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text = "Учёт заявок на ремонт",
            font = ("Arial", 18, "bold")
        )
        self.sidebar_title.pack(padx=20, pady=(25, 30))

        self.settings_button = ctk.CTkButton(
            self.sidebar,
            text = "Настройки",
            command = self.show_settings
        )
        self.settings_button.pack(fill="x", padx = 15, pady = 5)

        self.page_title = ctk.CTkLabel(
            self.content,
            text = "Заявки на ремонт",
            font = ("Arial", 26, "bold")
        )
        self.page_title.pack(anchor = "w", padx = 30, pady =(25, 5))

        self.page_description = ctk.CTkLabel(
            self.content,
            text = "Просмотр и управление заявками"
        )
        self.page_description.pack(anchor = "w", padx = 30, pady =(0, 20))

        self.requests_frame = ctk.CTkFrame(self.content)
        self.requests_frame.pack(
            fill="both",
            expand=True,
            padx = 30,
            pady = (0, 30)
        )

        self.request_table = ttk.Treeview(
            self.requests_frame,
            columns=("id", "title", "status"),
            show="headings",
        )

        self.request_table.heading("id", text="Номер")
        self.request_table.heading("title", text="Название заявки")
        self.request_table.heading("status", text="Статус")

        self.request_table.column("id", width=60, anchor="center")
        self.request_table.column("status", width=400)
        self.request_table.column("status", width=150, anchor="center")

        self.request_table.pack(
            fill="both",
            expand=True,
            padx = 10,
            pady = 10
        )

    def show_requests(self):
        self.page_title.configure(text="Заявки на ремонт")
        self.page_description.configure(
            text="Просмотр и управление заявками"
        )

    def show_settings(self):
        self.page_title.configure(text="Настройки")
        self.page_description.configure(
            text="Настройки приложения"
        )