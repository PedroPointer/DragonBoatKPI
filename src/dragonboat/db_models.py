"""SQLAlchemy ORM models — Dragon Boat Analyzer.

Jerarquía del modelo (sin ciclos, todas las FKs en el hijo):

    sesiones (día = sesión de entreno)
      ├─ csv_uploads (1:N) ─ un registro por CSV subido
      │    └─ gps_data (1:1) ─ GPS completo del CSV
      │         └─ test_metrics (0:N) ─ pruebas derivadas (OPCIONALES)
      ├─ test_metrics (1:N) ─ pruebas del día
      │    ├─ crew_assignments (1:N) ─ tripulación de la prueba
      │    └─ gps_data (0..1, FK) ─ GPS del que sale esta prueba
      └─ gps_data (1:N) ─ para queries rápidas por día

    Las métricas generales del entreno (tiempo parado, vel media, etc.) viven
    directamente en `sesiones` (denormalizadas, recomputadas al subir CSV).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Configuración de la app (key-value) ──

class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ── Catálogo de distancias (200/500/1000/2000) ──

class Distancia(Base):
    __tablename__ = "distancias"

    id: Mapped[int] = mapped_column(primary_key=True)
    metros: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(50), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    test_metrics = relationship("TestMetric", back_populates="distancia")


# ── Sesión diaria (un día = un entreno) ──

class Sesion(Base):
    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    categoria: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    distancia_total_nominal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    distancia_total_real: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    num_pruebas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_archivos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tiempo_total_entreno: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tiempo_parado: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tiempo_movimiento: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vel_media_movimiento: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vel_max_dia: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ritmo_medio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    csv_uploads = relationship("CsvUpload", back_populates="sesion", cascade="all, delete-orphan")
    test_metrics = relationship("TestMetric", back_populates="sesion", cascade="all, delete-orphan")
    gps_data = relationship("GpsData", back_populates="sesion", cascade="all, delete-orphan")


# ── CSV subido (procedencia) ──

class CsvUpload(Base):
    __tablename__ = "csv_uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    file_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kept: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("sesiones.id"), nullable=False)

    sesion = relationship("Sesion", back_populates="csv_uploads")
    gps_data = relationship(
        "GpsData", back_populates="csv_upload", uselist=False, cascade="all, delete-orphan"
    )
    test_metrics = relationship("TestMetric", back_populates="csv_upload", cascade="all, delete-orphan")


# ── GPS completo (25Hz) de un CSV ──

class GpsData(Base):
    __tablename__ = "gps_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    csv_upload_id: Mapped[int] = mapped_column(
        ForeignKey("csv_uploads.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    sesion_id: Mapped[int] = mapped_column(ForeignKey("sesiones.id"), nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    csv_upload = relationship("CsvUpload", back_populates="gps_data")
    sesion = relationship("Sesion", back_populates="gps_data")
    test_metrics = relationship("TestMetric", back_populates="gps_data")


# ── Catálogos referenciados ──

class Boat(Base):
    __tablename__ = "boats"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    num_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    total_persons: Mapped[int] = mapped_column(Integer, nullable=False)

    test_metrics = relationship("TestMetric", back_populates="boat")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    test_metrics = relationship("TestMetric", back_populates="categoria")


class TestType(Base):
    __tablename__ = "test_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    test_metrics = relationship("TestMetric", back_populates="tipo")


# ── Prueba (un tramo de 200/500/1000/2000m) ──

class TestMetric(Base):
    __tablename__ = "test_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("sesiones.id"), nullable=False)
    csv_upload_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("csv_uploads.id", ondelete="CASCADE"), nullable=True
    )
    gps_data_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("gps_data.id", ondelete="SET NULL"), nullable=True
    )

    fecha_hora: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    test_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    distancia_id: Mapped[int] = mapped_column(ForeignKey("distancias.id"), nullable=False)
    boat_id: Mapped[Optional[int]] = mapped_column(ForeignKey("boats.id"), nullable=True)
    tipo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("test_types.id"), nullable=True)
    categoria_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    chart_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    gps_inicio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gps_fin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tiempos_por_distancia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    segment_gps_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sectores_detalle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paladas_detalle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tiempo_total: Mapped[float] = mapped_column(Float, nullable=False)
    velocidad_media: Mapped[float] = mapped_column(Float, nullable=False)
    velocidad_maxima: Mapped[float] = mapped_column(Float, nullable=False)
    velocidad_min_post10: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aceleracion_max: Mapped[float] = mapped_column(Float, nullable=False)
    tiempo_12kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    num_paladas: Mapped[int] = mapped_column(Integer, nullable=False)
    dist_media_palada: Mapped[float] = mapped_column(Float, nullable=False)
    dist_std_palada: Mapped[float] = mapped_column(Float, nullable=False)
    dist_max_palada: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dist_min_palada: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    sesion = relationship("Sesion", back_populates="test_metrics")
    csv_upload = relationship("CsvUpload", back_populates="test_metrics")
    gps_data = relationship("GpsData", back_populates="test_metrics")
    distancia = relationship("Distancia", back_populates="test_metrics")
    boat = relationship("Boat", back_populates="test_metrics")
    tipo = relationship("TestType", back_populates="test_metrics")
    categoria = relationship("Category", back_populates="test_metrics")
    crew_assignments = relationship(
        "CrewAssignment", back_populates="test_metric", cascade="all, delete-orphan"
    )


# ── Tripulantes y asignaciones ──

class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    categoria: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    assignments = relationship(
        "CrewAssignment", back_populates="crew_member", cascade="all, delete-orphan"
    )


class CrewAssignment(Base):
    __tablename__ = "crew_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_metric_id: Mapped[int] = mapped_column(
        ForeignKey("test_metrics.id", ondelete="CASCADE"), nullable=False
    )
    crew_member_id: Mapped[int] = mapped_column(
        ForeignKey("crew_members.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    row_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "test_metric_id", "role", "side", "row_number", name="uq_crew_position"
        ),
    )

    test_metric = relationship("TestMetric", back_populates="crew_assignments")
    crew_member = relationship("CrewMember", back_populates="assignments")


# ── Seeds ──

CATEGORIAS_COMPETICION = [
    "Open Sénior",
    "Open Veterano",
    "Femenino Sénior",
    "Femenino Veterano",
    "Mixto Sénior",
    "Mixto Veterano",
    "ACS",
    "PD1",
    "PD2",
    "PD3",
]

DISTANCIAS_SEED = [
    (200, "200 metros", 1),
    (500, "500 metros", 2),
    (1000, "1000 metros", 3),
    (2000, "2000 metros", 4),
]
