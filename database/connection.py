import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# Путь к корневой папке проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Загружаем настройки из .env
load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    """Создаёт подключение к PostgreSQL."""

    required_variables = (
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    )

    missing = [
        name for name in required_variables
        if not os.getenv(name)
    ]

    if missing:
        raise ValueError(
            "Не заполнены параметры подключения: "
            + ", ".join(missing)
        )

    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
        connect_timeout=10,
        application_name="repair_request_app",
    )