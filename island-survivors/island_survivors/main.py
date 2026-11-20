
import salabim as sim
import random
import argparse
from pathlib import Path


from island_survivors.explorers import create_explorers
from island_survivors.map_data import generate_scenario
from island_survivors.movement import ExplorerMovement
from island_survivors.survival import (
    ExplorerNeeds,
    LeaderNeeds,
)
from island_survivors.metrics import (
    collect_resource_economy_metrics,
    print_resource_economy_summary,
)

from entities.leader import Leader

from environment import create_resources
from agents.rule_based_agent import RuleBasedAgent
from orchestration.game_controller import ExplorerController

from entities.team_knowledge import TeamKnowledge
from entities.team_storage import TeamStorage
from entities.team_task_board import TeamTaskBoard

from orchestration.event_logger import EventLogger
from orchestration.team_manager import TeamManager


MASTER_SEED = 789


def parse_args(argv=None):
    """Parse command-line configuration."""

    parser = argparse.ArgumentParser(
        description="Island Survivors simulation"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without map animation or dashboard.",
    )

    parser.add_argument(
        "--teams",
        type=int,
        choices=[2, 4],
        default=2,
        help="Number of active teams (2 or 4).",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=MASTER_SEED,
        help=f"Master random seed (default: {MASTER_SEED}).",
    )

    parser.add_argument(
        "--log-level",
        choices=["quiet", "summary", "info", "debug"],
        default=None,
        help="Console logging verbosity.",
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of episodes to run (default: 1).",
    )

    parser.add_argument(
        "--results-dir",
        type=str,
        default="results/baseline_v1",
        help="Directory for experiment CSV results.",
    )

    parser.add_argument(
        "--placement",
        choices=["nw-se", "se-nw"],
        default="nw-se",
        help=(
            "Assign Team 1 and Team 2 to Northwest/Southeast "
            "bases."
        ),
    )

    args = parser.parse_args(argv)

    if args.runs < 1:
        parser.error("--runs must be at least 1.")

    if args.runs > 1 and not args.headless:
        parser.error(
            "Multiple runs require --headless."
        )

    if args.runs > 1 and args.teams != 2:
        parser.error(
            "Batch experiments currently support only --teams 2. "
            "Four-team batch support will be added later."
        )

    if args.teams == 4 and args.placement != "nw-se":
        parser.error(
            "--placement is only applicable when --teams 2."
        )

    return args


def select_active_bases(bases, teams, placement):
    """Assign teams to their starting bases."""

    base_lookup = {
        "nw": bases[0],
        "ne": bases[1],
        "se": bases[2],
        "sw": bases[3],
    }

    # Four-team mode: activate all four bases.
    if teams == 4:

        return {
            1: base_lookup["nw"],
            2: base_lookup["ne"],
            3: base_lookup["se"],
            4: base_lookup["sw"],
        }

    # Two-team mode: preserve existing placement configurations.
    if teams == 2:

        team1_base, team2_base = placement.split("-")

        return {
            1: base_lookup[team1_base],
            2: base_lookup[team2_base],
        }

    raise ValueError(
        f"Unsupported number of teams: {teams}"
    )

def run_episode(
    master_seed,
    headless=True,
    log_level="quiet",
    print_reports=True,
    placement="nw-se",
    teams=2,
):
    """Run one complete simulation episode and return its results."""

    # Derive separate, reproducible seeds.
    seed_generator = random.Random(master_seed)

    MAP_SEED = seed_generator.getrandbits(32)
    SIM_SEED = seed_generator.getrandbits(32)

    # --------------------------------------------------
    # 1. Generate the world.
    # --------------------------------------------------

    scenario = generate_scenario(seed=MAP_SEED)

    map_layout = scenario["map_layout"]
    features = scenario["features"]
    bases = scenario["bases"]

    if print_reports and log_level != "quiet":
        print(
            f"Master seed: {master_seed} | "
            f"Map seed: {MAP_SEED} | "
            f"Simulation seed: {SIM_SEED}"
        )

    # Activate bases according to the selected team configuration.
    active_bases = select_active_bases(
        bases=bases,
        teams=teams,
        placement=placement,
    )

    # Create fresh workers for these teams.
    explorers = create_explorers(active_bases)

    
    # --------------------------------------------------
    # 2. Initialize the simulation.
    # --------------------------------------------------

    env = sim.Environment(
        trace=False,
        random_seed=SIM_SEED,
    )

    # Map configuration is shared by both execution modes.
    map_options = {
        "tile_size": 26,
        "origin_x": 65,
        "origin_y": 30,
    }

    # Animation and rendering are only initialized in visual mode.
    if not headless:

        from island_survivors.map_renderer import (
            draw_map,
            draw_explorers,
        )

        from island_survivors.dashboard import SimulationDashboard

        env.animation_parameters(
            animate=True,
            width=650,
            height=640,
            title="Island Survivors",
            background_color="#173449",
            speed=1,
            fps=30,
            show_fps=True,
            x0=15,
            y0=-30,
            x1=665,
        )

        draw_map(
            env,
            map_layout,
            features,
            **map_options,
        )

        explorer_animations = {}

    else:

        # No graphical objects are created in headless mode.
        explorer_animations = {}

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


    # Can add temporary initial values here if needed
    # eg. team_storages[2].inventory["berries"] = 6


    initial_storage_inventory = {
        team_id: storage.inventory.copy()
        for team_id, storage in team_storages.items()
    }

    # Create one stationary leader for each team.
    team_leaders = {
        team_id: Leader(
            team_id=team_id,
            name=f"Leader {team_id}",
        )
        for team_id in active_bases
    }

    # --------------------------------------------------
    # 4. Draw explorers (visual mode only).
    # --------------------------------------------------

    if not headless:

        explorer_animations = draw_explorers(
            env,
            explorers,
            map_layout,
            features,
            **map_options,
        )

    else:

        explorer_animations = {}

    blocked_positions = {
        (row, col)
        for _, row, col in features
    }

    occupied_positions = {
        (explorer.row, explorer.col)
        for explorer in explorers
    }

    event_logger = EventLogger(
        level=log_level,
        max_events=10000,
    )

    # --------------------------------------------------
    # 5. Create controllers and survival components.
    # --------------------------------------------------

    controllers_by_explorer = {}

    for index, explorer in enumerate(explorers):

        movement = ExplorerMovement(
            explorer=explorer,
            animation_objects=explorer_animations.get(explorer.name),

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
        announce_episode_finished=(
            print_reports and log_level != "quiet"
        ),
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

    if not headless:
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

    # --------------------------------------------------
    # Collect episode results.
    # --------------------------------------------------

    episode_results = team_manager.get_results()

    # Capture the final leader state for each team.
    for team_id, team_result in episode_results["teams"].items():

        leader = team_leaders[team_id]

        team_result["leader_final_health"] = leader.health
        team_result["leader_final_hunger"] = leader.hunger

    # --------------------------------------------------
    # Collect resource economy metrics.
    # --------------------------------------------------

    economy_metrics = collect_resource_economy_metrics(
        event_logger=event_logger,
        team_storages=team_storages,
        explorers=explorers,
        loot_caches=loot_caches,
        initial_storage_inventory=initial_storage_inventory,
    )

    # --------------------------------------------------
    # Print reports when requested.
    # --------------------------------------------------

    if print_reports:

        team_manager.print_results()

        if log_level != "quiet":
            print_resource_economy_summary(economy_metrics)

    # --------------------------------------------------
    # Return structured episode data.
    # --------------------------------------------------

    winner_team_id = None

    if episode_results["outcome"].startswith("TEAM "):
        winner_team_id = int(
            episode_results["outcome"].split()[1]
        )

    return {
        "master_seed": master_seed,
        "map_seed": MAP_SEED,
        "sim_seed": SIM_SEED,
        "placement": (
            "four-corners" if teams == 4 else placement
        ),

        "episode": episode_results,
        "winner_team_id": winner_team_id,

        "resource_economy": economy_metrics,
    }


def main(args=None):
    """Configure and execute one or multiple episodes."""

    if args is None:
        args = parse_args()

    # Default logging depends on execution mode.
    if args.log_level is None:
        log_level = (
            "summary" if args.headless else "debug"
        )
    else:
        log_level = args.log_level

    # --------------------------------------------------
    # Single episode.
    # --------------------------------------------------

    if args.runs == 1:

        return run_episode(
            master_seed=args.seed,
            headless=args.headless,
            log_level=log_level,
            placement=args.placement,
            teams=args.teams,
        )

    # --------------------------------------------------
    # Multiple episodes.
    # --------------------------------------------------

    from island_survivors.experiment_runner import run_experiments

    return run_experiments(
        run_episode_fn=run_episode,
        experiment_seed=args.seed,
        runs=args.runs,
        log_level=log_level,

        output_dir=str(
            Path(args.results_dir)
            / "position_bias"
            / args.placement
        ),

        placement=args.placement,
    )


if __name__ == "__main__":
    args = parse_args()
    main(args)