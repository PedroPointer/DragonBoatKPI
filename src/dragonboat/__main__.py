"""CLI entry point — python -m dragonboat.

Procesa CSVs de data/input/, agrupa por día (sesiones_diarias) y registra
pruebas (test_metrics) + GPS completo (gps_data).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime

import pandas as pd

from dragonboat.analysis import (
    analizar_tramo,
    build_gps_data_json,
    build_gps_inicio_fin,
    calcular_sectores,
    cargar_csv,
    detectar_paladas,
    detectar_tramos,
    extraer_metadata_date,
    generar_informe_str,
    imprimir_metricas,
    nombre_base,
)
from dragonboat.config import settings
from dragonboat.database import init_db
from dragonboat.repo import (
    crear_csv_upload,
    crear_gps_data,
    crear_prueba,
    get_or_create_sesion_by_date,
    list_sesiones_diarias,
    recalc_sesion_aggregates,
)
from dragonboat.db_models import Boat
from dragonboat.database import get_session
from dragonboat.visualization.charts import graficar_200m


def _default_boat_id() -> int | None:
    with get_session() as s:
        boat = s.query(Boat).filter(Boat.name == "DB12").first()
        return boat.id if boat else None


def procesar_archivo(filepath: str) -> None:
    filename = os.path.basename(filepath)
    df = cargar_csv(filepath)
    if df.empty:
        print(f"  [!] CSV vacío: {filename}")
        return

    metadata_date = extraer_metadata_date(filepath)
    if metadata_date is None:
        try:
            metadata_date = df["Time"].iloc[0].to_pydatetime()
        except Exception:
            metadata_date = datetime.now()

    sesion = get_or_create_sesion_by_date(metadata_date.date())

    input_dir = settings.resolved_input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    file_path = str(input_dir / filename)
    (input_dir / filename).write_bytes(open(filepath, "rb").read())

    csv_upload = crear_csv_upload(
        filename=filename,
        file_path=file_path,
        sesion_id=sesion.id,
        metadata_date=metadata_date,
    )

    # GPS completo del CSV
    full_gps = {
        "time": [float(t) for t in (df["elapsed_time"].values - df["elapsed_time"].iloc[0])],
        "speed": [float(s) for s in df["speed_kmh"].values],
        "lat": [float(v) if pd.notna(v) else None for v in df["lat"].values],
        "lon": [float(v) if pd.notna(v) else None for v in df["lon"].values],
        "lean": [float(v) if pd.notna(v) else 0.0 for v in df["lean_angle"].values],
        "gforce_x": [float(v) if pd.notna(v) else 0.0 for v in df["gforce_x"].values],
        "gforce_z": [float(v) if pd.notna(v) else 0.0 for v in df["gforce_z"].values],
    }
    gps_data = crear_gps_data(
        csv_upload_id=csv_upload.id,
        sesion_id=sesion.id,
        data=full_gps,
    )

    tramos = detectar_tramos(df)
    if not tramos:
        print(f"  [!] No se detectaron tramos válidos en {filename}")
        recalc_sesion_aggregates(sesion.id)
        return

    default_boat_id = _default_boat_id()
    idx_valido = 0
    pruebas_info: list[tuple] = []

    for tramo in tramos:
        paladas_info = detectar_paladas(df, tramo.start_idx, tramo.end_idx)
        m = analizar_tramo(
            df, tramo.start_idx, tramo.end_idx, paladas_info, distancia=tramo.distancia
        )
        if m is None:
            continue
        t11 = m.tiempo_11kmh if m.tiempo_11kmh is not None else 99
        limite = settings.limite_tiempo_max.get(tramo.distancia, 1500.0)
        media_check = (tramo.distancia == 2000) or (m.velocidad_media > 9.0)
        if not (m.tiempo_total < limite and t11 < 20.0 and media_check):
            continue

        m.calm_start = tramo.calm_start
        m.calm_end = tramo.calm_end
        idx_valido += 1

        if paladas_info.dist_por_palada and len(paladas_info.dist_por_palada) > 15:
            after_15 = paladas_info.dist_por_palada[15:]
            m.dist_max_palada = max(after_15)
            m.dist_min_palada = min(after_15)

        start_dt = df["Time"].iloc[tramo.start_idx] + pd.Timedelta(hours=2)
        nb = nombre_base(m, idx_valido, start_dt)
        imprimir_metricas(m, filepath, idx_valido)

        try:
            graficar_200m(df, m, paladas_info, settings.resolved_output_dir, nb)
        except Exception as exc:  # noqa: BLE001
            print(f"  [!] No se pudo generar PNG: {exc}")

        segment_gps = build_gps_data_json(df, tramo.start_idx, tramo.end_idx, paladas_info, m)
        segment_gps_json = json.dumps(segment_gps, ensure_ascii=False)
        gps_inicio, gps_fin = build_gps_inicio_fin(
            df, tramo.start_idx, tramo.end_idx, time_offset=m.start_time
        )

        crear_prueba(
            sesion_id=sesion.id,
            csv_upload_id=csv_upload.id,
            gps_data_id=gps_data.id,
            fecha_hora=start_dt,
            test_number=idx_valido,
            distancia_metros=tramo.distancia,
            metric=m,
            chart_filename=nb,
            boat_id=default_boat_id,
            tipo="entreno",
            gps_inicio=gps_inicio,
            gps_fin=gps_fin,
            tiempos_por_distancia=m.tiempos_por_distancia,
            segment_gps_json=segment_gps_json,
            sectores_detalle=calcular_sectores(m.tiempos_por_distancia, tramo.distancia),
            paladas_detalle=list(paladas_info.dist_por_palada),
        )

        pruebas_info.append((m, idx_valido, start_dt, paladas_info.dist_por_palada))
        txt = generar_informe_str(m, idx_valido, start_dt, paladas_info.dist_por_palada)
        try:
            print(txt)
        except UnicodeEncodeError:
            print(txt.encode("cp1252", errors="replace").decode("cp1252"))
        print()

    recalc_sesion_aggregates(sesion.id)

    if idx_valido == 0:
        print(f"  [!] Todos los tramos detectados fueron descartados como no plausibles")
    else:
        print(f"  [+] Sesión #{sesion.id} ({sesion.fecha}): {idx_valido} pruebas + GPS completo")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DragonBoat Analyzer — Análisis de rendimiento"
    )
    parser.add_argument("--file", "-f", help="Procesar un archivo específico")
    parser.add_argument("--list", "-l", action="store_true", help="Listar sesiones")
    args = parser.parse_args()

    init_db()

    if args.list:
        print("\n--- SESIONES REGISTRADAS ---")
        for s in list_sesiones_diarias(50):
            print(
                f"  #{s.id} | {s.fecha} | {s.num_pruebas} pruebas | "
                f"{s.num_archivos} archivos | dist: {s.distancia_total_nominal}m"
            )
            for p in (s.test_metrics or []):
                print(f"     - Prueba #{p.test_number}: {p.distancia.metros if p.distancia else '?'}m  {p.tiempo_total:.2f}s")
        return

    archivos = [args.file] if args.file else glob.glob(
        str(settings.resolved_input_dir / "*.csv")
    )
    if not archivos:
        print(f'No se encontraron archivos CSV en "{settings.resolved_input_dir}".')
        return

    for filepath in archivos:
        filename = os.path.basename(filepath)
        print(f'\n{"=" * 65}\n  PROCESANDO: {filename}\n{"=" * 65}')
        procesar_archivo(filepath)

    print("\n--- PROCESO COMPLETADO ---")


if __name__ == "__main__":
    main()
