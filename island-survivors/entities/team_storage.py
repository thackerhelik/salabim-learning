from dataclasses import dataclass, field


@dataclass
class TeamStorage:
    """Represents a shared resource storage for a team."""

    team_id: int
    row: int
    col: int

    inventory: dict = field(
        default_factory=lambda: {
            "wood": 0,
            "stone": 0,
            "berries": 0,
        }
    )

    def deposit(self, resource_type, amount):
        """Add resources to team storage."""

        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")

        if resource_type not in self.inventory:
            raise ValueError(f"Unknown resource type: {resource_type}")

        self.inventory[resource_type] += amount

        return amount

    def withdraw(self, resource_type, amount):
        """Withdraw resources from team storage."""

        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")

        if resource_type not in self.inventory:
            raise ValueError(f"Unknown resource type: {resource_type}")

        available = self.inventory[resource_type]

        withdrawn = min(amount, available)

        self.inventory[resource_type] -= withdrawn

        return withdrawn
