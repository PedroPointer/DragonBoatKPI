"""SQLAlchemy ORM models — maps to SQLite tables.

Model: csv_uploads (provenance) ──< sesiones (pruebas) ──< test_metrics
                                                    └──< crew_assignments >── crew_members
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── CsvUpload (provenance: one per CSV file uploaded) ──

class CsvUpload(Base):
    __tablename__ = "csv_uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    file_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kept: Mapped[bool] = mapped_column(Boolean, default=True)

    sesiones = relationship("Sesion", back_populates="csv_upload", cascade="all, delete-orphan")


# ── Boat (DB12 / DB22) ──

class Boat(Base):
    __tablename__ = "boats"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(10), unique=True)  # "DB12", "DB22"
    display_name: Mapped[str] = mapped_column(String(50))
    num_rows: Mapped[int] = mapped_column(Integer)      # 5, 10
    total_persons: Mapped[int] = mapped_column(Integer)  # 12, 22

    sesiones = relationship("Sesion", back_populates="boat")


# ── Sesion (one 200m tramo = one prueba) ──

class Sesion(Base):
    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    csv_upload_id: Mapped[Optional[int]] = mapped_column(ForeignKey("csv_uploads.id"), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    test_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tipo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "competición" | "entreno"
    boat_id: Mapped[Optional[int]] = mapped_column(ForeignKey("boats.id"), nullable=True)
    categoria: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    csv_upload = relationship("CsvUpload", back_populates="sesiones")
    boat = relationship("Boat", back_populates="sesiones")
    metric = relationship("TestMetric", back_populates="sesion", uselist=False,
                          cascade="all, delete-orphan")
    crew_assignments = relationship("CrewAssignment", back_populates="sesion",
                                    cascade="all, delete-orphan")
    gps_data = relationship("TestGpsData", back_populates="sesion", uselist=False,
                            cascade="all, delete-orphan")


# ── TestMetric (one row per sesion) ──

class TestMetric(Base):
    __tablename__ = "test_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("sesiones.id"), unique=True)

    tiempo_total: Mapped[float] = mapped_column(Float)
    velocidad_media: Mapped[float] = mapped_column(Float)
    velocidad_maxima: Mapped[float] = mapped_column(Float)
    velocidad_min_post10: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aceleracion_max: Mapped[float] = mapped_column(Float)
    tiempo_11kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tiempo_12kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tiempo_50m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tiempo_100m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tiempo_150m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    num_paladas: Mapped[int] = mapped_column(Integer)
    dist_media_palada: Mapped[float] = mapped_column(Float)
    dist_std_palada: Mapped[float] = mapped_column(Float)
    dist_max_palada: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dist_min_palada: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    chart_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    sesion = relationship("Sesion", back_populates="metric")


# ── CrewMember ──

class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    apellido: Mapped[str] = mapped_column(String(100))
    categoria: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    assignments = relationship("CrewAssignment", back_populates="crew_member",
                               cascade="all, delete-orphan")


# ── CrewAssignment ──

class CrewAssignment(Base):
    __tablename__ = "crew_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("sesiones.id"))
    crew_member_id: Mapped[int] = mapped_column(ForeignKey("crew_members.id"))
    role: Mapped[str] = mapped_column(String(20))        # "tambor", "remero", "timonel"
    side: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "estribor", "babor"
    row_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1..10

    __table_args__ = (
        UniqueConstraint("sesion_id", "role", "side", "row_number",
                         name="uq_crew_position"),
    )

    sesion = relationship("Sesion", back_populates="crew_assignments")
    crew_member = relationship("CrewMember", back_populates="assignments")


# ── Category (CRUD dinámico) ──

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ── TestType (entreno / competicion) ──

class TestType(Base):
    __tablename__ = "test_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ── TestGpsData (full 25Hz sensor data as JSON, one row per sesion) ──

class TestGpsData(Base):
    __tablename__ = "test_gps_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[int] = mapped_column(
        ForeignKey("sesiones.id", ondelete="CASCADE"), unique=True
    )
    data_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sesion = relationship("Sesion", back_populates="gps_data")


# ── Categorías iniciales (seed) ──
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
