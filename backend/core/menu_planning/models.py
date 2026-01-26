"""Pydantic v2 models for API request/response validation."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# === Unit Models ===

class UnitCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    station_groups: dict[str, list[str]] = Field(default_factory=dict)
    active_stations: list[str] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    station_groups: dict[str, list[str]]
    active_stations: list[str]
    settings: dict
    created_at: datetime


# === Cycle Menu Models ===

class CycleMenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    day_of_week: str
    week_number: int
    meal: str
    station: str
    station_group: Optional[str]
    item_name: str
    keywords: list[str]


class CycleMenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: str
    month: str
    filename: str
    uploaded_at: datetime
    status: str
    error_message: Optional[str]
    items: list[CycleMenuItemResponse] = []


class CycleMenuListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: str
    month: str
    filename: str
    uploaded_at: datetime
    status: str
    item_count: int = 0


# === Promo Models ===

class PromoRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    master_ref: str
    name: str
    station: Optional[str]
    station_groups: list[str]
    calories: Optional[int]
    cost: Optional[Decimal]
    dietary: list[str]
    theme: str
    keywords: list[str]


class PromoPacketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    month: str
    theme: str
    filename: str
    uploaded_at: datetime
    status: str
    error_message: Optional[str]
    recipes: list[PromoRecipeResponse] = []


# === Recommendation Models ===

class ScoreBreakdown(BaseModel):
    date_relevance: int = 0
    station_fit: int = 0
    keyword_fit: int = 0
    cost_delta: int = 0
    dietary_value: int = 0
    variety_bonus: int = 0
    total: int = 0


class RecommendationItem(BaseModel):
    date: date
    day_of_week: str
    current_item: dict
    promo_recipe: dict
    scores: ScoreBreakdown
    total_score: int
    why: str = ""


class FlagsReport(BaseModel):
    theme_collisions: list[dict] = []
    weekday_repeats: list[dict] = []
    ingredient_collisions: list[dict] = []
    total_flags: int = 0


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_menu_id: int
    run_at: datetime
    config_snapshot: dict
    results: list[RecommendationItem]
    flags: FlagsReport


class GenerateRequest(BaseModel):
    unit_id: str
    month: str
    min_score: int = Field(default=50, ge=0, le=100)
    max_per_day: int = Field(default=5, ge=1, le=20)


# === Theme Models ===

class ThemeConfig(BaseModel):
    name: str
    dates: list[str] = []
    window: int = 0
    all_month: bool = False
    keywords: list[str] = []


class ThemesResponse(BaseModel):
    themes: dict[str, dict[str, ThemeConfig]]
