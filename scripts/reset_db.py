"""Reset script — drops test-related tables and recreates them empty.

Usage: python scripts/reset_db.py

Drops:  gps_data, crew_assignments, test_metrics, csv_uploads, sesiones
Keeps:  boats, crew_members, categories, test_types, distancias, app_settings

After running, re-upload CSVs from /informes to repopulate.
"""

from dragonboat.database import engine, init_db

TABLES_TO_DROP = [
    "gps_data",
    "crew_assignments",
    "test_metrics",
    "csv_uploads",
    "sesiones",
]


def main():
    from sqlalchemy import text
    with engine.connect() as conn:
        for table in TABLES_TO_DROP:
            conn.execute(text(f"DELETE FROM {table}"))
            try:
                conn.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
            except Exception:  # noqa: BLE001
                pass
            print(f"  Cleared: {table}")
        conn.commit()

    print("\nRecreating tables (if missing) and reseeding catalogs...")
    init_db()
    print("Done. Database is clean. Re-upload CSVs from /informes to repopulate.")


if __name__ == "__main__":
    main()
