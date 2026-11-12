"""Общий пул подключений к Neon PostgreSQL.

Важно: функции сервиса должны использовать `with get_connection() as connection:`.
"""
import atexit
import os
import threading
from pathlib import Path

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / '.env')

_pool = None
_pool_lock = threading.Lock()


def get_connection():
    """Выдаёт контекстный менеджер подключения из пула."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                names = ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
                missing = [name for name in names if not os.getenv(name)]
                if missing:
                    raise ValueError('Не заполнены параметры подключения: ' + ', '.join(missing))
                _pool = ConnectionPool(
                    conninfo='',
                    kwargs={
                        'host': os.environ['DB_HOST'],
                        'port': int(os.environ['DB_PORT']),
                        'dbname': os.environ['DB_NAME'],
                        'user': os.environ['DB_USER'],
                        'password': os.environ['DB_PASSWORD'],
                        'sslmode': 'require',
                        'connect_timeout': 10,
                        'application_name': 'repair_request_app',
                        'prepare_threshold': None,
                    },
                    min_size=0,
                    max_size=4,
                    timeout=15,
                    open=True,
                )
    return _pool.connection()


def close_pool():
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


atexit.register(close_pool)
