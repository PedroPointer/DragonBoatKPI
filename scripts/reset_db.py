"""Reset script — drops test-related tables and recreates them empty.

Usage: python scripts/reset_db.py

Drops:  sesiones, test_metrics, crew_assignments, csv_uploads
Keeps:  boats, crew_members, categories

After running, re-upload CSVs from /informes to repopulate.
"""

from dragonboat.database import engine, init_db
from dragonboat.db_models import Base

TABLES_TO_DROP = [
    "test_gps_data",
    "crew_assignments",
    "test_metrics",
    "sesiones",
    "csv_uploads",
]


def main():
    from sqlalchemy import text
    with engine.connect() as conn:
        for table in TABLES_TO_DROP:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            print(f"  Dropped table: {table}")
        conn.commit()

    print("\nRecreating all tables...")
    init_db()
    print("Done. Database is clean. Re-upload CSVs from /informes to repopulate.")


if __name__ == "__main__":
    main()
