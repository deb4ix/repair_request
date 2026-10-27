import customtkinter as ctk

from ui.technician_window import TechnicianWindow


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = TechnicianWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
