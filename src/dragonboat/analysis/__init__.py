"""Analysis package — public API."""

from dragonboat.analysis._utils import (
    fmt,
    format_duration,
    format_duration_short,
    calcular_sectores,
    resumen_paladas,
)
from dragonboat.analysis.loader import (
    cargar_csv,
    extraer_metadata_date,
    build_gps_data_json,
    build_gps_inicio_fin,
    classify_gps_segments,
    downsample_5hz,
    get_trajectory,
)
from dragonboat.analysis.detection import detectar_tramos, detectar_200m
from dragonboat.analysis.strokes import detectar_paladas, detectar_picos
from dragonboat.analysis.metrics import analizar_tramo, analizar_200m, calcular_pitch
from dragonboat.analysis.report import (
    imprimir_metricas,
    nombre_base,
    generar_informe_str,
    generar_resumen_sesion,
)

__all__ = [
    "fmt",
    "format_duration",
    "format_duration_short",
    "calcular_sectores",
    "resumen_paladas",
    "cargar_csv",
    "extraer_metadata_date",
    "build_gps_data_json",
    "build_gps_inicio_fin",
    "classify_gps_segments",
    "downsample_5hz",
    "get_trajectory",
    "detectar_tramos",
    "detectar_200m",
    "detectar_paladas",
    "detectar_picos",
    "analizar_tramo",
    "analizar_200m",
    "calcular_pitch",
    "imprimir_metricas",
    "nombre_base",
    "generar_informe_str",
    "generar_resumen_sesion",
]
