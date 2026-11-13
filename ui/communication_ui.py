"""Общий интерфейс чата и уведомлений для обеих ролей."""
import queue
import threading
import customtkinter as ctk
from tkinter import messagebox
from services.communication_service import (send_message, get_messages, get_notifications,
    mark_notification_read, get_status_history)


class CommunicationMixin:
    def init_communication(self):
        self._comm_closed = False
        self._comm_queue = queue.Queue()
        self._comm_loading = False
        self._seen_notifications = None
        self._chat_window = None
        self._chat_request_id = None
        self._chat_last_messages = None
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
                elif kind == 'messages' and error is None:
                    request_id, messages = data
                    if request_id == self._chat_request_id and self._chat_window and self._chat_window.winfo_exists():
                        if messages != self._chat_last_messages:
                            self._chat_last_messages = messages
                            self._chat_box.configure(state='normal')
                            self._chat_box.delete('1.0','end')
                            for msg in messages:
                                self._chat_box.insert('end',f'{msg[1]} ({msg[4]:%d.%m %H:%M}):\n{msg[3]}\n\n')
                            self._chat_box.configure(state='disabled')
                            self._chat_box.see('end')
        except queue.Empty:
            pass
        if not self._comm_loading:
            self._comm_loading = True
            self._run_async('notifications',lambda: get_notifications(self.current_user['id']))
        if self._chat_window and self._chat_window.winfo_exists() and self._chat_request_id is not None:
            request_id = self._chat_request_id
            self._run_async('messages',lambda: (request_id,get_messages(request_id,self.current_user['id'])))
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
            get_messages(request_id,self.current_user['id'])
        except Exception as error:
            messagebox.showerror('Чат',str(error),parent=self)
            return
        if self._chat_window and self._chat_window.winfo_exists():
            self._chat_window.destroy()
        self._chat_request_id = request_id
        self._chat_last_messages = None
        window = ctk.CTkToplevel(self)
        self._chat_window = window
        window.title(f'Переписка по заявке №{request_id}')
        window.geometry('660x620')
        window.protocol('WM_DELETE_WINDOW',self._close_chat)
        self._chat_box = ctk.CTkTextbox(window,wrap='word')
        self._chat_box.pack(fill='both',expand=True,padx=15,pady=(15,5))
        self._chat_box.configure(state='disabled')
        self._chat_entry = ctk.CTkTextbox(window,height=75)
        self._chat_entry.pack(fill='x',padx=15,pady=5)
        ctk.CTkButton(window,text='Отправить сообщение',command=self._send_chat).pack(pady=8)
        ctk.CTkButton(window,text='История статусов',command=self._show_history).pack(pady=(0,12))
        self._run_async('messages',lambda: (request_id,get_messages(request_id,self.current_user['id'])))

    def _close_chat(self):
        self._chat_request_id = None
        if self._chat_window and self._chat_window.winfo_exists():
            self._chat_window.destroy()
        self._chat_window = None

    def _send_chat(self):
        body = self._chat_entry.get('1.0','end').strip()
        if not body:
            return
        try:
            send_message(self._chat_request_id,self.current_user['id'],body)
            self._chat_entry.delete('1.0','end')
            request_id = self._chat_request_id
            self._run_async('messages',lambda: (request_id,get_messages(request_id,self.current_user['id'])))
        except Exception as error:
            messagebox.showerror('Сообщение',str(error),parent=self._chat_window)

    def _show_history(self):
        try:
            rows = get_status_history(self._chat_request_id,self.current_user['id'])
            text = '\n'.join(f'{row[3]:%d.%m.%Y %H:%M} · {row[0]}: {row[1]} → {row[2]}' for row in rows)
            messagebox.showinfo('История статусов',text or 'Изменений пока нет',parent=self._chat_window)
        except Exception as error:
            messagebox.showerror('История',str(error),parent=self._chat_window)

    def stop_communication(self):
        self._comm_closed = True
