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


def create_explorers(team_bases):
    """Create fresh workers for the supplied team bases."""

    worker_templates = [
        [
            ("Ava", "#E76F51"),
            ("Bram", "#457BCE"),
        ],
        [
            ("Cleo", "#E9C74B"),
            ("Dax", "#9B72CF"),
        ],
        [
            ("Eli", "#4EAD83"),
            ("Faye", "#D17BB5"),
        ],
        [
            ("Gus", "#D69B48"),
            ("Hana", "#65B8C7"),
        ],
    ]

    explorers = []

    for team_index, (team_id, base) in enumerate(
        sorted(team_bases.items())
    ):

        if team_index >= len(worker_templates):
            raise ValueError("Maximum of four teams supported.")

        spawn_positions = base["spawn_positions"]

        if len(spawn_positions) != 2:
            raise ValueError(
                f"Team {team_id} must have two spawn positions."
            )

        for worker_index, position in enumerate(spawn_positions):

            name, color = worker_templates[team_index][worker_index]

            row, col = position

            explorers.append(
                Explorer(
                    name=name,
                    row=row,
                    col=col,
                    color=color,
                    team_id=team_id,
                )
            )

    return explorers