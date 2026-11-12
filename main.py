import customtkinter as ctk
from ui.auth_window import AuthWindow


def main():
    ctk.set_appearance_mode('System')
    ctk.set_default_color_theme('blue')
    app = AuthWindow()
    app.mainloop()


if __name__ == '__main__':
    main()
