"""Plugin discovery and loading system."""
import re
import logging
from pathlib import Path
from typing import Optional
import yaml

from .schema import (
    LoadedPlugin, PluginManifest, DistributorsConfig, SitesConfig,
    LocationsConfig, FlagsConfig, SiteEntry, DistributorEntry
)

logger = logging.getLogger(__name__)

# Plugins directory is at the project root, next to backend/
PLUGINS_DIR = Path(__file__).parent.parent.parent.parent / "plugins"


class PluginLoader:
    """Singleton loader for client plugins."""

    _instance: Optional['PluginLoader'] = None

    def __init__(self):
        self.plugins: dict[str, LoadedPlugin] = {}
        self._valid_distributors_cache: Optional[list[str]] = None
        self._flagged_distributors_cache: Optional[dict[str, DistributorEntry]] = None
        self._sites_cache: Optional[dict[str, tuple[str, SiteEntry]]] = None
        self._load_all()

    @classmethod
    def get(cls) -> 'PluginLoader':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reload(cls) -> 'PluginLoader':
        """Force reload all plugins."""
        cls._instance = None
        return cls.get()

    def _load_all(self):
        """Discover and load all plugins from the plugins directory."""
        if not PLUGINS_DIR.exists():
            logger.info(f"No plugins directory at {PLUGINS_DIR}")
            return

        for plugin_dir in PLUGINS_DIR.iterdir():
            if plugin_dir.is_dir():
                manifest_path = plugin_dir / "plugin.yaml"
                if manifest_path.exists():
                    try:
                        self._load_plugin(plugin_dir)
                    except Exception as e:
                        logger.error(f"Failed to load plugin {plugin_dir.name}: {e}")

        logger.info(f"Loaded {len(self.plugins)} plugin(s): {list(self.plugins.keys())}")

    def _load_yaml(self, path: Path) -> dict:
        """Load a YAML file, returning empty dict if not found."""
        if not path.exists():
            return {}
        with open(path) as f:
            return yaml.safe_load(f) or {}

    def _load_plugin(self, plugin_dir: Path):
        """Load a single plugin from its directory."""
        manifest_data = self._load_yaml(plugin_dir / "plugin.yaml")
        manifest = PluginManifest(**manifest_data)

        # Load each config file if provided
        distributors = DistributorsConfig()
        sites = SitesConfig()
        locations = LocationsConfig()
        flags = FlagsConfig()

        if "distributors" in manifest.provides:
            dist_data = self._load_yaml(plugin_dir / "distributors.yaml")
            if dist_data:
                distributors = DistributorsConfig(**dist_data)

        if "sites" in manifest.provides:
            sites_data = self._load_yaml(plugin_dir / "sites.yaml")
            if sites_data:
                sites = SitesConfig(**sites_data)

        if "locations" in manifest.provides:
            loc_data = self._load_yaml(plugin_dir / "locations.yaml")
            if loc_data:
                locations = LocationsConfig(**loc_data)

        if "flags" in manifest.provides:
            flags_data = self._load_yaml(plugin_dir / "flags.yaml")
            if flags_data:
                flags = FlagsConfig(**flags_data)

        plugin = LoadedPlugin(
            manifest=manifest,
            distributors=distributors,
            sites=sites,
            locations=locations,
            flags=flags,
            plugin_dir=str(plugin_dir)
        )

        self.plugins[manifest.name] = plugin
        logger.info(f"Loaded plugin: {manifest.name} v{manifest.version}")

    # -------------------------------------------------------------------------
    # Distributor Methods
    # -------------------------------------------------------------------------

    def _build_distributor_caches(self):
        """Build caches for distributor lookups."""
        if self._valid_distributors_cache is not None:
            return

        valid = []
        flagged = {}

        for plugin in self.plugins.values():
            # Valid distributors
            for dist in plugin.distributors.valid:
                valid.append(dist.name.lower())
                for alias in dist.aliases:
                    valid.append(alias.lower())

            # Flagged distributors
            for dist in plugin.distributors.flagged:
                flagged[dist.name.lower()] = dist
                for alias in dist.aliases:
                    flagged[alias.lower()] = dist

        self._valid_distributors_cache = valid
        self._flagged_distributors_cache = flagged

    def get_valid_distributors(self) -> list[str]:
        """Get all valid distributor names (lowercase)."""
        self._build_distributor_caches()
        return self._valid_distributors_cache or []

    def is_valid_distributor(self, name: str) -> bool:
        """Check if a distributor name is in the valid list."""
        if not name:
            return False
        self._build_distributor_caches()
        return name.lower() in (self._valid_distributors_cache or [])

    def is_distributor_flagged(self, name: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if a distributor should be flagged.

        Returns:
            (is_flagged, reason, severity) - reason and severity are None if not flagged
        """
        if not name:
            return False, None, None

        self._build_distributor_caches()
        entry = (self._flagged_distributors_cache or {}).get(name.lower())

        if entry:
            return True, entry.reason, entry.severity

        return False, None, None

    def matches_distributor_pattern(self, dist_num: str) -> bool:
        """Check if a distributor number matches any known pattern."""
        if not dist_num:
            return False

        for plugin in self.plugins.values():
            for dist in plugin.distributors.valid:
                if dist.dist_num_pattern:
                    try:
                        if re.match(dist.dist_num_pattern, dist_num):
                            return True
                    except re.error:
                        logger.warning(f"Invalid regex pattern: {dist.dist_num_pattern}")

        return False

    def get_unknown_distributor_config(self):
        """Get the unknown distributor handling config from the first plugin."""
        for plugin in self.plugins.values():
            return plugin.distributors.unknown_distributor
        # Default if no plugins
        from .schema import UnknownDistributorConfig
        return UnknownDistributorConfig()

    # -------------------------------------------------------------------------
    # Site Methods
    # -------------------------------------------------------------------------

    def _build_sites_cache(self):
        """Build cache for site lookups."""
        if self._sites_cache is not None:
            return

        cache = {}
        for plugin in self.plugins.values():
            for site_id, site_entry in plugin.sites.sites.items():
                # Map site_id and all aliases to (site_id, site_entry)
                cache[site_id.lower()] = (site_id, site_entry)
                for alias in site_entry.aliases:
                    cache[alias.lower()] = (site_id, site_entry)

        self._sites_cache = cache

    def get_site_config(self, site_id: str) -> Optional[SiteEntry]:
        """Get site configuration by ID or alias."""
        if not site_id:
            return None
        self._build_sites_cache()
        result = (self._sites_cache or {}).get(site_id.lower())
        return result[1] if result else None

    def normalize_site_id(self, raw_name: str) -> Optional[str]:
        """Normalize a site name to its canonical ID using plugin config."""
        if not raw_name:
            return None
        self._build_sites_cache()
        result = (self._sites_cache or {}).get(raw_name.lower())
        return result[0] if result else None

    def get_site_display_name(self, site_id: str) -> Optional[str]:
        """Get the display name for a site."""
        config = self.get_site_config(site_id)
        return config.display_name if config else None

    # -------------------------------------------------------------------------
    # Template & File Methods
    # -------------------------------------------------------------------------

    def get_template_path(self, site_id: str) -> Optional[Path]:
        """Get the template file path for a site from plugin."""
        config = self.get_site_config(site_id)
        if not config or not config.template:
            return None

        # Find which plugin has this site
        for plugin in self.plugins.values():
            if site_id in plugin.sites.sites or any(
                site_id.lower() in [a.lower() for a in s.aliases]
                for s in plugin.sites.sites.values()
            ):
                template_path = Path(plugin.plugin_dir) / "templates" / config.template
                if template_path.exists():
                    return template_path

        return None

    def get_mog_path(self, site_id: str) -> Optional[Path]:
        """Get the MOG file path for a site from plugin."""
        config = self.get_site_config(site_id)
        if not config or not config.mog:
            return None

        for plugin in self.plugins.values():
            if site_id in plugin.sites.sites:
                mog_path = Path(plugin.plugin_dir) / "mogs" / config.mog
                if mog_path.exists():
                    return mog_path

        return None

    def get_ips_path(self, site_id: str) -> Optional[Path]:
        """Get the IPS file path for a site from plugin."""
        config = self.get_site_config(site_id)
        if not config or not config.ips:
            return None

        for plugin in self.plugins.values():
            if site_id in plugin.sites.sites:
                ips_path = Path(plugin.plugin_dir) / "ips" / config.ips
                if ips_path.exists():
                    return ips_path

        return None

    # -------------------------------------------------------------------------
    # Location Methods
    # -------------------------------------------------------------------------

    def get_location_order(self) -> dict[str, int]:
        """Get merged location order from all plugins."""
        order = {}
        for plugin in self.plugins.values():
            for loc_name, loc_entry in plugin.locations.locations.items():
                order[loc_name] = loc_entry.order
                for alias in loc_entry.aliases:
                    order[alias] = loc_entry.order
        return order

    # -------------------------------------------------------------------------
    # Flags & Thresholds
    # -------------------------------------------------------------------------

    def get_thresholds(self):
        """Get thresholds from the first plugin with flags config."""
        for plugin in self.plugins.values():
            return plugin.flags.thresholds
        from .schema import ThresholdsConfig
        return ThresholdsConfig()

    def get_flag_rules(self) -> list:
        """Get all custom flag rules from plugins."""
        rules = []
        for plugin in self.plugins.values():
            rules.extend(plugin.flags.rules)
        return rules

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    def has_plugins(self) -> bool:
        """Check if any plugins are loaded."""
        return len(self.plugins) > 0

    def list_plugins(self) -> list[str]:
        """List all loaded plugin names."""
        return list(self.plugins.keys())
