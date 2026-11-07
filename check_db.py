"""Print table names and row counts for the project SQLite database."""
import sqlite3
from src.config import DB


def main():
    if not DB.exists():
        raise FileNotFoundError(f"Database not found: {DB}")
    with sqlite3.connect(DB) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        print("\\n========== DATABASE TABLES ==========\\n")
        for (table_name,) in tables:
            count = connection.execute(f' SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            print(f"{table_name}: {count:,} records")
        print("\\n========== DATABASE CHECK COMPLETED ==========")


if __name__ == "__main__":
    main()
