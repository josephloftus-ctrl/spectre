"""Pydantic models for plugin configuration schemas."""
from typing import Optional
from pydantic import BaseModel


class DistributorEntry(BaseModel):
    """A valid or flagged distributor."""
    name: str
    aliases: list[str] = []
    dist_num_pattern: Optional[str] = None  # Regex pattern for distributor numbers
    reason: Optional[str] = None  # For flagged distributors
    severity: Optional[str] = None  # "info", "warning", "error"


class UnknownDistributorConfig(BaseModel):
    """How to handle unknown distributors."""
    action: str = "flag"  # "flag", "allow", "block"
    severity: str = "warning"
    message: str = "Unknown distributor - verify legitimacy"


class DistributorsConfig(BaseModel):
    """Distributors configuration from distributors.yaml."""
    valid: list[DistributorEntry] = []
    flagged: list[DistributorEntry] = []
    unknown_distributor: UnknownDistributorConfig = UnknownDistributorConfig()


class SiteEntry(BaseModel):
    """A site definition."""
    display_name: str
    aliases: list[str] = []
    template: Optional[str] = None  # Template filename
    mog: Optional[str] = None  # MOG filename
    ips: Optional[str] = None  # IPS filename


class SitesConfig(BaseModel):
    """Sites configuration from sites.yaml."""
    sites: dict[str, SiteEntry] = {}


class LocationEntry(BaseModel):
    """A storage location with sort order."""
    order: int
    aliases: list[str] = []


class LocationsConfig(BaseModel):
    """Locations configuration from locations.yaml."""
    locations: dict[str, LocationEntry] = {}
    default_location: str = "UNASSIGNED"


class FlagRule(BaseModel):
    """A custom flagging rule."""
    name: str
    condition: str  # Simple expression like "total_price > 500"
    severity: str = "warning"
    message: str


class ThresholdsConfig(BaseModel):
    """Override default thresholds."""
    dedicated_storage_value: float = 1000.0
    other_room_value: float = 200.0
    big_dollar_threshold: float = 250.0


class FlagsConfig(BaseModel):
    """Flags configuration from flags.yaml."""
    rules: list[FlagRule] = []
    thresholds: ThresholdsConfig = ThresholdsConfig()


class PluginSettings(BaseModel):
    """Plugin-level settings."""
    auto_categorize: bool = True
    strict_distributor_validation: bool = False


class PluginManifest(BaseModel):
    """Plugin manifest from plugin.yaml."""
    name: str
    version: str = "1.0"
    description: str = ""
    provides: list[str] = []
    settings: PluginSettings = PluginSettings()


class LoadedPlugin(BaseModel):
    """A fully loaded plugin with all its configurations."""
    manifest: PluginManifest
    distributors: DistributorsConfig = DistributorsConfig()
    sites: SitesConfig = SitesConfig()
    locations: LocationsConfig = LocationsConfig()
    flags: FlagsConfig = FlagsConfig()
    plugin_dir: str  # Path to plugin directory

    class Config:
        arbitrary_types_allowed = True
