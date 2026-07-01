"""Analysis package — public API."""

from dragonboat.analysis._utils import fmt
from dragonboat.analysis.loader import cargar_csv, build_gps_data_json, downsample_5hz
from dragonboat.analysis.detection import detectar_200m
from dragonboat.analysis.strokes import detectar_paladas, detectar_picos
from dragonboat.analysis.metrics import analizar_200m, calcular_pitch
from dragonboat.analysis.report import (
    imprimir_metricas,
    nombre_base,
    generar_informe_str,
)

__all__ = [
    "fmt",
    "cargar_csv",
    "build_gps_data_json",
    "downsample_5hz",
    "detectar_200m",
    "detectar_paladas",
    "detectar_picos",
    "analizar_200m",
    "calcular_pitch",
    "imprimir_metricas",
    "nombre_base",
    "generar_informe_str",
]
