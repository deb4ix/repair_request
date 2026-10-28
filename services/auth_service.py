import hashlib
import hmac
import secrets

from database.connection import get_connection


ITERATIONS = 310_000


def ensure_auth_schema():
    """Создаёт таблицу аккаунтов и добавляет владельца заявке."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_users (
                    id BIGSERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user'
                        CHECK (role IN ('user', 'technician')),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                """
                ALTER TABLE repair_requests
                ADD COLUMN IF NOT EXISTS owner_id BIGINT
                REFERENCES app_users(id) ON DELETE SET NULL;
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_repair_requests_owner_id
                ON repair_requests(owner_id);
                """
            )


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    ).hex()


def register_user(username: str, password: str, role: str = "user"):
    """Регистрирует пользователя или работника по выбранной роли."""
    username = username.strip()

    if role not in ("user", "technician"):
        raise ValueError("Выберите корректную роль аккаунта.")

    if len(username) < 3:
        raise ValueError("Логин должен содержать минимум 3 символа.")
    if len(username) > 50:
        raise ValueError("Логин не должен быть длиннее 50 символов.")
    if not username.replace("_", "").replace("-", "").isalnum():
        raise ValueError(
            "В логине используйте буквы, цифры, дефис или подчёркивание."
        )
    if len(password) < 8:
        raise ValueError("Пароль должен содержать минимум 8 символов.")

    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_users (
                        username, password_hash, password_salt, role
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, username, role;
                    """,
                    (username, password_hash, salt.hex(), role),
                )
                row = cursor.fetchone()
    except Exception as error:
        # Не скрываем ошибки базы, но сообщаем понятнее о повторном логине.
        if "unique" in str(error).lower() or "duplicate" in str(error).lower():
            raise ValueError("Этот логин уже занят.") from error
        raise

    return {"id": row[0], "username": row[1], "role": row[2]}


def authenticate_user(username: str, password: str):
    username = username.strip()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, password_hash, password_salt, role
                FROM app_users
                WHERE username = %s;
                """,
                (username,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    user_id, saved_username, saved_hash, saved_salt, role = row
    candidate_hash = _hash_password(password, bytes.fromhex(saved_salt))

    if not hmac.compare_digest(candidate_hash, saved_hash):
        return None

    return {"id": user_id, "username": saved_username, "role": role}


def create_technician(username: str, password: str):
    """Создание работника из отдельного административного скрипта."""
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Логин должен содержать минимум 3 символа.")
    if len(password) < 8:
        raise ValueError("Пароль должен содержать минимум 8 символов.")

    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_users (
                        username, password_hash, password_salt, role
                    )
                    VALUES (%s, %s, %s, 'technician')
                    RETURNING id, username;
                    """,
                    (username, password_hash, salt.hex()),
                )
                row = cursor.fetchone()
    except Exception as error:
        if "unique" in str(error).lower() or "duplicate" in str(error).lower():
            raise ValueError("Этот логин уже занят.") from error
        raise

    return {"id": row[0], "username": row[1]}
