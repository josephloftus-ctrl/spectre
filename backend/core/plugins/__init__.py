"""Plugin system for client-specific configurations.

Plugins allow client-specific data (distributors, sites, templates, MOGs)
to be kept outside the main repository.

Usage:
    from backend.core.plugins import PluginLoader

    loader = PluginLoader.get()
    if loader.is_valid_distributor("Vistar Corporation"):
        # It's a valid distributor
        pass

    is_flagged, reason, severity = loader.is_distributor_flagged("Imperial Dade")
    if is_flagged:
        # Add a flag/warning
        pass
"""

from .loader import PluginLoader
from .schema import (
    LoadedPlugin,
    PluginManifest,
    DistributorsConfig,
    DistributorEntry,
    SitesConfig,
    SiteEntry,
    LocationsConfig,
    FlagsConfig,
    FlagRule,
    ThresholdsConfig,
)

__all__ = [
    "PluginLoader",
    "LoadedPlugin",
    "PluginManifest",
    "DistributorsConfig",
    "DistributorEntry",
    "SitesConfig",
    "SiteEntry",
    "LocationsConfig",
    "FlagsConfig",
    "FlagRule",
    "ThresholdsConfig",
]
