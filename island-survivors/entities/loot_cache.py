
from dataclasses import dataclass


@dataclass
class LootCache:
    """Represents resources left behind by a deceased explorer."""

    row: int
    col: int
    inventory: dict[str, int]

    def __post_init__(self):
        """Validate and copy the inventory."""

        clean_inventory = {}

        for resource, quantity in self.inventory.items():

            if not isinstance(resource, str) or not resource:
                raise ValueError(
                    "Resource names must be non-empty strings."
                )

            if type(quantity) is not int or quantity < 0:
                raise ValueError(
                    f"Invalid quantity for {resource}: {quantity}"
                )

            if quantity > 0:
                clean_inventory[resource] = quantity

        self.inventory = clean_inventory

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
