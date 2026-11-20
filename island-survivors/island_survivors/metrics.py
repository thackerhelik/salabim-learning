RESOURCE_TYPES = ("wood", "stone", "berries")


def parse_resource_change(detail, prefix):
    """Extract a resource quantity change from an event detail."""

    if not detail.startswith(prefix):
        return None

    try:
        label, values = detail.split(":", 1)
        resource_type = label[len(prefix):].strip()

        previous, current = values.split("->")

        return (
            resource_type,
            int(previous.strip()),
            int(current.strip()),
        )

    except (ValueError, IndexError):
        return None


def collect_resource_economy_metrics(
    event_logger,
    team_storages,
    explorers,
    loot_caches,
    initial_storage_inventory,
):
    """Collect resource economy metrics without printing anything."""

    events = event_logger.get_recent_events(
        limit=None,
        include_debug=True,
    )

    metrics = {}

    for team_id, storage in team_storages.items():

        workers = [
            explorer
            for explorer in explorers
            if explorer.team_id == team_id
        ]

        initial = initial_storage_inventory.get(team_id, {})

        metrics[team_id] = {
            "team_id": team_id,
            "workers_total": len(workers),
            "workers_alive": sum(
                worker.is_alive for worker in workers
            ),

            "gathered": dict.fromkeys(RESOURCE_TYPES, 0),
            "looted": dict.fromkeys(RESOURCE_TYPES, 0),
            "deposited": dict.fromkeys(RESOURCE_TYPES, 0),
            "withdrawn": dict.fromkeys(RESOURCE_TYPES, 0),

            "worker_berries_consumed": 0,
            "worker_eat_events": 0,

            "leader_berries_consumed": 0,
            "leader_feed_events": 0,

            "deposit_events": 0,

            "starting_storage": {
                resource: initial.get(resource, 0)
                for resource in RESOURCE_TYPES
            },

            "ending_storage": {
                resource: storage.inventory.get(resource, 0)
                for resource in RESOURCE_TYPES
            },

            "resources_carried": {
                resource: sum(
                    worker.inventory.get(resource, 0)
                    for worker in workers
                )
                for resource in RESOURCE_TYPES
            },

            "storage_balance": {},
        }

    def add_amount(bucket, resource_type, amount):
        if resource_type in bucket:
            bucket[resource_type] += amount

    # --------------------------------------------------
    # 1. Process recorded events.
    # --------------------------------------------------

    for event in events:

        team_id = event["team_id"]

        if team_id not in metrics:
            continue

        team_metrics = metrics[team_id]
        event_type = event["event"]

        for detail in event.get("details") or []:

            inventory_change = parse_resource_change(
                detail,
                "Inventory - ",
            )

            storage_change = parse_resource_change(
                detail,
                "Team storage - ",
            )

            # World resource gathering.
            if event_type == "GATHER" and inventory_change:

                resource, previous, current = inventory_change

                add_amount(
                    team_metrics["gathered"],
                    resource,
                    max(0, current - previous),
                )

            # Recovery from loot caches.
            elif event_type == "LOOT" and inventory_change:

                resource, previous, current = inventory_change

                add_amount(
                    team_metrics["looted"],
                    resource,
                    max(0, current - previous),
                )

            # Worker food consumption.
            elif event_type == "EAT" and inventory_change:

                resource, previous, current = inventory_change

                if resource == "berries":

                    consumed = max(0, previous - current)

                    team_metrics["worker_berries_consumed"] += consumed

                    if consumed > 0:
                        team_metrics["worker_eat_events"] += 1

            # Deposits into team storage.
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

            # Worker withdrawals from team storage.
            elif event_type == "WITHDRAW" and storage_change:

                resource, previous, current = storage_change

                add_amount(
                    team_metrics["withdrawn"],
                    resource,
                    max(0, previous - current),
                )

            # Leader food consumption.
            if event_type == "LEADER_FED":

                if detail.startswith("Berries consumed:"):

                    consumed = int(
                        detail.split(":", 1)[1].strip()
                    )

                    team_metrics["leader_berries_consumed"] += consumed

                    if consumed > 0:
                        team_metrics["leader_feed_events"] += 1

    # --------------------------------------------------
    # 2. Calculate storage balance checks.
    # --------------------------------------------------

    for team_id, team_metrics in metrics.items():

        for resource in RESOURCE_TYPES:

            leader_consumption = (
                team_metrics["leader_berries_consumed"]
                if resource == "berries"
                else 0
            )

            expected = (
                team_metrics["starting_storage"][resource]
                + team_metrics["deposited"][resource]
                - team_metrics["withdrawn"][resource]
                - leader_consumption
            )

            actual = team_metrics["ending_storage"][resource]

            team_metrics["storage_balance"][resource] = {
                "expected": expected,
                "actual": actual,
                "ok": expected == actual,
            }

    # --------------------------------------------------
    # 3. Calculate remaining loot caches.
    # --------------------------------------------------

    remaining_loot = dict.fromkeys(RESOURCE_TYPES, 0)

    for cache in loot_caches.values():

        for resource in RESOURCE_TYPES:

            remaining_loot[resource] += (
                cache.inventory.get(resource, 0)
            )

    return {
        "teams": metrics,
        "remaining_loot": remaining_loot,
        "remaining_loot_cache_count": len(loot_caches),
    }


def print_resource_economy_summary(economy_metrics):
    """Print a previously collected resource economy report."""

    print("\n" + "=" * 55)
    print("                 RESOURCE ECONOMY")
    print("=" * 55)

    for team_id, team in sorted(economy_metrics["teams"].items()):

        def format_resources(inventory):
            return ", ".join(
                f"{resource}={inventory.get(resource, 0)}"
                for resource in RESOURCE_TYPES
            )

        print(f"\nTEAM {team_id}")
        print("-" * 45)

        print(
            f"Workers alive: "
            f"{team['workers_alive']}/{team['workers_total']}"
        )

        print(
            f"Gathered from world: "
            f"{format_resources(team['gathered'])}"
        )

        print(
            f"Recovered from loot: "
            f"{format_resources(team['looted'])}"
        )

        print(
            f"Deposited into storage: "
            f"{format_resources(team['deposited'])}"
        )

        print(
            f"Withdrawn by workers: "
            f"{format_resources(team['withdrawn'])}"
        )

        print(
            f"Berries consumed by workers: "
            f"{team['worker_berries_consumed']} "
            f"({team['worker_eat_events']} eating events)"
        )

        print(
            f"Berries consumed by leader: "
            f"{team['leader_berries_consumed']} "
            f"({team['leader_feed_events']} feeding events)"
        )

        print(f"Deposit events: {team['deposit_events']}")

        print(
            f"Starting storage: "
            f"{format_resources(team['starting_storage'])}"
        )

        print(
            f"Ending storage: "
            f"{format_resources(team['ending_storage'])}"
        )

        print(
            f"Resources still carried: "
            f"{format_resources(team['resources_carried'])}"
        )

        print("\nStorage balance checks:")

        for resource, balance in team["storage_balance"].items():

            status = "OK" if balance["ok"] else "MISMATCH"

            print(
                f"  {resource}: "
                f"expected={balance['expected']}, "
                f"actual={balance['actual']} [{status}]"
            )

    print("\n" + "-" * 45)
    print("REMAINING LOOT CACHES (ALL TEAMS)")

    print(
        format_resources(economy_metrics["remaining_loot"])
    )

    print(
        "Number of remaining caches: "
        f"{economy_metrics['remaining_loot_cache_count']}"
    )

    print("=" * 55)