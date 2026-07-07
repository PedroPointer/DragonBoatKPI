"""CLI entry point — python -m dragonboat."""

from __future__ import annotations

import argparse
import glob
import os
from datetime import datetime

import pandas as pd

from dragonboat.analysis import (
    analizar_tramo,
    cargar_csv,
    detectar_tramos,
    detectar_paladas,
    generar_informe_str,
    imprimir_metricas,
    nombre_base,
)
from dragonboat.config import settings
from dragonboat.database import init_db
from dragonboat.repo import (
    crear_csv_upload,
    crear_sesion,
    get_csv_sesiones,
    get_sesiones,
)
from dragonboat.visualization.charts import graficar_200m


def procesar_archivo(filepath: str) -> None:
    filename = os.path.basename(filepath)
    df = cargar_csv(filepath)

    tramos = detectar_tramos(df)
    if not tramos:
        print(f"  [!] No se detectaron tramos válidos (200/500/1000/2000m) en {filename}")
        return

    input_dir = settings.resolved_input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    file_path = str(input_dir / filename)
    (input_dir / filename).write_bytes(open(filepath, "rb").read())

    csv_upload = crear_csv_upload(filename, file_path=file_path)
    idx_valido = 0

    for tramo in tramos:
        start_idx, end_idx = tramo.start_idx, tramo.end_idx
        paladas_info = detectar_paladas(df, start_idx, end_idx)
        m = analizar_tramo(df, start_idx, end_idx, paladas_info, distancia=tramo.distancia)
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

        start_dt = df["Time"].iloc[start_idx] + pd.Timedelta(hours=2)
        nb = nombre_base(m, idx_valido, start_dt)
        imprimir_metricas(m, filepath, idx_valido)

        chart_path = graficar_200m(df, m, paladas_info, settings.resolved_output_dir, nb)

        crear_sesion(
            csv_upload.id, idx_valido, m,
            fecha_hora=start_dt,
            tipo="entreno",
            chart_filename=nb,
            distancia=tramo.distancia,
            tiempos_por_distancia=m.tiempos_por_distancia,
        )

        txt = generar_informe_str(m, idx_valido, start_dt, paladas_info.dist_por_palada)
        try:
            print(txt)
        except UnicodeEncodeError:
            print(txt.encode("cp1252", errors="replace").decode("cp1252"))
        print()

    if idx_valido == 0:
        print(f"  [!] Todos los tramos detectados fueron descartados como no plausibles")
    else:
        print(f'  [+] CSV guardado (id={csv_upload.id}) con {idx_valido} pruebas.')


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DragonBoat Analyzer — Analisis de rendimiento"
    )
    parser.add_argument("--file", "-f", help="Procesar un archivo especifico")
    parser.add_argument("--list", "-l", action="store_true", help="Listar pruebas")
    args = parser.parse_args()

    init_db()

    if args.list:
        print("\n--- PRUEBAS REGISTRADAS ---")
        for s in get_sesiones(50):
            tiempo_str = f'{s.metric.tiempo_total:.2f}s' if s.metric else "—"
            csv_name = s.csv_upload.filename if s.csv_upload else "—"
            print(f"  #{s.id}: {s.custom_name or 'Prueba ' + str(s.test_number)}  ({csv_name})")
            print(f"       Tiempo: {tiempo_str}")
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
