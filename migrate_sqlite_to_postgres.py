import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

SQLITE_PATH = "users.db"
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL before running migration.")

TABLES = [
    "users",
    "works",
    "evaluations",
    "weights",
    "notifications",
]

sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

pg_conn = psycopg2.connect(DATABASE_URL)
pg_cursor = pg_conn.cursor()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users(
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE,
    password TEXT,
    name TEXT,
    role TEXT
);

CREATE TABLE IF NOT EXISTS works(
    id SERIAL PRIMARY KEY,
    user_email TEXT,
    year INTEGER,
    period TEXT,
    work_type TEXT,
    work_details TEXT,
    start_date TEXT,
    end_date TEXT,
    actual_days INTEGER,
    target_days INTEGER,
    status TEXT DEFAULT 'pending',
    admin_note TEXT,
    approved_date TEXT
);

CREATE TABLE IF NOT EXISTS evaluations(
    id SERIAL PRIMARY KEY,
    user_email TEXT,
    year INTEGER,
    period TEXT,
    quality INTEGER,
    teamwork INTEGER,
    continuity INTEGER,
    extra_work INTEGER,
    status TEXT DEFAULT 'pending',
    admin_note TEXT,
    approved_date TEXT
);

CREATE TABLE IF NOT EXISTS weights(
    id SERIAL PRIMARY KEY,
    metric TEXT,
    year INTEGER,
    period TEXT,
    weight REAL
);

CREATE TABLE IF NOT EXISTS notifications(
    id SERIAL PRIMARY KEY,
    user_email TEXT,
    message TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT,
    work_id INTEGER,
    evaluation_id INTEGER
);
"""

try:
    pg_cursor.execute(SCHEMA_SQL)
    for table in TABLES:
        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()

        if not rows:
            print(f"{table}: 0 rows")
            continue

        pg_cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))

        pg_columns = [row[0] for row in pg_cursor.fetchall()]
        sqlite_columns = rows[0].keys()
        common_columns = [col for col in sqlite_columns if col in pg_columns]

        values = [
            tuple(row[col] for col in common_columns)
            for row in rows
        ]

        columns_sql = ", ".join(common_columns)

        pg_cursor.execute(f"DELETE FROM {table}")

        execute_values(
            pg_cursor,
            f"INSERT INTO {table} ({columns_sql}) VALUES %s",
            values
        )

        if "id" in common_columns:
            pg_cursor.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1),
                    true
                )
                """
            )

        print(f"{table}: migrated {len(rows)} rows")

    pg_conn.commit()
    print("Migration completed successfully.")

except Exception:
    pg_conn.rollback()
    raise

finally:
    sqlite_conn.close()
    pg_cursor.close()
    pg_conn.close()
