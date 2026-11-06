import hashlib
import hmac
import os
import secrets

from database.connection import get_connection


ITERATIONS = 310_000


def ensure_auth_schema():
    """Создаёт таблицу аккаунтов и связывает заявки с их владельцами."""
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
                    created_at TIMESTAMP WITH TIME ZONE
                        NOT NULL DEFAULT CURRENT_TIMESTAMP
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


def _validate_credentials(username: str, password: str):
    username = username.strip()

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

    return username


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    ).hex()


def _create_account(username: str, password: str, role: str):
    username = _validate_credentials(username, password)

    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_users (
                        username,
                        password_hash,
                        password_salt,
                        role
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, username, role;
                    """,
                    (username, password_hash, salt.hex(), role),
                )

                row = cursor.fetchone()

    except Exception as error:
        error_text = str(error).lower()

        if "unique" in error_text or "duplicate" in error_text:
            raise ValueError("Этот логин уже занят.") from error

        raise

    return {
        "id": row[0],
        "username": row[1],
        "role": row[2],
    }


def register_user(username: str, password: str):
    """Создаёт только обычного пользователя."""
    return _create_account(username, password, "user")


def register_technician(
    username: str,
    password: str,
    invitation_code: str,
):
    """Создаёт ремонтника только при правильном коде приглашения."""
    expected_code = os.getenv("TECHNICIAN_INVITE_CODE", "")

    if not expected_code:
        raise ValueError(
            "Код приглашения не настроен. "
            "Добавьте TECHNICIAN_INVITE_CODE в файл .env."
        )

    if not invitation_code or not hmac.compare_digest(
        invitation_code,
        expected_code,
    ):
        raise ValueError("Неверный код приглашения.")

    return _create_account(username, password, "technician")


def authenticate_user(username: str, password: str):
    username = username.strip()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    password_salt,
                    role
                FROM app_users
                WHERE username = %s;
                """,
                (username,),
            )

            row = cursor.fetchone()

    if row is None:
        return None

    user_id, saved_username, saved_hash, saved_salt, role = row

    candidate_hash = _hash_password(
        password,
        bytes.fromhex(saved_salt),
    )

    if not hmac.compare_digest(candidate_hash, saved_hash):
        return None

    return {
        "id": user_id,
        "username": saved_username,
        "role": role,
    }