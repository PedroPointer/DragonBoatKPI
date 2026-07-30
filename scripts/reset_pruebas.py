"""Reset solo de pruebas — borra sesiones, métricas, asignaciones, GPS y CSV uploads.

A diferencia de `reset_db.py`, este script:
- NO dropea tablas, solo borra el contenido.
- NO toca deportistas (crew_members), categorías, ni barcos.
- Limpia también los archivos físicos en data/output/ (PNGs, HTML charts) y
  los .txt de informes generados, para que no queden referencias huérfanas.
- Borra los CSV originales de data/input/ (opcional, con --keep-inputs).

Uso:
    python scripts/reset_pruebas.py                # borra todo, conserva deportistas
    python scripts/reset_pruebas.py --keep-inputs  # conserva también los CSV de input
    python scripts/reset_pruebas.py --keep-outputs # conserva los gráficos/HTML/TXT
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from sqlalchemy import text

from dragonboat.config import settings
from dragonboat.database import engine, get_session
from dragonboat.db_models import (
    Sesion,
    TestMetric,
    GpsData,
    CrewAssignment,
    CsvUpload,
)

# Tablas a truncar (orden importa por las FKs)
TABLES_TO_TRUNCATE = [
    "gps_data",
    "crew_assignments",
    "test_metrics",
    "sesiones",
    "csv_uploads",
]


def _truncate_tables() -> None:
    """Vacía las tablas de pruebas. NO toca deportistas/categorías/barcos."""
    with engine.connect() as conn:
        # SQLite: desactiva FKs para truncar en cualquier orden
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in TABLES_TO_TRUNCATE:
            conn.execute(text(f"DELETE FROM {table}"))
            # Reset autoincrement counters (sqlite_sequence puede no existir
            # si la DB es nueva y nunca tuvo inserciones con AUTOINCREMENT).
            try:
                conn.execute(
                    text(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                )
            except Exception:  # noqa: BLE001
                pass
            print(f"  Cleared: {table}")
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()


def _clear_outputs(keep: bool) -> None:
    """Borra data/output/* excepto el directorio charts/ si querés mantenerlo."""
    if keep:
        return
    out = settings.resolved_output_dir
    if not out.exists():
        return
    removed = 0
    for entry in out.iterdir():
        try:
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            removed += 1
        except OSError as exc:
            print(f"  ! No se pudo borrar {entry.name}: {exc}")
    print(f"  Limpiado data/output/ ({removed} entradas eliminadas)")


def _clear_inputs(keep: bool) -> None:
    """Borra data/input/* (los CSV subidos)."""
    if keep:
        return
    inp = settings.resolved_input_dir
    if not inp.exists():
        return
    removed = 0
    for entry in inp.iterdir():
        try:
            if entry.is_file():
                entry.unlink()
                removed += 1
        except OSError as exc:
            print(f"  ! No se pudo borrar {entry.name}: {exc}")
    print(f"  Limpiado data/input/ ({removed} CSV eliminados)")


def main():
    parser = argparse.ArgumentParser(
        description="Borra solo los datos de pruebas (conserva deportistas)."
    )
    parser.add_argument(
        "--keep-inputs",
        action="store_true",
        help="No borrar los CSV de data/input/",
    )
    parser.add_argument(
        "--keep-outputs",
        action="store_true",
        help="No borrar gráficos, HTMLs y .txt de data/output/",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="No pedir confirmación",
    )
    args = parser.parse_args()

    # Confirmación
    if not args.yes:
        print(
            "Esto va a borrar:\n"
            "  - todas las sesiones/pruebas\n"
            "  - todas las métricas\n"
            "  - todas las asignaciones de tripulación\n"
            "  - todos los datos GPS de pruebas\n"
            "  - todos los registros de csv_uploads\n"
            + ("  - los CSV originales en data/input/\n" if not args.keep_inputs else "  - (NO toca data/input/)\n")
            + ("  - los gráficos/.txt en data/output/\n" if not args.keep_outputs else "  - (NO toca data/output/)\n")
            + "CONSERVANDO: deportistas, categorías y barcos.\n"
        )
        resp = input("¿Continuar? [s/N]: ").strip().lower()
        if resp not in {"s", "si", "sí", "y", "yes"}:
            print("Cancelado.")
            return

    print("--- Limpiando tablas de pruebas ---")
    _truncate_tables()

    print("\n--- Limpiando archivos físicos ---")
    _clear_inputs(args.keep_inputs)
    _clear_outputs(args.keep_outputs)

    # Verificación final
    with get_session() as s:
        n_ses = s.query(Sesion).count()
        n_tm = s.query(TestMetric).count()
        n_ca = s.query(CrewAssignment).count()
        n_gps = s.query(GpsData).count()
        n_csv = s.query(CsvUpload).count()

    print("\n--- Verificación ---")
    print(f"  Sesiones:           {n_ses}")
    print(f"  TestMetrics:        {n_tm}")
    print(f"  CrewAssignments:    {n_ca}")
    print(f"  GpsData:            {n_gps}")
    print(f"  CsvUploads:         {n_csv}")
    print("\nListo. Re-subí los CSV desde /informes para regenerar los informes.")


if __name__ == "__main__":
    main()
