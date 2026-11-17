
from dataclasses import dataclass


@dataclass
class LootCache:
    """Represents resources left behind by a deceased explorer."""

    row: int
    col: int
    inventory: dict[str, int]

    def __post_init__(self):
        """Keep a separate copy of the inventory."""

        self.inventory = {
            resource: quantity
            for resource, quantity in self.inventory.items()
            if quantity > 0
        }

    def collect(self, resource_type: str, amount: int = 1) -> int:
        """Collect a resource and return the actual quantity collected."""

        if amount <= 0:
            raise ValueError("Collection amount must be positive.")

        available = self.inventory.get(resource_type, 0)

        collected = min(amount, available)

        self.inventory[resource_type] -= collected

        return collected

    @property
    def is_empty(self) -> bool:
        """Check whether the loot cache is empty."""

        return all(
            quantity <= 0
            for quantity in self.inventory.values()
        )
