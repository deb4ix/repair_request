"""Общий интерфейс чата и уведомлений для обеих ролей."""
import queue
import threading
import os
from pathlib import Path
from io import BytesIO
from datetime import datetime
from PIL import Image
import customtkinter as ctk
from tkinter import messagebox, filedialog
from services.communication_service import (send_message, get_messages, get_notifications,
    mark_notification_read, get_status_history, send_chat_message,
    get_chat_attachments, download_chat_attachment)


class CommunicationMixin:
    def init_communication(self):
        self._comm_closed = False
        self._comm_queue = queue.Queue()
        self._comm_loading = False
        self._seen_notifications = None
        self._chat_window = None
        self._chat_request_id = None
        self._chat_last_messages = None
        self._chat_files = []
        self._chat_last_attachments = None
        self._comm_tick()

    def _comm_tick(self):
        if self._comm_closed:
            return
        try:
            while True:
                kind, data, error = self._comm_queue.get_nowait()
                if kind == 'notifications':
                    self._comm_loading = False
                    if error is None:
                        unread = [row for row in data if not row[5]]
                        ids = {row[0] for row in unread}
                        if self._seen_notifications is not None:
                            for row in reversed(unread):
                                if row[0] not in self._seen_notifications:
                                    self._notify(row)
                        self._seen_notifications = ids
                        if hasattr(self, '_comm_button'):
                            self._comm_button.configure(text=f'Уведомления ({len(unread)})')
                elif kind in ('chat_attachments', 'messages') and error is None:
                    request_id, rows = data
                    if (request_id == self._chat_request_id and self._chat_window
                            and self._chat_window.winfo_exists()):
                        if kind == 'messages':
                            if rows != self._chat_last_messages:
                                self._chat_last_messages = rows
                                self._render_chat()
                        else:
                            if rows != self._chat_last_attachments:
                                self._chat_last_attachments = rows
                                self._render_chat()
                elif kind == 'chat_sent':
                    if error is None:
                        request_id = data
                        if request_id == self._chat_request_id and self._chat_window and self._chat_window.winfo_exists():
                            self._chat_entry.delete('1.0', 'end')
                            self._clear_chat_files()
                            self._chat_send_button.configure(state='normal', text='➤')
                            self._run_async('messages', lambda: (request_id, get_messages(request_id, self.current_user['id'])))
                            self._run_async('chat_attachments', lambda: (request_id, get_chat_attachments(request_id, self.current_user['id'])))
                    elif self._chat_window and self._chat_window.winfo_exists():
                        self._chat_send_button.configure(state='normal', text='➤')
                        messagebox.showerror('Отправка', str(error), parent=self._chat_window)
        except queue.Empty:
            pass
        if not self._comm_loading:
            self._comm_loading = True
            self._run_async('notifications',lambda: get_notifications(self.current_user['id']))
        if self._chat_window and self._chat_window.winfo_exists() and self._chat_request_id is not None:
            request_id = self._chat_request_id
            self._run_async('messages',lambda: (request_id,get_messages(request_id,self.current_user['id'])))
            self._run_async('chat_attachments',lambda: (request_id,get_chat_attachments(request_id,self.current_user['id'])))
        self.after(4000,self._comm_tick)

    def _run_async(self,kind,callback):
        def work():
            try:
                self._comm_queue.put((kind,callback(),None))
            except Exception as error:
                self._comm_queue.put((kind,None,error))
        threading.Thread(target=work,daemon=True).start()

    def _notify(self,row):
        try:
            notification_id, request_id, kind, text, _, _ = row
            self.bell()
            popup = ctk.CTkToplevel(self)
            popup.title('Уведомление')
            popup.geometry('420x140')
            ctk.CTkLabel(popup,text=f'Заявка №{request_id}: {text}',wraplength=370).pack(padx=20,pady=18)
            ctk.CTkButton(popup,text='Прочитано',command=lambda: (mark_notification_read(notification_id,self.current_user['id']),popup.destroy())).pack(pady=6)
            popup.after(12000,lambda: popup.destroy() if popup.winfo_exists() else None)
        except Exception:
            pass

    def open_notifications(self):
        try:
            rows = get_notifications(self.current_user['id'])
            window = ctk.CTkToplevel(self)
            window.title('Уведомления')
            window.geometry('620x470')
            frame = ctk.CTkScrollableFrame(window)
            frame.pack(fill='both',expand=True,padx=12,pady=12)
            if not rows:
                ctk.CTkLabel(frame,text='Уведомлений пока нет').pack(pady=20)
            for row in rows:
                notification_id, request_id, kind, text, created_at, is_read = row
                line = f'{created_at:%d.%m.%Y %H:%M} · Заявка №{request_id or "—"}\n{text}'
                item = ctk.CTkFrame(frame)
                item.pack(fill='x',padx=5,pady=5)
                ctk.CTkLabel(item,text=line,wraplength=460,justify='left').pack(side='left',padx=8,pady=8)
                if not is_read:
                    ctk.CTkButton(item,text='Прочитано',width=90,command=lambda nid=notification_id,w=item: (mark_notification_read(nid,self.current_user['id']),w.destroy())).pack(side='right',padx=8)
        except Exception as error:
            messagebox.showerror('Уведомления',str(error),parent=self)

    def open_request_chat(self):
        request_id = self.get_selected_request_id()
        if request_id is None:
            return
        try:
            get_messages(request_id, self.current_user['id'])
        except Exception as error:
            messagebox.showerror('Чат', str(error), parent=self)
            return
        if self._chat_window and self._chat_window.winfo_exists():
            self._chat_window.destroy()
        self._chat_request_id = request_id
        self._chat_last_messages = None
        self._chat_last_attachments = None
        self._chat_files = []
        self._chat_images = []
        self._chat_last_rendered_request = None
        window = ctk.CTkToplevel(self)
        self._chat_window = window
        window.title(f'FIXORA · Чат заявки №{request_id}')
        window.geometry('780x680')
        window.minsize(530, 480)
        window.protocol('WM_DELETE_WINDOW', self._close_chat)
        # Three fixed layout regions: header, expanding history, compact composer.
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(0, weight=0)
        window.grid_rowconfigure(1, weight=1)
        window.grid_rowconfigure(2, weight=0)

        header = ctk.CTkFrame(window, corner_radius=0, height=66)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=f'Заявка №{request_id}',
                     font=ctk.CTkFont(size=19, weight='bold')).grid(
                         row=0, column=0, sticky='w', padx=20, pady=(9, 0))
        ctk.CTkLabel(header, text='Переписка по ремонту',
                     text_color=('gray40', 'gray65')).grid(
                         row=1, column=0, sticky='w', padx=20, pady=(0, 8))

        self._chat_messages_frame = ctk.CTkScrollableFrame(
            window, fg_color='transparent', corner_radius=0)
        self._chat_messages_frame.grid(row=1, column=0, sticky='nsew', padx=8, pady=4)
        self._chat_empty = ctk.CTkLabel(self._chat_messages_frame,
                                        text='Загрузка сообщений...', text_color='gray')
        self._chat_empty.pack(pady=24)

        composer = ctk.CTkFrame(window, corner_radius=0)
        composer.grid(row=2, column=0, sticky='ew')
        composer.grid_columnconfigure(1, weight=1)
        self._chat_files_frame = ctk.CTkFrame(composer, fg_color='transparent')
        self._chat_files_frame.grid(row=0, column=0, columnspan=3,
                                    sticky='ew', padx=14)
        # Empty CTkFrame has a large default requested height; hide it.
        self._chat_files_frame.grid_remove()
        self._chat_entry = ctk.CTkTextbox(composer, height=46, corner_radius=12, wrap='word')
        self._chat_entry.grid(row=1, column=1, sticky='ew', padx=4, pady=(8, 12))
        self._chat_entry.bind('<Control-Return>',
                              lambda event: (self._send_chat(), 'break')[1])
        ctk.CTkButton(composer, text='📎', width=44, height=44,
                      command=self._choose_chat_files,
                      font=ctk.CTkFont(size=19)).grid(
                          row=1, column=0, padx=(14, 4), pady=(8, 12))
        self._chat_send_button = ctk.CTkButton(
            composer, text='➤', width=48, height=44,
            command=self._send_chat, font=ctk.CTkFont(size=19))
        self._chat_send_button.grid(row=1, column=2,
                                    padx=(4, 14), pady=(8, 12))
        self._run_async('messages', lambda: (request_id, get_messages(request_id, self.current_user['id'])))
        self._run_async('chat_attachments', lambda: (request_id, get_chat_attachments(request_id, self.current_user['id'])))

    def _close_chat(self):
        self._chat_request_id = None
        self._chat_files = []
        self._chat_last_messages = None
        self._chat_last_attachments = None
        self._chat_images = []
        if self._chat_window and self._chat_window.winfo_exists():
            self._chat_window.destroy()
        self._chat_window = None

    def _choose_chat_files(self):
        paths = filedialog.askopenfilenames(
            parent=self._chat_window, title='Прикрепить файлы',
            filetypes=[('Фото, видео, документы', '*.jpg *.jpeg *.png *.webp *.mp4 *.pdf *.txt *.docx'),
                       ('Все файлы', '*.*')])
        if paths:
            self._chat_files = list(paths)
            self._render_selected_files()

    def _clear_chat_files(self):
        self._chat_files = []
        self._render_selected_files()

    def _render_selected_files(self):
        if not self._chat_window or not self._chat_window.winfo_exists():
            return
        for child in self._chat_files_frame.winfo_children():
            child.destroy()
        if self._chat_files:
            self._chat_files_frame.grid()
            names = ', '.join(Path(p).name for p in self._chat_files)
            ctk.CTkLabel(self._chat_files_frame,
                         text=f'📎 {len(self._chat_files)} файл(ов): {names}',
                         anchor='w', wraplength=540).pack(
                             side='left', fill='x', expand=True)
            ctk.CTkButton(self._chat_files_frame, text='✕', width=30,
                          fg_color='gray40', command=self._clear_chat_files).pack(
                              side='right', padx=5, pady=4)
        else:
            self._chat_files_frame.grid_remove()

    def _render_chat(self):
        if not self._chat_window or not self._chat_window.winfo_exists():
            return
        frame = self._chat_messages_frame
        canvas = frame._parent_canvas
        # Do not force the user to the bottom while reading older messages.
        was_near_bottom = canvas.yview()[1] >= 0.96
        for child in frame.winfo_children():
            child.destroy()
        self._chat_images = []
        messages = self._chat_last_messages or []
        attachments = self._chat_last_attachments or []
        by_message = {}
        for attachment in attachments:
            by_message.setdefault(attachment[1], []).append(attachment)
        if not messages:
            ctk.CTkLabel(frame, text='Сообщений пока нет. Начните переписку.',
                         text_color='gray').pack(pady=35)
            return
        for msg in messages:
            msg_id, username, role, body, created_at = msg
            mine = username == self.current_user.get('username')
            # One full-width row per message: no empty grid columns or stretched rows.
            line = ctk.CTkFrame(frame, fg_color='transparent')
            line.pack(fill='x', padx=8, pady=3)
            bubble = ctk.CTkFrame(
                line, corner_radius=14,
                fg_color=('#DCEBFA', '#205B8F') if mine else ('#E8E8E8', '#303030'))
            bubble.pack(side='right' if mine else 'left', padx=4)
            text_color = ('#163B5D', '#FFFFFF') if mine else ('#222222', '#F2F2F2')
            when = created_at.strftime('%H:%M') if hasattr(created_at, 'strftime') else str(created_at)
            ctk.CTkLabel(bubble, text=f'{"Вы" if mine else username} · {when}',
                         text_color=text_color,
                         font=ctk.CTkFont(size=11, weight='bold'),
                         anchor='w').pack(anchor='w', padx=12, pady=(7, 2))
            if body:
                ctk.CTkLabel(bubble, text=body, wraplength=390,
                             justify='left', text_color=text_color,
                             anchor='w').pack(anchor='w', padx=12, pady=(0, 7))
            for attachment_id, _, filename, mime, size in by_message.get(msg_id, []):
                symbol = '🖼' if mime.startswith('image/') else '🎬' if mime.startswith('video/') else '📄'
                ctk.CTkButton(
                    bubble, text=f'{symbol} {filename} · {size / 1048576:.1f} МБ',
                    anchor='w', fg_color=('gray78', '#3C5269') if mine else ('gray78', 'gray35'),
                    hover_color=('gray70', 'gray45'),
                    command=lambda aid=attachment_id: self._open_chat_attachment(aid)
                ).pack(fill='x', padx=10, pady=(0, 7))
        if was_near_bottom or self._chat_last_rendered_request != self._chat_request_id:
            frame.after(80, lambda: canvas.yview_moveto(1.0)
                        if frame.winfo_exists() else None)
        self._chat_last_rendered_request = self._chat_request_id

    def _open_chat_attachment(self,attachment_id):
        try:
            filename,mime,data = download_chat_attachment(attachment_id,self.current_user['id'])
            if mime.startswith('image/'):
                with Image.open(BytesIO(data)) as source:
                    picture=source.convert('RGBA')
                picture.thumbnail((950,650))
                preview=ctk.CTkToplevel(self._chat_window)
                preview.title(filename)
                preview.geometry('980x750')
                photo=ctk.CTkImage(light_image=picture,dark_image=picture,size=picture.size)
                label=ctk.CTkLabel(preview,text='',image=photo)
                label.image=photo
                label.pack(fill='both',expand=True,padx=12,pady=12)
                ctk.CTkButton(preview,text='Сохранить файл',
                    command=lambda:self._save_chat_attachment(filename,data)).pack(pady=10)
            else:
                if messagebox.askyesno('Вложение',f'Сохранить файл «{filename}»?',parent=self._chat_window):
                    self._save_chat_attachment(filename,data)
        except Exception as error:
            messagebox.showerror('Вложение',str(error),parent=self._chat_window)

    def _save_chat_attachment(self,filename,data):
        path=filedialog.asksaveasfilename(parent=self._chat_window,initialfile=Path(filename).name)
        if path:
            Path(path).write_bytes(data)
            messagebox.showinfo('Готово','Файл сохранён.',parent=self._chat_window)

    def _send_chat(self):
        if self._chat_send_button.cget('state') == 'disabled':
            return
        body = self._chat_entry.get('1.0', 'end').strip()
        if not body and not self._chat_files:
            return
        request_id = self._chat_request_id
        paths = list(self._chat_files)
        self._chat_send_button.configure(state='disabled', text='…')
        self._run_async('chat_sent', lambda: (send_chat_message(
            request_id, self.current_user['id'], body, paths), request_id)[1])

    def _show_history(self):
        try:
            rows = get_status_history(self._chat_request_id,self.current_user['id'])
            text = '\n'.join(f'{row[3]:%d.%m.%Y %H:%M} · {row[0]}: {row[1]} → {row[2]}' for row in rows)
            messagebox.showinfo('История статусов',text or 'Изменений пока нет',parent=self._chat_window)
        except Exception as error:
            messagebox.showerror('История',str(error),parent=self._chat_window)

    def stop_communication(self):
        self._comm_closed = True