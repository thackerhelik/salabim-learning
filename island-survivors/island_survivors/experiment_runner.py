import json
import subprocess
import csv
import random
import statistics
from pathlib import Path

from island_survivors.metrics import RESOURCE_TYPES


def get_git_metadata():
    """Retrieve the Git commit and tracked working-tree status."""

    project_root = Path(__file__).resolve().parents[1]

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        return {
            "commit": commit,
            "tracked_changes": bool(status),
        }

    except (FileNotFoundError, subprocess.CalledProcessError):

        return {
            "commit": "unavailable",
            "tracked_changes": None,
        }


def write_csv(path, rows):
    """Write dictionaries to a CSV file."""

    if not rows:
        raise ValueError(f"No data available to write to {path}.")

    # Combine keys so every row has the same CSV columns.
    fieldnames = list(
        dict.fromkeys(
            key
            for row in rows
            for key in row
        )
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)


def build_episode_row(
    run_index,
    experiment_seed,
    episode_seed,
    result,
):
    """Flatten one episode result into a CSV row."""

    episode = result["episode"]

    row = {
        "run_index": run_index,
        "experiment_seed": experiment_seed,
        "episode_master_seed": episode_seed,
        "map_seed": result["map_seed"],
        "sim_seed": result["sim_seed"],
        "placement": result["placement"],
        "number_of_teams": len(episode["teams"]),
        "episode_finished": episode["episode_finished"],
        "episode_duration": episode["episode_duration"],
        "outcome": episode["outcome"],
        "winner_team_id": result["winner_team_id"],
    }
    
    assignment = result.get("team_assignment")

    row["team_assignment"] = (
        json.dumps(assignment, sort_keys=True)
        if assignment is not None
        else ""
    )

    for team_id, team in sorted(episode["teams"].items()):

        prefix = f"team_{team_id}"

        row[f"{prefix}_status"] = team["status"]
        row[f"{prefix}_survival_time"] = team["survival_time"]
        row[f"{prefix}_eliminated_at"] = team["eliminated_at"]

        row[f"{prefix}_leader_final_health"] = team.get(
            "leader_final_health"
        )

        row[f"{prefix}_leader_final_hunger"] = team.get(
            "leader_final_hunger"
        )

    # Remaining loot is a global episode metric.
    economy = result["resource_economy"]

    row["remaining_loot_cache_count"] = (
        economy["remaining_loot_cache_count"]
    )

    for resource in RESOURCE_TYPES:
        row[f"remaining_loot_{resource}"] = (
            economy["remaining_loot"].get(resource, 0)
        )

    return row


def build_economy_rows(
    run_index,
    experiment_seed,
    episode_seed,
    result,
):
    """Flatten resource economy metrics into one row per team."""

    economy = result["resource_economy"]
    rows = []

    for team_id, team in sorted(economy["teams"].items()):

        row = {
            "run_index": run_index,
            "experiment_seed": experiment_seed,
            "episode_master_seed": episode_seed,
            "map_seed": result["map_seed"],
            "sim_seed": result["sim_seed"],
            "placement": result["placement"],
            "team_id": team_id,
            "workers_total": team["workers_total"],
            "workers_alive": team["workers_alive"],
            "worker_berries_consumed": team["worker_berries_consumed"],
            "worker_eat_events": team["worker_eat_events"],
            "leader_berries_consumed": team["leader_berries_consumed"],
            "leader_feed_events": team["leader_feed_events"],
            "deposit_events": team["deposit_events"],
        }

        # Flatten each resource dictionary.
        resource_groups = (
            "gathered",
            "looted",
            "deposited",
            "withdrawn",
            "starting_storage",
            "ending_storage",
            "resources_carried",
        )

        for group in resource_groups:

            for resource in RESOURCE_TYPES:

                row[f"{group}_{resource}"] = (
                    team[group].get(resource, 0)
                )

        # Include storage accounting checks.
        for resource in RESOURCE_TYPES:

            balance = team["storage_balance"][resource]

            row[f"storage_balance_{resource}_expected"] = (
                balance["expected"]
            )

            row[f"storage_balance_{resource}_actual"] = (
                balance["actual"]
            )

            row[f"storage_balance_{resource}_ok"] = (
                balance["ok"]
            )

        rows.append(row)

    return rows


def calculate_experiment_summary(
    experiment_seed,
    episode_results,
):
    """Calculate aggregate experiment statistics."""

    runs = len(episode_results)

    if runs == 0:
        raise ValueError("Cannot summarise an empty experiment.")

    team_ids = sorted(
        episode_results[0]["episode"]["teams"]
    )

    expected_team_ids = set(team_ids)

    # Every episode must contain the same teams.
    for run_index, result in enumerate(episode_results, start=1):

        episode_team_ids = set(result["episode"]["teams"])
        economy_team_ids = set(result["resource_economy"]["teams"])

        if episode_team_ids != expected_team_ids:
            raise ValueError(
                f"Team IDs differ in episode {run_index}: "
                f"expected {sorted(expected_team_ids)}, "
                f"found {sorted(episode_team_ids)}."
            )

        if economy_team_ids != expected_team_ids:
            raise ValueError(
                f"Resource economy team IDs differ in episode {run_index}."
            )

    summary = {
        "experiment_seed": experiment_seed,
        "number_of_episodes": runs,
        "number_of_teams": len(team_ids),
        "team_ids": team_ids,
    }

    winners = {
        team_id: 0
        for team_id in team_ids
    }

    draw_count = 0
    incomplete_count = 0

    episode_durations = []

    for result in episode_results:

        winner = result["winner_team_id"]

        if winner in winners:
            winners[winner] += 1

        elif result["episode"]["outcome"] == "DRAW":
            draw_count += 1

        else:
            incomplete_count += 1

        episode_durations.append(
            result["episode"]["episode_duration"]
        )

    summary["draw_count"] = draw_count
    summary["incomplete_count"] = incomplete_count

    summary["average_episode_duration"] = (
        statistics.fmean(episode_durations)
    )

    summary["episode_duration_stddev"] = (
        statistics.pstdev(episode_durations)
    )

    # Aggregate team-specific performance.
    for team_id in team_ids:

        prefix = f"team_{team_id}"

        survival_times = [
            result["episode"]["teams"][team_id]["survival_time"]
            for result in episode_results
        ]

        win_count = winners[team_id]

        summary[f"{prefix}_wins"] = win_count
        summary[f"{prefix}_win_rate"] = win_count / runs

        summary[f"{prefix}_average_survival"] = (
            statistics.fmean(survival_times)
        )

        summary[f"{prefix}_survival_stddev"] = (
            statistics.pstdev(survival_times)
        )

        def average_resource_metric(group, resource=None):

            values = []

            for result in episode_results:

                team = result["resource_economy"]["teams"][team_id]

                if resource is None:
                    value = team[group]
                else:
                    value = team[group].get(resource, 0)

                values.append(value)

            return statistics.fmean(values)

        summary[f"{prefix}_avg_berries_gathered"] = (
            average_resource_metric("gathered", "berries")
        )

        summary[f"{prefix}_avg_berries_deposited"] = (
            average_resource_metric("deposited", "berries")
        )

        summary[f"{prefix}_avg_worker_berries_consumed"] = (
            average_resource_metric("worker_berries_consumed")
        )

        summary[f"{prefix}_avg_leader_berries_consumed"] = (
            average_resource_metric("leader_berries_consumed")
        )

    # Average resources remaining in loot caches.
    for resource in RESOURCE_TYPES:

        remaining_values = [
            result["resource_economy"]["remaining_loot"].get(
                resource, 0
            )
            for result in episode_results
        ]

        summary[f"avg_remaining_loot_{resource}"] = (
            statistics.fmean(remaining_values)
        )

    summary["avg_remaining_loot_cache_count"] = (
        statistics.fmean(
            result["resource_economy"]["remaining_loot_cache_count"]
            for result in episode_results
        )
    )

    return summary


def print_experiment_summary(summary, team_ids):
    """Print the aggregate experiment results."""

    print("\n" + "=" * 60)
    print("                 EXPERIMENT SUMMARY")
    print("=" * 60)

    print(f"Experiment seed: {summary['experiment_seed']}")
    print(f"Episodes: {summary['number_of_episodes']}")
    print(f"Teams per episode: {summary['number_of_teams']}")

    print(
        f"Average episode duration: "
        f"{summary['average_episode_duration']:.2f}"
    )

    print(
        f"Episode duration stddev: "
        f"{summary['episode_duration_stddev']:.2f}"
    )

    print(f"Draws: {summary['draw_count']}")
    print(f"Incomplete episodes: {summary['incomplete_count']}")

    for team_id in team_ids:

        prefix = f"team_{team_id}"

        print(f"\nTEAM {team_id}")
        print("-" * 45)

        print(f"Wins: {summary[f'{prefix}_wins']}")

        print(
            f"Win rate: "
            f"{summary[f'{prefix}_win_rate'] * 100:.1f}%"
        )

        print(
            f"Average leader survival: "
            f"{summary[f'{prefix}_average_survival']:.2f}"
        )

        print(
            f"Survival time stddev: "
            f"{summary[f'{prefix}_survival_stddev']:.2f}"
        )

        print(
            f"Average berries gathered: "
            f"{summary[f'{prefix}_avg_berries_gathered']:.2f}"
        )

        print(
            f"Average berries deposited: "
            f"{summary[f'{prefix}_avg_berries_deposited']:.2f}"
        )

        print(
            f"Average berries consumed by workers: "
            f"{summary[f'{prefix}_avg_worker_berries_consumed']:.2f}"
        )

        print(
            f"Average berries consumed by leader: "
            f"{summary[f'{prefix}_avg_leader_berries_consumed']:.2f}"
        )

    print("\nGLOBAL RESOURCE REMAINS")
    print("-" * 45)

    for resource in RESOURCE_TYPES:

        print(
            f"Average remaining {resource}: "
            f"{summary[f'avg_remaining_loot_{resource}']:.2f}"
        )

    print(
        "Average remaining loot caches: "
        f"{summary['avg_remaining_loot_cache_count']:.2f}"
    )

    print("=" * 60)


def run_experiments(
    run_episode_fn,
    experiment_seed,
    runs,
    log_level="summary",
    output_dir="results/baseline_v1",
    placement="nw-se",
    teams=2,
    team_assignment=None,
):
    """Run multiple independent episodes and save their results."""

    if runs <= 0:
        raise ValueError("Number of runs must be positive.")

    if teams not in (2, 4):
        raise ValueError("Only 2-team and 4-team experiments are supported.")

    if teams == 2 and placement not in ("nw-se", "se-nw"):
        raise ValueError(
            f"Invalid two-team placement: {placement}"
        )

    if teams == 4 and placement != "four-corners":
        raise ValueError(
            "Four-team experiments must use placement='four-corners'."
        )

    if teams == 4 and team_assignment is not None:

        expected_positions = {"nw", "ne", "se", "sw"}

        if set(team_assignment.keys()) != expected_positions:
            raise ValueError(
                "Four-team assignment must contain "
                "nw, ne, se and sw."
            )

        if set(team_assignment.values()) != {1, 2, 3, 4}:
            raise ValueError(
                "Four-team assignment must assign "
                "each team exactly once."
            )

    elif teams == 2 and team_assignment is not None:

        raise ValueError(
            "Custom team assignments are only supported "
            "in four-team mode."
        )

    # Generate reproducible, distinct episode seeds.
    seed_generator = random.Random(experiment_seed)

    episode_seeds = []
    used_seeds = set()

    while len(episode_seeds) < runs:

        episode_seed = seed_generator.getrandbits(64)

        if episode_seed not in used_seeds:
            used_seeds.add(episode_seed)
            episode_seeds.append(episode_seed)

    all_results = []
    episode_rows = []
    economy_rows = []

    print(
        f"\nStarting experiment: {runs} episodes "
        f"(experiment seed={experiment_seed})"
    ) if log_level != "quiet" else None

    # --------------------------------------------------
    # Run each episode independently.
    # --------------------------------------------------

    for run_index, episode_seed in enumerate(
        episode_seeds,
        start=1,
    ):

        if log_level in {"info", "debug"}:
            print(
                f"\n--- Run {run_index}/{runs} "
                f"| Episode seed: {episode_seed} ---"
            )

        result = run_episode_fn(
            master_seed=episode_seed,
            headless=True,
            log_level=log_level,
            print_reports=False,
            placement=placement,
            teams=teams,
            team_assignment=team_assignment,
        )

        # Verify that the episode actually used the requested teams.
        expected_team_ids = set(range(1, teams + 1))

        actual_team_ids = set(result["episode"]["teams"])

        if actual_team_ids != expected_team_ids:
            raise ValueError(
                f"Episode {run_index} has unexpected teams: "
                f"{sorted(actual_team_ids)}."
            )

        # Verify resource metrics contain the same teams.
        economy_team_ids = set(result["resource_economy"]["teams"])

        if economy_team_ids != expected_team_ids:
            raise ValueError(
                f"Episode {run_index} has inconsistent resource metrics."
            )

        # Verify the placement assignment is consistent.
        if teams == 4:

            actual_assignment = result.get("team_assignment")

            if actual_assignment is None:
                raise ValueError(
                    f"Episode {run_index} did not return its team assignment."
                )

            expected_assignment = team_assignment

            if expected_assignment is None:
                expected_assignment = {
                    "nw": 1,
                    "ne": 2,
                    "se": 3,
                    "sw": 4,
                }

            if actual_assignment != expected_assignment:
                raise ValueError(
                    f"Episode {run_index} used an unexpected assignment."
                )

        all_results.append(result)

        episode_rows.append(
            build_episode_row(
                run_index=run_index,
                experiment_seed=experiment_seed,
                episode_seed=episode_seed,
                result=result,
            )
        )

        economy_rows.extend(
            build_economy_rows(
                run_index=run_index,
                experiment_seed=experiment_seed,
                episode_seed=episode_seed,
                result=result,
            )
        )

        if log_level == "summary":

            winner = result["winner_team_id"]

            winner_text = (
                f"Team {winner} wins"
                if winner is not None
                else result["episode"]["outcome"]
            )

            print(
                f"[Run {run_index}/{runs}] "
                f"{winner_text} | "
                f"Duration: "
                f"{result['episode']['episode_duration']:.1f}"
            )

        elif log_level in {"info", "debug"}:

            print(
                f"[Run {run_index}/{runs}] Completed | "
                f"Outcome: {result['episode']['outcome']}"
            )

    # --------------------------------------------------
    # Capture Git metadata.
    # --------------------------------------------------

    git_metadata = get_git_metadata()

    # --------------------------------------------------
    # Calculate aggregate statistics.
    # --------------------------------------------------

    summary = calculate_experiment_summary(
        experiment_seed=experiment_seed,
        episode_results=all_results,
    )
    
    summary["placement"] = placement

    summary["git_commit"] = git_metadata["commit"]

    summary["tracked_working_tree_changes"] = (
        git_metadata["tracked_changes"]
    )

    # --------------------------------------------------
    # Save experiment outputs.
    # --------------------------------------------------

    # Use a seed-specific folder so experiments with
    # different master seeds don't overwrite each other.
    experiment_path = (
        Path(output_dir)
        / f"seed_{experiment_seed}_runs_{runs}"
    )

    experiment_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Capture the code version used for this experiment.
    
    experiment_metadata = {
        "experiment_seed": experiment_seed,
        "number_of_episodes": runs,
        "number_of_teams": teams,
        "team_ids": sorted(
            all_results[0]["episode"]["teams"]
        ),
        "placement": placement,
        "team_assignment": (
            all_results[0].get("team_assignment")
            if teams == 4
            else None
        ),
        "log_level": log_level,
        "execution_mode": "headless",

        "git_commit": git_metadata["commit"],
        "tracked_working_tree_changes": (
            git_metadata["tracked_changes"]
        ),

        "episode_master_seeds": episode_seeds,

        "seed_derivation": (
            "Each episode master seed is derived from "
            "random.Random(experiment_seed)."
        ),
    }

    with (
        experiment_path / "metadata.json"
    ).open("w", encoding="utf-8") as file:

        json.dump(
            experiment_metadata,
            file,
            indent=4,
        )

    write_csv(
        experiment_path / "episodes.csv",
        episode_rows,
    )

    write_csv(
        experiment_path / "resource_economy.csv",
        economy_rows,
    )

    write_csv(
        experiment_path / "experiment_summary.csv",
        [summary],
    )

    # --------------------------------------------------
    # Display the aggregate report.
    # --------------------------------------------------

    team_ids = sorted(
        all_results[0]["episode"]["teams"]
    )

    print_experiment_summary(
        summary=summary,
        team_ids=team_ids,
    )

    print("\nExperiment files saved to:")
    print(experiment_path.resolve())

    return {
        "experiment_seed": experiment_seed,
        "runs": runs,
        "results": all_results,
        "summary": summary,
        "output_directory": str(experiment_path),
    }
