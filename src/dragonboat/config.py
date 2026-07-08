"""Application configuration — reads from .env file."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings


def _project_root() -> Path:
    """Two levels up from this file (src/dragonboat/config.py → project root)."""
    return Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # ── Paths ──
    data_dir: str = "./data"
    input_dir: str = "./data/input"
    output_dir: str = "./data/output"
    registro_file: str = "./data/registro.json"

    # ── Telegram ──
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ── Web server ──
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Analysis constants ──
    bote_personas: int = 12
    distancias_validas: list[int] = [200, 500, 1000, 2000]
    tolerancia_distancia: dict[int, float] = {
        200: 0.15,   # ±30m   -> [170, 230]
        500: 0.10,   # ±50m   -> [450, 550]
        1000: 0.10,  # ±50m   -> [950, 1050]
        2000: 0.10,  # ±200m  -> [1800, 2200]
    }
    limite_tiempo_max: dict[int, float] = {
        200: 85.0,
        500: 240.0,
        1000: 600.0,
        2000: 1500.0,
    }
    umbral_velocidad_fin: float = 8.0            # km/h sostenidos para detectar fin
    umbral_ventana_fin: int = 25                 # samples (1s @ 25Hz)
    umbral_velocidad_instantanea_2000: float = 8.0   # km/h, mínimo en 2000m

    # Detection params
    min_speed_start: float = 8.0
    accel_threshold: float = 11.0
    accel_time_window: float = 9.0
    min_cruise_speed: float = 9.0
    stroke_min_dist: int = 15
    stroke_prominence: float = 0.2
    stroke_min_amp: float = 1.0

    # Calm detection params
    calm_window: int = 14
    calm_max_ssr: float = 0.5
    calm_max_slope: float = 0.04
    calm_scan_back: int = 250

    # First stroke params
    stroke_rise_threshold: float = 1.0
    stroke_decel_drop: float = 0.3

    # Visualization params
    roll_alert_deg: float = 3.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def resolved_input_dir(self) -> Path:
        root = _project_root()
        return Path(self.input_dir) if Path(self.input_dir).is_absolute() else root / self.input_dir

    @property
    def resolved_output_dir(self) -> Path:
        root = _project_root()
        return Path(self.output_dir) if Path(self.output_dir).is_absolute() else root / self.output_dir

    @property
    def resolved_registro_file(self) -> Path:
        root = _project_root()
        return Path(self.registro_file) if Path(self.registro_file).is_absolute() else root / self.registro_file


settings = Settings()
