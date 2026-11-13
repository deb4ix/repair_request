"""Фоновая загрузка списков без вызовов Tkinter из рабочих потоков."""
import queue
import threading

from services.request_service import get_all_requests, get_categories


class AsyncRequestLoader:
    def init_async_loader(self):
        self._cached_requests = []
        self._request_queue = queue.Queue()
        self._request_loading = False
        self._refresh_pending = False
        self._first_load_complete = False
        self.after(80, self._poll_request_results)

    def load_requests(self, show_errors=True):
        """Обновляет данные из БД, не блокируя интерфейс."""
        if self._request_loading:
            self._refresh_pending = True
            return
        self._request_loading = True
        need_categories = not bool(self.categories)

        def worker():
            try:
                requests = get_all_requests()
                categories = get_categories() if need_categories else None
                self._request_queue.put((requests, categories, None, show_errors))
            except Exception as exc:
                self._request_queue.put((None, None, exc, show_errors))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_request_results(self):
        try:
            if not self.winfo_exists():
                return
            while True:
                requests, categories, error, show_errors = self._request_queue.get_nowait()
                self._request_loading = False
                if error is not None:
                    if show_errors:
                        from tkinter import messagebox
                        messagebox.showerror('Ошибка загрузки', f'Не удалось загрузить заявки:\n{error}', parent=self)
                else:
                    changed = (not self._first_load_complete or
                               requests != self._cached_requests or
                               categories is not None)
                    self._cached_requests = requests
                    if categories is not None:
                        self._install_categories(categories)
                    self._on_requests_received(requests)
                    if changed:
                        self.apply_filters()
                    self._first_load_complete = True
                if self._refresh_pending:
                    self._refresh_pending = False
                    self.load_requests(show_errors=False)
        except queue.Empty:
            pass
        self.after(80, self._poll_request_results)

    def _install_categories(self, categories):
        self.categories = categories
        self.category_names = [name for _, name in categories]
        self.category_name_to_id = {name: id_ for id_, name in categories}
        self.category_id_to_name = {id_: name for id_, name in categories}
        self.update_category_filter()

    def _on_requests_received(self, requests):
        pass
