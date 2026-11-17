from dataclasses import dataclass, field


@dataclass
class Explorer:
    """Represents an explorer in the island simulation."""

    name: str
    row: int
    col: int
    color: str

    team_id: int = 1

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
    Explorer(name="Ava", row=3, col=8, color="#E76F51", team_id=1),
    Explorer(name="Bram", row=3, col=9, color="#457BCE", team_id=1),
    Explorer(name="Cleo", row=7, col=4, color="#F30BF3", team_id=1),
    Explorer(name="Dax", row=7, col=6, color="#9B72CF", team_id=1),
]