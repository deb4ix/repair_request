from database.connection import get_connection


DEFAULT_CATEGORIES = [
    "Компьютер и ноутбук",
    "Принтер и сканер",
    "Сеть и интернет",
    "Программное обеспечение",
    "Оборудование",
    "Другое",
]


def ensure_request_schema():
    """Создаёт категории и необходимые поля заявок."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS request_categories (
                    id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE
                );
            """)

            for category in DEFAULT_CATEGORIES:
                cursor.execute(
                    """
                    INSERT INTO request_categories (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING;
                    """,
                    (category,),
                )

            cursor.execute("""
                ALTER TABLE repair_requests
                ADD COLUMN IF NOT EXISTS priority
                VARCHAR(20) NOT NULL DEFAULT 'normal';
            """)

            cursor.execute("""
                ALTER TABLE repair_requests
                ADD COLUMN IF NOT EXISTS category_id BIGINT;
            """)

            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'fk_repair_requests_category'
                          AND conrelid = 'public.repair_requests'::regclass
                    ) THEN
                        ALTER TABLE public.repair_requests
                        ADD CONSTRAINT fk_repair_requests_category
                        FOREIGN KEY (category_id)
                        REFERENCES public.request_categories(id)
                        ON DELETE SET NULL;
                    END IF;
                END
                $$;
            """)

            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'chk_repair_requests_priority'
                          AND conrelid = 'public.repair_requests'::regclass
                    ) THEN
                        ALTER TABLE public.repair_requests
                        ADD CONSTRAINT chk_repair_requests_priority
                        CHECK (
                            priority IN (
                                'low', 'normal', 'high', 'critical'
                            )
                        );
                    END IF;
                END
                $$;
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_repair_requests_category_id
                ON repair_requests(category_id);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_repair_requests_priority
                ON repair_requests(priority);
            """)