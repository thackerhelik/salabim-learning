
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



RESOURCE_TYPES = ("wood", "stone", "berries")


def parse_resource_change(detail, prefix):
    """Extract a resource quantity change from an event detail."""

    if not detail.startswith(prefix):
        return None

    try:
        label, values = detail.split(":", 1)
        resource_type = label[len(prefix):].strip()

        previous, current = values.split("->", 1)

        return (
            resource_type,
            int(previous.strip()),
            int(current.strip()),
        )

    except (ValueError, IndexError):
        return None


def print_resource_economy_summary(
    event_logger,
    team_storages,
    explorers,
    loot_caches,
    initial_storage_inventory,
):
    """Print a detailed resource-flow report for each team."""

    events = event_logger.get_recent_events(
        limit=10000,
        include_debug=True,
    )

    # Initialise counters for each team.
    metrics = {}

    for team_id in team_storages:

        metrics[team_id] = {
            "gathered": {},
            "looted": {},
            "deposited": {},
            "withdrawn": {},
            "worker_consumed": 0,
            "worker_eat_events": 0,
            "leader_consumed": 0,
            "leader_feed_events": 0,
            "deposit_events": 0,
        }

    def add_amount(bucket, resource_type, amount):
        bucket[resource_type] = (
            bucket.get(resource_type, 0) + amount
        )

    # --------------------------------------------------
    # 1. Analyse recorded events.
    # --------------------------------------------------

    for event in events:

        team_id = event["team_id"]

        if team_id not in metrics:
            continue

        event_type = event["event"]
        team_metrics = metrics[team_id]

        for detail in event.get("details") or []:

            inventory_change = parse_resource_change(
                detail,
                "Inventory - ",
            )

            storage_change = parse_resource_change(
                detail,
                "Team storage - ",
            )

            # Resources gathered directly from the world.
            if event_type == "GATHER" and inventory_change:

                resource, previous, current = inventory_change

                add_amount(
                    team_metrics["gathered"],
                    resource,
                    max(0, current - previous),
                )

            # Resources recovered from loot caches.
            elif event_type == "LOOT" and inventory_change:

                resource, previous, current = inventory_change

                add_amount(
                    team_metrics["looted"],
                    resource,
                    max(0, current - previous),
                )

            # Resources consumed by workers.
            elif event_type == "EAT" and inventory_change:

                resource, previous, current = inventory_change

                if resource == "berries":

                    consumed = max(0, previous - current)

                    team_metrics["worker_consumed"] += consumed

                    if consumed > 0:
                        team_metrics["worker_eat_events"] += 1

            # Resources deposited into team storage.
            elif event_type == "DEPOSIT" and storage_change:

                resource, previous, current = storage_change

                deposited = max(0, current - previous)

                add_amount(
                    team_metrics["deposited"],
                    resource,
                    deposited,
                )

                if deposited > 0:
                    team_metrics["deposit_events"] += 1

            # Resources withdrawn from team storage by workers.
            elif event_type == "WITHDRAW" and storage_change:

                resource, previous, current = storage_change

                add_amount(
                    team_metrics["withdrawn"],
                    resource,
                    max(0, previous - current),
                )

            # Resources consumed directly by the leader.
            if event_type == "LEADER_FED":

                if detail.startswith("Berries consumed:"):

                    consumed = int(
                        detail.split(":", 1)[1].strip()
                    )

                    team_metrics["leader_consumed"] += consumed

                    if consumed > 0:
                        team_metrics["leader_feed_events"] += 1

    # --------------------------------------------------
    # 2. Calculate resources remaining at episode end.
    # --------------------------------------------------

    loot_totals = {
        resource: 0
        for resource in RESOURCE_TYPES
    }

    for cache in loot_caches.values():

        for resource in RESOURCE_TYPES:

            loot_totals[resource] += (
                cache.inventory.get(resource, 0)
            )

    # --------------------------------------------------
    # 3. Print report.
    # --------------------------------------------------

    print("\n" + "=" * 55)
    print("                 RESOURCE ECONOMY")
    print("=" * 55)

    for team_id in sorted(team_storages):

        team_metrics = metrics[team_id]
        storage = team_storages[team_id]

        workers = [
            explorer
            for explorer in explorers
            if explorer.team_id == team_id
        ]

        initial = initial_storage_inventory.get(team_id, {})
        final = storage.inventory

        carried = {
            resource: sum(
                worker.inventory.get(resource, 0)
                for worker in workers
            )
            for resource in RESOURCE_TYPES
        }

        alive_workers = sum(
            worker.is_alive
            for worker in workers
        )

        def format_resources(inventory):
            return ", ".join(
                f"{resource}={inventory.get(resource, 0)}"
                for resource in RESOURCE_TYPES
            )

        print(f"\nTEAM {team_id}")
        print("-" * 45)

        print(
            f"Workers alive: "
            f"{alive_workers}/{len(workers)}"
        )

        print(
            f"Gathered from world: "
            f"{format_resources(team_metrics['gathered'])}"
        )

        print(
            f"Recovered from loot: "
            f"{format_resources(team_metrics['looted'])}"
        )

        print(
            f"Deposited into storage: "
            f"{format_resources(team_metrics['deposited'])}"
        )

        print(
            f"Withdrawn by workers: "
            f"{format_resources(team_metrics['withdrawn'])}"
        )

        print(
            f"Berries consumed by workers: "
            f"{team_metrics['worker_consumed']} "
            f"({team_metrics['worker_eat_events']} eating events)"
        )

        print(
            f"Berries consumed by leader: "
            f"{team_metrics['leader_consumed']} "
            f"({team_metrics['leader_feed_events']} feeding events)"
        )

        print(
            f"Deposit events: "
            f"{team_metrics['deposit_events']}"
        )

        print(
            f"Starting storage: "
            f"{format_resources(initial)}"
        )

        print(
            f"Ending storage: "
            f"{format_resources(final)}"
        )

        print(
            f"Resources still carried: "
            f"{format_resources(carried)}"
        )

        # Check that the storage accounting balances.
        print("\nStorage balance checks:")

        for resource in RESOURCE_TYPES:

            leader_consumption = (
                team_metrics["leader_consumed"]
                if resource == "berries"
                else 0
            )

            expected = (
                initial.get(resource, 0)
                + team_metrics["deposited"].get(resource, 0)
                - team_metrics["withdrawn"].get(resource, 0)
                - leader_consumption
            )

            actual = final.get(resource, 0)

            status = "OK" if expected == actual else "MISMATCH"

            print(
                f"  {resource}: "
                f"expected={expected}, actual={actual} "
                f"[{status}]"
            )

    # Loot caches are not currently associated with a team.
    print("\n" + "-" * 45)
    print("REMAINING LOOT CACHES (ALL TEAMS)")
    print(format_resources(loot_totals))
    print(f"Number of remaining caches: {len(loot_caches)}")

    print("=" * 55)



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

    print_resource_economy_summary(
        event_logger=event_logger,
        team_storages=team_storages,
        explorers=explorers,
        loot_caches=loot_caches,
        initial_storage_inventory=initial_storage_inventory,
    )


if __name__ == "__main__":
    main()
