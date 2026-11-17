from dataclasses import dataclass


@dataclass
class Resource:
    """Represents a collectible resource on the island."""

    kind: str
    row: int
    col: int
    resource_type: str
    quantity: int

    def collect(self, amount: int = 1) -> int:
        """Collect resources and return the amount actually collected."""

        if amount <= 0:
            raise ValueError("Collection amount must be positive.")

        collected = min(amount, self.quantity)

        self.quantity -= collected

        return collected