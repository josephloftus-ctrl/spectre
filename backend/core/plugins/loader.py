"""Plugin discovery and loading system."""
import re
import logging
from pathlib import Path
from typing import Optional
import yaml

from .schema import (
    LoadedPlugin, PluginManifest, DistributorsConfig, SitesConfig,
    LocationsConfig, FlagsConfig, CategorizationConfig, SiteEntry, DistributorEntry
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
        categorization = CategorizationConfig()

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

        # Always try to load categorization if file exists
        cat_data = self._load_yaml(plugin_dir / "categorization.yaml")
        if cat_data:
            categorization = CategorizationConfig(**cat_data)

        plugin = LoadedPlugin(
            manifest=manifest,
            distributors=distributors,
            sites=sites,
            locations=locations,
            flags=flags,
            categorization=categorization,
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

    def get_inventory_template_path(self, site_id: str) -> Optional[Path]:
        """
        Get inventory template path with fallback to blank.xlsx.

        Tries in order:
        1. Site-specific template from plugin config
        2. Generic blank.xlsx from any plugin's templates folder
        3. Legacy Templates/ folder

        Args:
            site_id: Site identifier

        Returns:
            Path to template file, or None if no template found
        """
        # Try site-specific first
        site_template = self.get_template_path(site_id)
        if site_template and site_template.exists():
            logger.debug(f"Using site-specific template: {site_template}")
            return site_template

        # Fallback to blank.xlsx in any plugin's templates folder
        for plugin in self.plugins.values():
            blank_path = Path(plugin.plugin_dir) / "templates" / "blank.xlsx"
            if blank_path.exists():
                logger.debug(f"Using blank template fallback: {blank_path}")
                return blank_path

        # Try legacy Templates folder at project root
        project_root = Path(plugin.plugin_dir).parent.parent if self.plugins else None
        if project_root:
            legacy_paths = [
                project_root / "Templates" / "EmptyInventoryTemplate.xlsx",
                project_root / "Templates" / "blank.xlsx",
            ]
            for legacy_path in legacy_paths:
                if legacy_path.exists():
                    logger.debug(f"Using legacy template: {legacy_path}")
                    return legacy_path

        logger.warning(f"No inventory template found for site: {site_id}")
        return None

    def get_cart_template_path(self) -> Optional[Path]:
        """
        Get cart template path with fallback.

        Tries in order:
        1. cart.xlsx from any plugin's templates folder
        2. CartTemplate.xlsx from legacy Templates folder

        Returns:
            Path to cart template file, or None if not found
        """
        # Try plugin templates folders
        for plugin in self.plugins.values():
            cart_path = Path(plugin.plugin_dir) / "templates" / "cart.xlsx"
            if cart_path.exists():
                logger.debug(f"Using plugin cart template: {cart_path}")
                return cart_path

        # Try legacy Templates folder
        project_root = Path(list(self.plugins.values())[0].plugin_dir).parent.parent if self.plugins else None
        if project_root:
            legacy_cart = project_root / "Templates" / "CartTemplate.xlsx"
            if legacy_cart.exists():
                logger.debug(f"Using legacy cart template: {legacy_cart}")
                return legacy_cart

        logger.warning("No cart template found")
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
    # Categorization Methods
    # -------------------------------------------------------------------------

    def categorize_item(self, item_desc: str, brand: str = '', pack: str = '') -> tuple[str, bool]:
        """
        Categorize an item using plugin keywords.

        Args:
            item_desc: Item description
            brand: Brand name (optional)
            pack: Pack size (optional)

        Returns:
            (location, never_count) tuple
        """
        item_upper = str(item_desc).upper().strip()

        # Get merged categorization from all plugins
        cat = self._get_merged_categorization()

        # Check NEVER INVENTORY first
        for keyword in cat.get('never_inventory', []):
            if keyword.upper() in item_upper:
                return ('NEVER INVENTORY', True)

        # Check Freezer
        for keyword in cat.get('freezer', []):
            if keyword.upper() in item_upper:
                return ('Freezer', False)

        # Check Walk In Cooler
        for keyword in cat.get('cooler', []):
            if keyword.upper() in item_upper:
                return ('Walk In Cooler', False)

        # Check Beverage (skip if BAKING in name)
        if 'BAKING' not in item_upper:
            for keyword in cat.get('beverage', []):
                if keyword.upper() in item_upper:
                    return ('Beverage Room', False)

        # Check Dry Storage Food
        for keyword in cat.get('dry_food', []):
            if keyword.upper() in item_upper:
                return ('Dry Storage Food', False)

        # Check Dry Storage Supplies
        for keyword in cat.get('dry_supplies', []):
            if keyword.upper() in item_upper:
                return ('Dry Storage Supplies', False)

        # Check Chemical Locker
        for keyword in cat.get('chemical', []):
            if keyword.upper() in item_upper:
                return ('Chemical Locker', False)

        # Fallback checks
        if 'FROZ' in item_upper or 'IQF' in item_upper:
            return ('Freezer', False)
        if 'REFRIG' in item_upper or 'COLD' in item_upper:
            return ('Walk In Cooler', False)

        return ('UNASSIGNED', False)

    def _get_merged_categorization(self) -> dict:
        """Get merged categorization keywords from all plugins."""
        merged = {
            'never_inventory': [],
            'freezer': [],
            'cooler': [],
            'beverage': [],
            'dry_food': [],
            'dry_supplies': [],
            'chemical': [],
        }

        for plugin in self.plugins.values():
            cat = plugin.categorization
            merged['never_inventory'].extend(cat.never_inventory)
            merged['freezer'].extend(cat.freezer)
            merged['cooler'].extend(cat.cooler)
            merged['beverage'].extend(cat.beverage)
            merged['dry_food'].extend(cat.dry_food)
            merged['dry_supplies'].extend(cat.dry_supplies)
            merged['chemical'].extend(cat.chemical)

        return merged

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    def has_plugins(self) -> bool:
        """Check if any plugins are loaded."""
        return len(self.plugins) > 0

    def list_plugins(self) -> list[str]:
        """List all loaded plugin names."""
        return list(self.plugins.keys())
