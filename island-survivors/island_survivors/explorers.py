from dataclasses import dataclass, field


@dataclass
class Explorer:
    """Represents an explorer in the island simulation."""

    name: str
    row: int
    col: int
    color: str

    health: int = 100
    hunger: int = 0

    inventory: dict = field(
        default_factory=lambda: {
            "wood": 0,
            "stone": 0,
            "berries": 0,
        }
    )

    is_alive: bool = True

# Initial explorers
EXPLORERS = [
    Explorer(name="Ava", row=3, col=8, color="#E76F51"),
    Explorer("Bram", 3, 9, "#457BCE"),
    Explorer("Cleo", 7, 4, "#F30BF3"),
    Explorer("Dax", 7, 6, "#9B72CF"),
]