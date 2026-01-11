"""
Configuration for Purchase Match Diagnostic.

Handles unit-vendor mappings and vendor name normalization.
Config is declarative JSON - edit the file, not the code.
"""

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Optional


@dataclass
class UnitConfig:
    """Configuration for a single unit/location."""
    name: str
    vendors: list[str]  # Normalized vendor keys


@dataclass
class MatchSettings:
    """Settings for the matching algorithm."""
    price_match_tolerance_percent: Decimal = Decimal("0")
    price_match_tolerance_absolute: Decimal = Decimal("0.00")
    default_lookback_months: int = 3


@dataclass
class Config:
    """Full configuration for purchase match diagnostic."""
    units: dict[str, UnitConfig] = field(default_factory=dict)
    vendor_aliases: dict[str, list[str]] = field(default_factory=dict)
    settings: MatchSettings = field(default_factory=MatchSettings)

    # Reverse lookup: raw name -> normalized key (built on load)
    _vendor_lookup: dict[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Build reverse lookup for vendor normalization."""
        self._build_vendor_lookup()

    def _build_vendor_lookup(self):
        """Create mapping from all alias variations to normalized key."""
        self._vendor_lookup = {}
        for normalized_key, aliases in self.vendor_aliases.items():
            # Map the key itself
            self._vendor_lookup[normalized_key.lower()] = normalized_key
            # Map all aliases
            for alias in aliases:
                self._vendor_lookup[alias.lower()] = normalized_key


def load_config(config_path: str | Path) -> Config:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to unit_vendor_config.json

    Returns:
        Config object with units, aliases, and settings
    """
    path = Path(config_path)
    with open(path, "r") as f:
        data = json.load(f)

    # Parse units
    units = {}
    for unit_id, unit_data in data.get("units", {}).items():
        units[unit_id] = UnitConfig(
            name=unit_data.get("name", unit_id),
            vendors=unit_data.get("vendors", [])
        )

    # Parse settings
    settings_data = data.get("settings", {})
    settings = MatchSettings(
        price_match_tolerance_percent=Decimal(str(settings_data.get("price_match_tolerance_percent", 0))),
        price_match_tolerance_absolute=Decimal(str(settings_data.get("price_match_tolerance_absolute", 0.00))),
        default_lookback_months=settings_data.get("default_lookback_months", 3)
    )

    config = Config(
        units=units,
        vendor_aliases=data.get("vendor_aliases", {}),
        settings=settings
    )

    return config


def get_approved_vendors(unit: str, config: Config) -> list[str]:
    """
    Get list of approved vendor keys for a unit.

    Args:
        unit: Unit identifier (e.g., "PSEG_HQ")
        config: Loaded configuration

    Returns:
        List of normalized vendor keys, or empty list if unit not found
    """
    unit_config = config.units.get(unit)
    if unit_config is None:
        return []
    return unit_config.vendors


def normalize_vendor(raw_name: str, config: Config) -> Optional[str]:
    """
    Normalize a vendor name from source data to canonical key.

    Args:
        raw_name: Vendor name as it appears in IPS file (e.g., "Sysco Corporation")
        config: Loaded configuration with vendor_aliases

    Returns:
        Normalized key (e.g., "sysco") or None if not found
    """
    if not raw_name:
        return None
    return config._vendor_lookup.get(raw_name.lower())
