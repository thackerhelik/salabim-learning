
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
        """Collect a quantity of a resource from the cache."""

        if type(amount) is not int or amount <= 0:
            raise ValueError(
                "Collection amount must be a positive integer."
            )

        available = self.inventory.get(resource_type, 0)

        if available <= 0:
            return 0

        collected = min(amount, available)
        remaining = available - collected

        if remaining > 0:
            self.inventory[resource_type] = remaining
        else:
            self.inventory.pop(resource_type, None)

        return collected

    @property
    def is_empty(self) -> bool:
        """Check whether the loot cache is empty."""

        return all(
            quantity <= 0
            for quantity in self.inventory.values()
        )
