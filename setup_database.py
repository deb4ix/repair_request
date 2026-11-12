from time import perf_counter

from services.auth_service import ensure_auth_schema
from services.request_schema import ensure_request_schema


def main():
    start = perf_counter()

    print("Подготовка базы данных...")

    ensure_auth_schema()
    print("Таблицы авторизации проверены.")

    ensure_request_schema()
    print("Таблицы заявок и категории проверены.")

    print(
        f"База данных готова. "
        f"Время: {perf_counter() - start:.2f} сек."
    )


if __name__ == "__main__":
    main()
