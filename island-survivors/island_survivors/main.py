
import salabim as sim
import random

from island_survivors.map_renderer import (
    draw_map,
    draw_explorers,
)

from island_survivors.explorers import create_explorers
from island_survivors.map_data import generate_scenario
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


MASTER_SEED = 123


def main():

    
    # Derive separate, reproducible seeds
    seed_generator = random.Random(MASTER_SEED)
    MAP_SEED = seed_generator.getrandbits(32)
    SIM_SEED = seed_generator.getrandbits(32)

    scenario = generate_scenario(seed=MAP_SEED)

    # --------------------------------------------------
    # 1. Generate the world.
    # --------------------------------------------------

    scenario = generate_scenario(seed=MAP_SEED)

    map_layout = scenario["map_layout"]
    features = scenario["features"]
    bases = scenario["bases"]

    print(f"Starting scenario with seed {scenario['seed']}")

    # Activate two diagonally opposite bases.
    active_bases = {
        1: bases[0],  # Northwest
        2: bases[2],  # Southeast
    }

    # Create fresh workers for these teams.
    explorers = create_explorers(active_bases)

    # --------------------------------------------------
    # 2. Initialize the simulation.
    # --------------------------------------------------

    env = sim.Environment(
        trace=False,
        random_seed=SIM_SEED,
    )

    env.animation_parameters(
        animate=True,
        width=650,
        height=600,
        title="Island Survivors",
        background_color="#173449",
        speed=1,
        fps=30,
        show_fps=True,

        x0=15,
        y0=-30,
        x1=665,
    )

    # Map configuration.
    map_options = {
        "tile_size": 26,
        "origin_x": 65,
        "origin_y": 40,
    }

    # Draw the generated map.
    draw_map(
        env,
        map_layout,
        features,
        **map_options,
    )

    # Create world resources.
    resources = create_resources(features)
    loot_caches = {}

    # --------------------------------------------------
    # 3. Create team infrastructure.
    # --------------------------------------------------

    team_task_boards = {
        team_id: TeamTaskBoard(team_id)
        for team_id in active_bases
    }

    team_knowledge_boards = {
        team_id: TeamKnowledge(team_id)
        for team_id in active_bases
    }

    team_storages = {}

    for team_id, base in active_bases.items():

        storage_row, storage_col = base["storage_position"]

        team_storages[team_id] = TeamStorage(
            team_id=team_id,
            row=storage_row,
            col=storage_col,
        )

    # --------------------------------------------------
    # 4. Draw explorers and initialize occupancy.
    # --------------------------------------------------

    explorer_animations = draw_explorers(
        env,
        explorers,
        map_layout,
        features,
        **map_options,
    )

    blocked_positions = {
        (row, col)
        for _, row, col in features
    }

    occupied_positions = {
        (explorer.row, explorer.col)
        for explorer in explorers
    }

    event_logger = EventLogger(debug=True)

    # --------------------------------------------------
    # 5. Create controllers and survival components.
    # --------------------------------------------------

    for index, explorer in enumerate(explorers):

        movement = ExplorerMovement(
            explorer=explorer,
            animation_objects=explorer_animations[explorer.name],

            map_layout=map_layout,
            blocked_positions=blocked_positions,
            occupied_positions=occupied_positions,

            map_options=map_options,

            move_duration=0.75,
            pause_duration=0.15,

            seed=42 + index,
        )

        controller = ExplorerController(
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

        ExplorerNeeds(
            env=env,
            explorer=explorer,
            update_interval=5,
            event_logger=event_logger,
            death_handler=controller.handle_death,
        )

    # --------------------------------------------------
    # 6. Configure the dashboard.
    # --------------------------------------------------

    tile_size = map_options["tile_size"]
    origin_x = map_options["origin_x"]
    origin_y = map_options["origin_y"]

    map_bounds = (
        origin_x,
        origin_y,
        origin_x + len(map_layout[0]) * tile_size,
        origin_y + len(map_layout) * tile_size,
    )

    dashboard = SimulationDashboard(
        env=env,
        explorers=explorers,
        team_storages=team_storages,
        team_knowledge_boards=team_knowledge_boards,
        event_logger=event_logger,
        map_bounds=map_bounds,
    )

    # --------------------------------------------------
    # 7. Run the simulation.
    # --------------------------------------------------

    env.run(env.inf)


if __name__ == "__main__":
    main()
