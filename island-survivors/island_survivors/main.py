import salabim as sim

from island_survivors.map_renderer import (
    draw_map,
    draw_explorers,
)

from island_survivors.explorers import EXPLORERS
from island_survivors.map_data import MAP_LAYOUT, FEATURES
from island_survivors.movement import ExplorerMovement
from island_survivors.survival import ExplorerNeeds
from island_survivors.dashboard import SimulationDashboard

from environment import create_resources
from agents.rule_based_agent import RuleBasedAgent
from orchestration.game_controller import ExplorerController

from entities.team_knowledge import TeamKnowledge
from entities.team_storage import TeamStorage
from entities.team_task_board import TeamTaskBoard

from orchestration.event_logger import EventLogger


def main():

    # Initialize simulation environment
    env = sim.Environment(
        trace=False,
        random_seed=42,
    )

    # Configure animation window
    env.animation_parameters(
        animate=True,
        width=650,
        height=600,
        title="Island Survivors",
        background_color="#173449",
        speed=1,
        fps=30,
        show_fps=True,
        x0=0,
        y0=0,
        x1=650,
    )

    # Map configuration
    map_options = {
        "tile_size": 40,
        "origin_x": 40,
        "origin_y": 50,
    }

    # Draw the island
    draw_map(env, **map_options)

    resources = create_resources()
    loot_caches = {}

    # Find the existing chest on the map.
    chest_positions = [
        (row, col)
        for kind, row, col in FEATURES
        if kind == "chest"
    ]

    if not chest_positions:
        raise ValueError("No chest found on the map.")

    storage_row, storage_col = chest_positions[0]

    # Team task board
    team_task_boards = {
        team_id: TeamTaskBoard(team_id)
        for team_id in {
            explorer.team_id
            for explorer in EXPLORERS
        }
    }

    # Create one storage inventory per team.
    team_storages = {
        team_id: TeamStorage(
            team_id=team_id,
            row=storage_row,
            col=storage_col,
        )
        for team_id in {
            explorer.team_id
            for explorer in EXPLORERS
        }
    }

    # Create one shared knowledge board per team.
    team_knowledge_boards = {
        team_id: TeamKnowledge(team_id)
        for team_id in {
            explorer.team_id
            for explorer in EXPLORERS
        }
    }

    # Draw explorers
    explorer_animations = draw_explorers(
        env,
        EXPLORERS,
        **map_options,
    )


    # Positions occupied by map features
    blocked_positions = {
        (row, col)
        for _, row, col in FEATURES
    }

    # Initial positions occupied by explorers
    occupied_positions = {
        (explorer.row, explorer.col)
        for explorer in EXPLORERS
    }

    # Create event logger
    event_logger = EventLogger(debug=True)

    # Create a movement component for each explorer
    for index, explorer in enumerate(EXPLORERS):
        # Create a movement helper for this explorer.
        movement = ExplorerMovement(
            explorer=explorer,
            animation_objects=explorer_animations[explorer.name],

            map_layout=MAP_LAYOUT,
            blocked_positions=blocked_positions,
            occupied_positions=occupied_positions,

            map_options=map_options,

            move_duration=0.75,
            pause_duration=0.15,

            seed=42 + index,
        )

        # Create a decision-making controller.
        ExplorerController(
            env=env,
            explorer=explorer,
            agent=RuleBasedAgent(),
            resources=resources,
            movement=movement,

            loot_caches=loot_caches,
            occupied_positions=occupied_positions,

            team_knowledge=team_knowledge_boards[explorer.team_id],
            team_task_board=team_task_boards[explorer.team_id],
            team_storage=team_storages[explorer.team_id],

            decision_interval=1,
            event_logger=event_logger,
        )

        # Continue tracking hunger and health independently.
        ExplorerNeeds(
            env=env,
            explorer=explorer,
            update_interval=5,
            event_logger=event_logger,
        )

    # Create the live simulation dashboard.
    dashboard = SimulationDashboard(
        env=env,
        explorers=EXPLORERS,
        team_storages=team_storages,
        team_knowledge_boards=team_knowledge_boards,
        event_logger=event_logger,
    )

    # Keep the animation running.
    env.run(env.inf)


if __name__ == "__main__":
    main()