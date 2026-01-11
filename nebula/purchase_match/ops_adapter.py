"""
Ops Dashboard Inventory Adapter - Production adapter stub.

This is a placeholder for the real ops dashboard integration.
Implement once the ops dashboard query interface is documented.
"""

from .adapters import InventoryAdapter
from .models import InventoryRecord


class OpsDashboardInventoryAdapter(InventoryAdapter):
    """
    Production adapter for ops dashboard inventory.

    TODO: Implement once ops dashboard query interface is documented.

    Expected integration points:
    - Query existing inventory valuations by unit
    - Map ops dashboard fields to InventoryRecord
    - Handle authentication/authorization

    Required information to implement:
    - API endpoint or database connection details
    - Field mapping (ops dashboard field names -> InventoryRecord)
    - Authentication method (API key, OAuth, etc.)
    - Unit identifier format in ops dashboard
    """

    def __init__(self, connection_string: str | None = None):
        """
        Initialize adapter with connection details.

        Args:
            connection_string: Connection details (format TBD)
        """
        self._connection = connection_string
        # Placeholder for actual connection setup

    def get_inventory_for_unit(self, unit: str) -> list[InventoryRecord]:
        """
        Fetch inventory records for a unit from ops dashboard.

        Args:
            unit: Unit identifier (e.g., "PSEG_HQ")

        Returns:
            List of InventoryRecord for that unit

        Raises:
            NotImplementedError: Until ops dashboard integration is ready
        """
        raise NotImplementedError(
            "Ops dashboard integration pending.\n"
            "Need: query interface, field mapping, auth method.\n"
            "See SPEC-007 Open Questions for details.\n"
            "Use MockInventoryAdapter or InMemoryInventoryAdapter for testing."
        )

    def get_all_units(self) -> list[str]:
        """
        Get list of all units from ops dashboard.

        Returns:
            List of unit identifiers

        Raises:
            NotImplementedError: Until ops dashboard integration is ready
        """
        raise NotImplementedError(
            "Ops dashboard integration pending.\n"
            "Use MockInventoryAdapter.get_all_units() for testing."
        )
