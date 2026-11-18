from dataclasses import dataclass


@dataclass
class Leader:
    """Represents a team's stationary leader."""

    team_id: int
    name: str

    health: int = 100
    hunger: int = 0
    is_alive: bool = True