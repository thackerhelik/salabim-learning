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


def create_explorers():
    """Create a fresh set of explorers for a simulation run."""

    return [
        Explorer(
            "Ava",
            3,
            8,
            "#E76F51",
            team_id=1,
        ),
        Explorer(
            "Bram",
            3,
            9,
            "#457BCE",
            team_id=1,
        ),
        Explorer(
            "Cleo",
            7,
            4,
            "#E9C74B",
            team_id=1,
        ),
        Explorer(
            "Dax",
            7,
            6,
            "#9B72CF",
            team_id=1,
        ),
    ]