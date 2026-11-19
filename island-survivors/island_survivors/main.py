
import salabim as sim
import random

from island_survivors.map_renderer import (
    draw_map,
    draw_explorers,
)

from island_survivors.explorers import create_explorers
from island_survivors.map_data import generate_scenario
from island_survivors.movement import ExplorerMovement
from island_survivors.survival import (
    ExplorerNeeds,
    LeaderNeeds,
)
from entities.leader import Leader
from island_survivors.dashboard import SimulationDashboard

from environment import create_resources
from agents.rule_based_agent import RuleBasedAgent
from orchestration.game_controller import ExplorerController

from entities.team_knowledge import TeamKnowledge
from entities.team_storage import TeamStorage
from entities.team_task_board import TeamTaskBoard

from orchestration.event_logger import EventLogger
from orchestration.team_manager import TeamManager


MASTER_SEED = 789


def print_gather_totals(event_logger):
    """Print total resources gathered by each team."""

    totals = {}

    events = event_logger.get_recent_events(
        limit=10000,
        include_debug=True,
    )

    for event in events:

        if event["event"] != "GATHER":
            continue

        team_id = event["team_id"]

        for detail in event["details"]:

            if not detail.startswith("Inventory - "):
                continue

            resource_info = detail[len("Inventory - "):]

            resource_type, quantities = resource_info.split(":", 1)

            old_quantity, new_quantity = quantities.split("->")

            collected = int(new_quantity) - int(old_quantity)

            team_totals = totals.setdefault(team_id, {})

            team_totals[resource_type.strip()] = (
                team_totals.get(resource_type.strip(), 0)
                + collected
            )

    print("\n" + "=" * 45)
    print("           RESOURCE GATHERING")
    print("=" * 45)

    for team_id, resources in sorted(totals.items()):

        print(f"\nTeam {team_id}")

        for resource_type, quantity in sorted(resources.items()):
            print(f"  {resource_type}: {quantity}")

    print("=" * 45)


def main():

    
    # Derive separate, reproducible seeds
    seed_generator = random.Random(MASTER_SEED)
    MAP_SEED = seed_generator.getrandbits(32)
    SIM_SEED = seed_generator.getrandbits(32)

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


    # Create one stationary leader for each team.
    team_leaders = {
        team_id: Leader(
            team_id=team_id,
            name=f"Leader {team_id}",
        )
        for team_id in active_bases
    }

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

    event_logger = EventLogger(debug=True, max_events=10000,)

    # --------------------------------------------------
    # 5. Create controllers and survival components.
    # --------------------------------------------------

    controllers_by_explorer = {}

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

            seed=SIM_SEED + index,
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

        controllers_by_explorer[explorer.name] = controller

        ExplorerNeeds(
            env=env,
            explorer=explorer,
            update_interval=5,
            event_logger=event_logger,
            death_handler=controller.handle_death,
        )


    # --------------------------------------------------
    # 6. Initialize team management.
    # --------------------------------------------------

    team_manager = TeamManager(
        env=env,
        team_leaders=team_leaders,
        explorers=explorers,
        controllers=controllers_by_explorer,
        event_logger=event_logger,
    )

    # Start survival processes for team leaders.
    for team_id, leader in team_leaders.items():

        LeaderNeeds(
            env=env,
            leader=leader,
            team_storage=team_storages[team_id],
            update_interval=5,
            event_logger=event_logger,

            # Leader death triggers team elimination.
            death_handler=team_manager.eliminate_team,
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
        team_leaders=team_leaders,
        team_states=team_manager.teams,
    )

    # --------------------------------------------------
    # 7. Run the simulation.
    # --------------------------------------------------

    env.run(till=sim.inf)

    team_manager.print_results()
    print_gather_totals(event_logger)


if __name__ == "__main__":
    main()
