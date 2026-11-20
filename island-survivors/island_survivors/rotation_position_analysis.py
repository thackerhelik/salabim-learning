
import argparse
import csv
import json
import math
import random
import statistics

from collections import defaultdict
from itertools import combinations
from pathlib import Path


POSITIONS = ("nw", "ne", "se", "sw")
TEAM_IDS = (1, 2, 3, 4)

RESOURCE_METRICS = (
    "berries_gathered",
    "berries_looted",
    "berries_deposited",
    "worker_berries_consumed",
    "leader_berries_consumed",
)


def parse_bool(value, context):
    """Parse a CSV boolean value."""

    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(
        f"Invalid boolean '{value}' in {context}."
    )


def percentile(values, quantile):
    """Calculate a percentile using linear interpolation."""

    ordered = sorted(values)

    if not ordered:
        raise ValueError("Cannot calculate an empty percentile.")

    position = (len(ordered) - 1) * quantile

    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)

    fraction = position - lower

    return (
        ordered[lower] * (1 - fraction)
        + ordered[upper] * fraction
    )


def stable_seed(base_seed, label):
    """Generate a reproducible seed for a particular statistic."""

    offset = sum(
        (index + 1) * ord(character)
        for index, character in enumerate(str(label))
    )

    return base_seed + offset


def bootstrap_cluster_mean_ci(
    scenario_values,
    seed,
    resamples=10000,
):
    """
    Bootstrap a mean by resampling complete scenario clusters.

    Each dictionary value represents one scenario-level mean.
    """

    values = list(scenario_values.values())

    if len(values) < 2:
        raise ValueError(
            "At least two scenario clusters are required."
        )

    rng = random.Random(seed)

    sample_size = len(values)
    bootstrap_means = []

    for _ in range(resamples):

        sample = rng.choices(
            values,
            k=sample_size,
        )

        bootstrap_means.append(
            statistics.fmean(sample)
        )

    return (
        statistics.fmean(values),
        percentile(bootstrap_means, 0.025),
        percentile(bootstrap_means, 0.975),
    )


def build_scenario_group_means(rows, group_function, metric):
    """
    Calculate metric means for each group within each scenario.

    Example:
        Starting position NW, scenario 1 -> mean survival.
        Starting position NW, scenario 2 -> mean survival.
    """

    buckets = defaultdict(list)

    for row in rows:

        scenario = row["episode_master_seed"]
        group = group_function(row)

        buckets[(scenario, group)].append(
            row[metric]
        )

    result = defaultdict(dict)

    for (scenario, group), values in buckets.items():

        result[group][scenario] = statistics.fmean(values)

    return dict(result)


def validate_and_load(input_path, metadata_path):
    """Read the complete dataset and validate its experimental design."""

    if not input_path.exists():
        raise FileNotFoundError(
            f"Observation CSV not found: {input_path}"
        )

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata JSON not found: {metadata_path}"
        )

    with metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        metadata = json.load(file)

    if metadata["number_of_teams"] != 4:
        raise ValueError("Expected a four-team experiment.")

    if metadata["number_of_configurations"] != 24:
        raise ValueError("Expected 24 configurations.")

    positions = tuple(metadata["positions"])
    team_ids = tuple(metadata["team_ids"])

    if positions != POSITIONS or team_ids != TEAM_IDS:
        raise ValueError(
            "Metadata contains unexpected positions or team IDs."
        )

    expected_runs = metadata["runs_per_configuration"]
    expected_total = metadata["total_team_position_observations"]

    if expected_runs < 2:
        raise ValueError("At least two scenarios are required.")

    metadata_assignments = {}

    for configuration in metadata["assignments"]:

        config_id = configuration["configuration_id"]
        assignment = {
            position: int(team_id)
            for position, team_id
            in configuration["team_assignment"].items()
        }

        if set(assignment) != set(POSITIONS):
            raise ValueError(
                f"Invalid assignment in {config_id}."
            )

        if set(assignment.values()) != set(TEAM_IDS):
            raise ValueError(
                f"Invalid team assignment in {config_id}."
            )

        metadata_assignments[config_id] = {
            "configuration_index": configuration[
                "configuration_index"
            ],
            "assignment": assignment,
        }

    if len(metadata_assignments) != 24:
        raise ValueError("Metadata does not contain 24 unique assignments.")

    expected_episode_seeds = [
        int(seed)
        for seed in metadata["episode_master_seeds"]
    ]

    if len(expected_episode_seeds) != expected_runs:
        raise ValueError(
            "Metadata episode seed count does not match runs_per_configuration."
        )

    expected_seed_by_run = {
        index: seed
        for index, seed in enumerate(expected_episode_seeds, start=1)
    }

    required_columns = {
        "configuration_index",
        "configuration_id",
        "experiment_seed",
        "run_index",
        "episode_master_seed",
        "map_seed",
        "sim_seed",
        "team_assignment",
        "team_id",
        "starting_position",
        "survival_time",
        "won",
        "episode_draw",
        "episode_outcome",
        *RESOURCE_METRICS,
    }

    rows = []
    seen_observations = set()

    episode_groups = defaultdict(list)
    configuration_seeds = defaultdict(set)
    scenario_signatures = {}
    team_position_counts = defaultdict(int)
    scenario_team_position_counts = defaultdict(int)

    with input_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        missing = required_columns - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                f"CSV is missing columns: {sorted(missing)}"
            )

        for raw in reader:

            config_id = raw["configuration_id"]

            if config_id not in metadata_assignments:
                raise ValueError(
                    f"Unknown configuration: {config_id}"
                )

            config_metadata = metadata_assignments[config_id]

            config_index = int(raw["configuration_index"])
            experiment_seed = int(raw["experiment_seed"])
            run_index = int(raw["run_index"])
            episode_seed = int(raw["episode_master_seed"])
            map_seed = int(raw["map_seed"])
            sim_seed = int(raw["sim_seed"])
            team_id = int(raw["team_id"])
            position = raw["starting_position"]

            context = (
                f"{config_id}, run {run_index}, team {team_id}"
            )

            if config_index != config_metadata["configuration_index"]:
                raise ValueError(
                    f"Configuration index mismatch in {context}."
                )

            if experiment_seed != metadata["experiment_seed"]:
                raise ValueError(
                    f"Experiment seed mismatch in {context}."
                )

            if team_id not in TEAM_IDS:
                raise ValueError(
                    f"Unexpected team ID in {context}."
                )

            if position not in POSITIONS:
                raise ValueError(
                    f"Unexpected starting position in {context}."
                )

            if not 1 <= run_index <= expected_runs:
                raise ValueError(
                    f"Invalid run index in {context}."
                )

            if expected_seed_by_run[run_index] != episode_seed:
                raise ValueError(
                    f"Episode seed/run index mismatch in {context}."
                )

            # Validate the actual assignment stored in the CSV.
            assignment = json.loads(raw["team_assignment"])

            assignment = {
                position_key: int(value)
                for position_key, value in assignment.items()
            }

            expected_assignment = config_metadata["assignment"]

            if assignment != expected_assignment:
                raise ValueError(
                    f"Assignment mismatch in {context}."
                )

            expected_position = next(
                position_key
                for position_key, assigned_team in assignment.items()
                if assigned_team == team_id
            )

            if position != expected_position:
                raise ValueError(
                    f"Team-position mismatch in {context}."
                )

            # Each configuration/scenario/team must appear exactly once.
            observation_key = (
                config_id,
                episode_seed,
                team_id,
            )

            if observation_key in seen_observations:
                raise ValueError(
                    f"Duplicate observation in {context}."
                )

            seen_observations.add(observation_key)

            # Validate matched scenario seeds.
            signature = (
                run_index,
                map_seed,
                sim_seed,
            )

            previous_signature = scenario_signatures.get(
                episode_seed
            )

            if (
                previous_signature is not None
                and previous_signature != signature
            ):
                raise ValueError(
                    f"Scenario seed mismatch for episode {episode_seed}."
                )

            scenario_signatures[episode_seed] = signature

            # Convert metric values.
            row = {
                "configuration_index": config_index,
                "configuration_id": config_id,
                "experiment_seed": experiment_seed,
                "run_index": run_index,
                "episode_master_seed": episode_seed,
                "map_seed": map_seed,
                "sim_seed": sim_seed,
                "team_id": team_id,
                "starting_position": position,
                "won": parse_bool(raw["won"], context),
                "episode_draw": parse_bool(
                    raw["episode_draw"],
                    context,
                ),
                "episode_outcome": raw["episode_outcome"],
            }

            for metric in (
                "survival_time",
                *RESOURCE_METRICS,
            ):

                value = float(raw[metric])

                if not math.isfinite(value) or value < 0:
                    raise ValueError(
                        f"Invalid {metric} value in {context}."
                    )

                row[metric] = value

            assignment_json = json.dumps(
                assignment,
                sort_keys=True,
            )

            row["team_assignment"] = assignment_json

            rows.append(row)

            group_key = (
                config_id,
                episode_seed,
            )

            episode_groups[group_key].append(row)
            configuration_seeds[config_id].add(episode_seed)

            team_position_counts[
                (team_id, position)
            ] += 1

            scenario_team_position_counts[
                (episode_seed, team_id, position)
            ] += 1

    # --------------------------------------------------
    # Check total observation and episode counts.
    # --------------------------------------------------

    expected_episodes = 24 * expected_runs

    if len(rows) != expected_total:
        raise ValueError(
            f"Expected {expected_total} observations, found {len(rows)}."
        )

    if len(episode_groups) != expected_episodes:
        raise ValueError(
            f"Expected {expected_episodes} episodes, "
            f"found {len(episode_groups)}."
        )

    if set(configuration_seeds) != set(metadata_assignments):
        raise ValueError(
            "CSV does not contain exactly the expected configurations."
        )

    # Each configuration must use every scenario.
    expected_seed_set = set(expected_episode_seeds)

    for config_id, seeds in configuration_seeds.items():

        if seeds != expected_seed_set:
            raise ValueError(
                f"Scenario set mismatch in {config_id}."
            )

    # --------------------------------------------------
    # Check every episode has four internally consistent rows.
    # --------------------------------------------------

    for group_key, episode_rows in episode_groups.items():

        if len(episode_rows) != 4:
            raise ValueError(
                f"Expected four team observations in {group_key}."
            )

        actual_teams = {
            row["team_id"]
            for row in episode_rows
        }

        if actual_teams != set(TEAM_IDS):
            raise ValueError(
                f"Missing or duplicate teams in {group_key}."
            )

        outcomes = {
            row["episode_outcome"]
            for row in episode_rows
        }

        draw_values = {
            row["episode_draw"]
            for row in episode_rows
        }

        if len(outcomes) != 1 or len(draw_values) != 1:
            raise ValueError(
                f"Inconsistent episode outcome in {group_key}."
            )

        outcome = next(iter(outcomes))
        is_draw = next(iter(draw_values))

        if outcome == "DRAW":

            if not is_draw:
                raise ValueError(
                    f"Draw flag inconsistent in {group_key}."
                )

            if any(row["won"] for row in episode_rows):
                raise ValueError(
                    f"A draw cannot have a winning team in {group_key}."
                )

        elif outcome.startswith("TEAM ") and outcome.endswith(" WINS"):

            if is_draw:
                raise ValueError(
                    f"Winner episode incorrectly marked as draw in {group_key}."
                )

            winner_id = int(outcome.split()[1])

            winners = [
                row["team_id"]
                for row in episode_rows
                if row["won"]
            ]

            if winners != [winner_id]:
                raise ValueError(
                    f"Winner flag inconsistent in {group_key}."
                )

        else:
            raise ValueError(
                f"Unexpected outcome '{outcome}' in {group_key}."
            )

    # --------------------------------------------------
    # Verify the full factorial balance.
    # --------------------------------------------------

    expected_cell_count = 6 * expected_runs

    for team_id in TEAM_IDS:
        for position in POSITIONS:

            count = team_position_counts[(team_id, position)]

            if count != expected_cell_count:
                raise ValueError(
                    f"Unbalanced team-position cell: "
                    f"Team {team_id}, {position}: {count}."
                )

    for episode_seed in expected_episode_seeds:
        for team_id in TEAM_IDS:
            for position in POSITIONS:

                count = scenario_team_position_counts[
                    (episode_seed, team_id, position)
                ]

                if count != 6:
                    raise ValueError(
                        f"Expected six assignments for scenario "
                        f"{episode_seed}, Team {team_id}, {position}; "
                        f"found {count}."
                    )

    draw_episodes = sum(
        rows_for_episode[0]["episode_draw"]
        for rows_for_episode in episode_groups.values()
    )

    validation = {
        "observations": len(rows),
        "configurations": len(configuration_seeds),
        "matched_scenarios": expected_runs,
        "episodes": len(episode_groups),
        "draw_episodes": draw_episodes,
        "decisive_episodes": len(episode_groups) - draw_episodes,
        "team_position_cells": len(team_position_counts),
        "observations_per_team_position_cell": expected_cell_count,
    }

    return rows, metadata, validation


def summarize_groups(
    rows,
    group_function,
    group_labels,
    group_column,
    bootstrap_seed,
    resamples,
):
    """Summarize a group using scenario-cluster bootstrap intervals."""

    results = []

    for label in group_labels:

        group_rows = [
            row
            for row in rows
            if group_function(row) == label
        ]

        scenario_means = defaultdict(list)

        for row in group_rows:

            scenario_means[row["episode_master_seed"]].append(
                row["survival_time"]
            )

        scenario_means = {
            seed: statistics.fmean(values)
            for seed, values in scenario_means.items()
        }

        mean_survival, ci_low, ci_high = (
            bootstrap_cluster_mean_ci(
                scenario_means,
                seed=stable_seed(bootstrap_seed, label),
                resamples=resamples,
            )
        )

        record = {
            group_column: label,
            "observations": len(group_rows),
            "scenarios": len(scenario_means),
            "average_survival": mean_survival,
            "survival_ci95_low": ci_low,
            "survival_ci95_high": ci_high,
            "wins": sum(row["won"] for row in group_rows),
            "win_rate": (
                sum(row["won"] for row in group_rows)
                / len(group_rows)
            ),
        }

        for metric in RESOURCE_METRICS:

            record[f"average_{metric}"] = statistics.fmean(
                row[metric]
                for row in group_rows
            )

        results.append(record)

    return results


def calculate_pairwise_differences(
    rows,
    group_function,
    group_labels,
    bootstrap_seed,
    resamples,
):
    """Calculate paired differences between groups across scenarios."""

    scenario_means = build_scenario_group_means(
        rows=rows,
        group_function=group_function,
        metric="survival_time",
    )

    results = []

    for group_a, group_b in combinations(group_labels, 2):

        values_a = scenario_means[group_a]
        values_b = scenario_means[group_b]

        if set(values_a) != set(values_b):
            raise ValueError(
                "Groups do not contain identical scenario clusters."
            )

        paired_differences = {
            seed: values_a[seed] - values_b[seed]
            for seed in values_a
        }

        mean_difference, ci_low, ci_high = (
            bootstrap_cluster_mean_ci(
                paired_differences,
                seed=stable_seed(
                    bootstrap_seed,
                    f"{group_a}-{group_b}",
                ),
                resamples=resamples,
            )
        )

        results.append({
            "group_a": group_a,
            "group_b": group_b,
            "mean_difference_a_minus_b": mean_difference,
            "ci95_low": ci_low,
            "ci95_high": ci_high,
        })

    return results


def write_csv(path, rows):
    """Write dictionary rows to CSV."""

    if not rows:
        raise ValueError(f"No rows to write to {path}.")

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def print_summary(
    validation,
    position_summary,
    team_summary,
    team_position_summary,
    position_differences,
):
    """Print the analysis results."""

    print("\n" + "=" * 75)
    print("             FOUR-TEAM POSITION ANALYSIS")
    print("=" * 75)

    print("\nDATA VALIDATION")
    print("-" * 55)

    for key, value in validation.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    print("\nAVERAGE SURVIVAL BY STARTING POSITION")
    print("-" * 55)

    for row in position_summary:

        print(
            f"{row['starting_position'].upper():>3} | "
            f"Mean: {row['average_survival']:.2f} | "
            f"95% CI: "
            f"[{row['survival_ci95_low']:.2f}, "
            f"{row['survival_ci95_high']:.2f}] | "
            f"Wins: {row['wins']}"
        )

    print("\nAVERAGE SURVIVAL BY TEAM IDENTITY")
    print("-" * 55)

    for row in team_summary:

        print(
            f"Team {row['team_id']} | "
            f"Mean: {row['average_survival']:.2f} | "
            f"95% CI: "
            f"[{row['survival_ci95_low']:.2f}, "
            f"{row['survival_ci95_high']:.2f}] | "
            f"Wins: {row['wins']}"
        )

    print("\nTEAM-POSITION SURVIVAL MATRIX")
    print("-" * 55)

    print(
        "Team  | "
        + " | ".join(position.upper() for position in POSITIONS)
    )

    for team_id in TEAM_IDS:

        values = [
            next(
                row["average_survival"]
                for row in team_position_summary
                if row["team_id"] == team_id
                and row["starting_position"] == position
            )
            for position in POSITIONS
        ]

        print(
            f"{team_id:>4}  | "
            + " | ".join(f"{value:.2f}" for value in values)
        )

    print("\nPAIRWISE POSITION DIFFERENCES (A - B)")
    print("-" * 55)

    for row in position_differences:

        print(
            f"{row['group_a'].upper()} - "
            f"{row['group_b'].upper()}: "
            f"{row['mean_difference_a_minus_b']:+.2f} "
            f"[{row['ci95_low']:.2f}, {row['ci95_high']:.2f}]"
        )

    print("=" * 75)


def parse_args(argv=None):
    """Parse analysis command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Analyse four-team rotational position experiments."
        )
    )

    parser.add_argument(
        "--input",
        default=(
            "results/baseline_v2/four_team_rotations/"
            "combined_seed_123_runs_20/"
            "team_position_observations.csv"
        ),
        help="Path to the combined team-position observations CSV.",
    )

    parser.add_argument(
        "--metadata",
        default=None,
        help="Path to metadata.json. Defaults to the CSV's directory.",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for analysis outputs.",
    )

    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=2026,
    )

    parser.add_argument(
        "--resamples",
        type=int,
        default=10000,
    )

    return parser.parse_args(argv)


def main(args=None):
    """Run the complete rotational position analysis."""

    if args is None:
        args = parse_args()

    if args.resamples < 1000:
        raise ValueError(
            "At least 1000 bootstrap resamples are required."
        )

    project_root = Path(__file__).resolve().parents[1]

    input_path = Path(args.input)

    if not input_path.is_absolute():
        input_path = project_root / input_path

    if args.metadata:

        metadata_path = Path(args.metadata)

        if not metadata_path.is_absolute():
            metadata_path = project_root / metadata_path

    else:
        metadata_path = input_path.parent / "metadata.json"

    print("Reading observations and metadata...")

    rows, metadata, validation = validate_and_load(
        input_path,
        metadata_path,
    )

    print(
        f"Validated {validation['observations']} observations "
        f"across {validation['episodes']} episodes."
    )

    print(
        "All 24 configurations, scenario seeds and "
        "team-position assignments are consistent."
    )

    # --------------------------------------------------
    # Position summaries.
    # --------------------------------------------------

    position_summary = summarize_groups(
        rows=rows,
        group_function=lambda row: row["starting_position"],
        group_labels=POSITIONS,
        group_column="starting_position",
        bootstrap_seed=args.bootstrap_seed,
        resamples=args.resamples,
    )

    # --------------------------------------------------
    # Team identity summaries.
    # --------------------------------------------------

    team_summary = summarize_groups(
        rows=rows,
        group_function=lambda row: row["team_id"],
        group_labels=TEAM_IDS,
        group_column="team_id",
        bootstrap_seed=args.bootstrap_seed,
        resamples=args.resamples,
    )

    # --------------------------------------------------
    # Team-position interaction summaries.
    # --------------------------------------------------

    team_position_labels = [
        (team_id, position)
        for team_id in TEAM_IDS
        for position in POSITIONS
    ]

    team_position_summary = []

    for team_id, position in team_position_labels:

        cell_summary = summarize_groups(
            rows=rows,
            group_function=lambda row, t=team_id, p=position: (
                row["team_id"] == t
                and row["starting_position"] == p
            ),
            group_labels=[True],
            group_column="cell",
            bootstrap_seed=args.bootstrap_seed,
            resamples=args.resamples,
        )[0]

        cell_summary.pop("cell")

        cell_summary["team_id"] = team_id
        cell_summary["starting_position"] = position

        team_position_summary.append(cell_summary)

    # --------------------------------------------------
    # Paired position comparisons.
    # --------------------------------------------------

    position_differences = calculate_pairwise_differences(
        rows=rows,
        group_function=lambda row: row["starting_position"],
        group_labels=POSITIONS,
        bootstrap_seed=args.bootstrap_seed,
        resamples=args.resamples,
    )

    # --------------------------------------------------
    # Paired team identity comparisons.
    # --------------------------------------------------

    team_differences = calculate_pairwise_differences(
        rows=rows,
        group_function=lambda row: row["team_id"],
        group_labels=TEAM_IDS,
        bootstrap_seed=args.bootstrap_seed,
        resamples=args.resamples,
    )

    # --------------------------------------------------
    # Print report.
    # --------------------------------------------------

    print_summary(
        validation=validation,
        position_summary=position_summary,
        team_summary=team_summary,
        team_position_summary=team_position_summary,
        position_differences=position_differences,
    )

    # --------------------------------------------------
    # Save analysis results.
    # --------------------------------------------------

    if args.output_dir:

        output_path = Path(args.output_dir)

        if not output_path.is_absolute():
            output_path = project_root / output_path

    else:
        output_path = input_path.parent / "rotation_analysis"

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_csv(
        output_path / "position_summary.csv",
        position_summary,
    )

    write_csv(
        output_path / "team_summary.csv",
        team_summary,
    )

    write_csv(
        output_path / "team_position_summary.csv",
        team_position_summary,
    )

    write_csv(
        output_path / "position_pairwise_differences.csv",
        position_differences,
    )

    write_csv(
        output_path / "team_pairwise_differences.csv",
        team_differences,
    )

    analysis_summary = {
        "experiment_seed": metadata["experiment_seed"],
        "number_of_configurations": 24,
        "matched_scenarios": metadata["runs_per_configuration"],
        "total_episodes": validation["episodes"],
        "total_observations": validation["observations"],
        "draw_episodes": validation["draw_episodes"],
        "decisive_episodes": validation["decisive_episodes"],

        "bootstrap": {
            "method": (
                "Percentile bootstrap over complete "
                "episode master seed scenario clusters."
            ),
            "resamples": args.resamples,
            "seed": args.bootstrap_seed,
            "number_of_clusters": metadata["runs_per_configuration"],
        },

        "validation": validation,
        "position_summary": position_summary,
        "team_summary": team_summary,
        "team_position_summary": team_position_summary,
        "position_pairwise_differences": position_differences,
        "team_pairwise_differences": team_differences,
    }

    with (
        output_path / "analysis_summary.json"
    ).open("w", encoding="utf-8") as file:

        json.dump(
            analysis_summary,
            file,
            indent=4,
        )

    print("\nAnalysis files saved to:")
    print(output_path.resolve())


if __name__ == "__main__":
    main()
