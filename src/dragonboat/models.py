"""Data models — typed structures replacing loose dicts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TramoDetectado:
    """A detected training segment (200/500/1000/2000m) within a CSV file."""
    start_idx: int
    end_idx: int
    calm_start: int
    calm_end: int
    distancia: int = 200  # 200 | 500 | 1000 | 2000


@dataclass
class PaladasInfo:
    """Stroke (palada) detection results."""
    num_paladas: int
    dist_por_palada: list[float] = field(default_factory=list)


@dataclass
class Metricas:
    """All computed metrics for a single training test."""
    tiempo_total: float
    velocidad_media: float
    velocidad_maxima: float
    velocidad_min_post10: float
    aceleracion_max: float
    tiempo_11kmh: Optional[float]
    tiempo_12kmh: Optional[float]
    tiempo_150m: Optional[float]
    tiempo_50m: Optional[float]
    tiempo_100m: Optional[float]
    tiempo_ultimos_50m: Optional[float]
    vel_media_ultimos_50m: Optional[float]
    num_paladas: int
    dist_media_palada: float
    dist_std_palada: float
    start_idx: int
    end_idx: int
    start_time: float
    exact_time: float

    # Optional calm zone info (set after analysis)
    calm_start: Optional[int] = None
    calm_end: Optional[int] = None

    # Optional stroke distance stats (set after analysis)
    dist_max_palada: Optional[float] = None
    dist_min_palada: Optional[float] = None

    # Distance classification (200 | 500 | 1000 | 2000)
    distancia: int = 200

    # Markers every D/4 of the test distance, e.g. {"50": 7.5, "100": 13.2, ...}
    tiempos_por_distancia: dict[str, float] = field(default_factory=dict)

    @property
    def test_time(self) -> float:
        return self.tiempo_total

    @property
    def chart_filename(self) -> str:
        """Deterministic filename for the generated chart."""
        from datetime import datetime
        ts = datetime.fromtimestamp(self.start_time) if self.start_time > 1e9 else datetime.now()
        return f"{self.distancia}m_{ts.strftime('%m%d_%H-%M')}_{self.tiempo_total:.2f}"


@dataclass
class SessionInforme:
    """Report for one CSV file containing multiple test runs."""
    filename: str
    fecha: str
    formato: str
    tramos: list[Metricas] = field(default_factory=list)
    texto_informe: str = ""
