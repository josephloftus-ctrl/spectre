"""SQLAlchemy ORM models for menu planning."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Date, Numeric, JSON, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .database import Base


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class Unit(Base):
    """Unit configuration."""
    __tablename__ = "units"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    station_groups: Mapped[dict] = mapped_column(JSON, default=dict)
    active_stations: Mapped[list] = mapped_column(JSON, default=list)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cycle_menus: Mapped[list["CycleMenu"]] = relationship(back_populates="unit")


class CycleMenu(Base):
    """Uploaded cycle menu."""
    __tablename__ = "cycle_menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_id: Mapped[str] = mapped_column(String(50), ForeignKey("units.id"))
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    unit: Mapped["Unit"] = relationship(back_populates="cycle_menus")
    items: Mapped[list["CycleMenuItem"]] = relationship(back_populates="cycle_menu", cascade="all, delete-orphan")


class CycleMenuItem(Base):
    """Parsed menu item from cycle menu."""
    __tablename__ = "cycle_menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_menu_id: Mapped[int] = mapped_column(Integer, ForeignKey("cycle_menus.id"))
    date: Mapped[date] = mapped_column(Date)
    day_of_week: Mapped[str] = mapped_column(String(20))
    week_number: Mapped[int] = mapped_column(Integer)
    meal: Mapped[str] = mapped_column(String(50))
    station: Mapped[str] = mapped_column(String(100))
    station_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255))
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    cycle_menu: Mapped["CycleMenu"] = relationship(back_populates="items")


class PromoPacket(Base):
    """Uploaded promotional recipe packet."""
    __tablename__ = "promo_packets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[str] = mapped_column(String(7))
    theme: Mapped[str] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recipes: Mapped[list["PromoRecipe"]] = relationship(back_populates="packet", cascade="all, delete-orphan")


class PromoRecipe(Base):
    """Parsed recipe from promo packet."""
    __tablename__ = "promo_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    packet_id: Mapped[int] = mapped_column(Integer, ForeignKey("promo_packets.id"))
    master_ref: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255))
    station: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    station_groups: Mapped[list] = mapped_column(JSON, default=list)
    calories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    dietary: Mapped[list] = mapped_column(JSON, default=list)
    theme: Mapped[str] = mapped_column(String(100))
    theme_dates: Mapped[list] = mapped_column(JSON, default=list)
    theme_window: Mapped[int] = mapped_column(Integer, default=0)
    theme_all_month: Mapped[bool] = mapped_column(default=False)
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    packet: Mapped["PromoPacket"] = relationship(back_populates="recipes")


class Recommendation(Base):
    """Generated recommendation run."""
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_menu_id: Mapped[int] = mapped_column(Integer, ForeignKey("cycle_menus.id"))
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    config_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[list] = mapped_column(JSON, default=list)
    flags: Mapped[dict] = mapped_column(JSON, default=dict)
