
import argparse
import csv
import json
import math
import random
import statistics

from pathlib import Path


OUTCOME_CATEGORIES = (
    "SAME_TEAM_WINS_BOTH",
    "DIFFERENT_TEAMS_WIN",
    "DRAW_BOTH",
    "ONE_DRAW_ONE_DECISIVE",
)

NUMERIC_COLUMNS = (
    "nw_se_team1_nw_survival",
    "nw_se_team2_se_survival",
    "se_nw_team2_nw_survival",
    "se_nw_team1_se_survival",
    "northwest_average_survival",
    "southeast_average_survival",
    "southeast_minus_northwest",
    "team1_average_survival",
    "team2_average_survival",
    "team1_minus_team2",
)

REQUIRED_COLUMNS = {
    "episode_master_seed",
    "map_seed",
    "sim_seed",
    *NUMERIC_COLUMNS,
    "nw_se_winner_location",
    "se_nw_winner_location",
    "nw_se_winner_team",
    "se_nw_winner_team",
    "pair_outcome_relation",
    "winner_location_changed",
}


def parse_bool(value, context):
    """Parse a CSV boolean value."""

    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(
        f"Invalid boolean value '{value}' in {context}."
    )


def classify_pair_outcome(team_a, team_b):
    """Classify the relationship between winners in both configurations."""

    if team_a == "DRAW" and team_b == "DRAW":
        return "DRAW_BOTH"

    if team_a == "DRAW" or team_b == "DRAW":
        return "ONE_DRAW_ONE_DECISIVE"

    if team_a == team_b:
        return "SAME_TEAM_WINS_BOTH"

    return "DIFFERENT_TEAMS_WIN"


def validate_paired_row(row, path):
    """Validate the consistency of one paired analysis row."""

    context = f"{path}, episode {row['episode_master_seed']}"

    # Check that the stored position difference is correct.
    expected_position_difference = (
        row["southeast_average_survival"]
        - row["northwest_average_survival"]
    )

    if not math.isclose(
        row["southeast_minus_northwest"],
        expected_position_difference,
        abs_tol=1e-9,
    ):
        raise ValueError(
            f"Inconsistent position difference in {context}."
        )

    # Check that the stored team difference is correct.
    expected_team_difference = (
        row["team1_average_survival"]
        - row["team2_average_survival"]
    )

    if not math.isclose(
        row["team1_minus_team2"],
        expected_team_difference,
        abs_tol=1e-9,
    ):
        raise ValueError(
            f"Inconsistent team difference in {context}."
        )

    valid_locations = {
        "NORTHWEST",
        "SOUTHEAST",
        "DRAW",
    }

    location_a = row["nw_se_winner_location"]
    location_b = row["se_nw_winner_location"]

    if location_a not in valid_locations:
        raise ValueError(
            f"Unexpected winner location '{location_a}' in {context}."
        )

    if location_b not in valid_locations:
        raise ValueError(
            f"Unexpected winner location '{location_b}' in {context}."
        )

    # Validate the winner team IDs.
    team_a = row["nw_se_winner_team"]
    team_b = row["se_nw_winner_team"]

    valid_teams = {"1", "2", "DRAW"}

    if team_a not in valid_teams or team_b not in valid_teams:
        raise ValueError(
            f"Unexpected winner team ID in {context}."
        )

    # Configuration A: Team 1 NW, Team 2 SE.
    expected_location_a = {
        "1": "NORTHWEST",
        "2": "SOUTHEAST",
        "DRAW": "DRAW",
    }[team_a]

    # Configuration B: Team 1 SE, Team 2 NW.
    expected_location_b = {
        "1": "SOUTHEAST",
        "2": "NORTHWEST",
        "DRAW": "DRAW",
    }[team_b]

    if location_a != expected_location_a:
        raise ValueError(
            f"Winner location/team mismatch in configuration A, {context}."
        )

    if location_b != expected_location_b:
        raise ValueError(
            f"Winner location/team mismatch in configuration B, {context}."
        )

    # Check the paired outcome classification.
    expected_relation = classify_pair_outcome(
        team_a,
        team_b,
    )

    if row["pair_outcome_relation"] != expected_relation:
        raise ValueError(
            f"Incorrect pair outcome classification in {context}."
        )

    # Check whether the winning location actually changed.
    expected_changed = location_a != location_b

    if row["winner_location_changed"] != expected_changed:
        raise ValueError(
            f"Inconsistent winner_location_changed value in {context}."
        )


def read_paired_csv(path, experiment_seed, expected_runs):
    """Read and validate one completed paired position analysis."""

    if not path.exists():
        raise FileNotFoundError(
            f"Paired analysis CSV not found: {path}"
        )

    rows = []
    episode_seeds = set()

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                f"{path} is missing columns: {sorted(missing)}"
            )

        for raw_row in reader:

            seed = raw_row["episode_master_seed"]

            if not seed:
                raise ValueError(
                    f"Missing episode master seed in {path}."
                )

            if seed in episode_seeds:
                raise ValueError(
                    f"Duplicate episode seed {seed} in {path}."
                )

            episode_seeds.add(seed)

            row = dict(raw_row)

            # Convert numerical fields from CSV strings to floats.
            for column in NUMERIC_COLUMNS:

                try:
                    row[column] = float(row[column])
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Invalid numeric value for '{column}' "
                        f"in {path}, episode {seed}."
                    )

            # Parse the boolean field.
            row["winner_location_changed"] = parse_bool(
                row["winner_location_changed"],
                f"{path}, episode {seed}",
            )

            # Preserve the experiment seed that produced this pair.
            row["source_experiment_seed"] = experiment_seed

            validate_paired_row(row, path)

            rows.append(row)

    if not rows:
        raise ValueError(
            f"No paired episodes found in {path}."
        )

    if len(rows) != expected_runs:
        raise ValueError(
            f"Expected {expected_runs} pairs in {path}, "
            f"but found {len(rows)}."
        )

    return rows


def percentile(values, quantile):
    """Calculate a percentile using linear interpolation."""

    ordered = sorted(values)

    if not ordered:
        raise ValueError(
            "Cannot calculate percentile of empty data."
        )

    position = (len(ordered) - 1) * quantile

    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)

    fraction = position - lower

    return (
        ordered[lower] * (1 - fraction)
        + ordered[upper] * fraction
    )


def bootstrap_mean_confidence_interval(
    values,
    seed,
    resamples=10000,
):
    """
    Estimate a 95% bootstrap confidence interval for the mean.

    Each value is one matched episode-pair difference.
    The paired observations are therefore resampled together.
    """

    if len(values) < 2:
        raise ValueError(
            "At least two paired observations are required."
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
        percentile(bootstrap_means, 0.025),
        percentile(bootstrap_means, 0.975),
    )


def calculate_combined_summary(
    paired_rows,
    experiment_seeds,
    runs_per_seed,
    bootstrap_seed,
    resamples,
):
    """Calculate aggregate statistics across all experiment seeds."""

    if not paired_rows:
        raise ValueError(
            "No paired observations available."
        )

    position_differences = [
        row["southeast_minus_northwest"]
        for row in paired_rows
    ]

    team_differences = [
        row["team1_minus_team2"]
        for row in paired_rows
    ]

    northwest_values = [
        row["northwest_average_survival"]
        for row in paired_rows
    ]

    southeast_values = [
        row["southeast_average_survival"]
        for row in paired_rows
    ]

    team1_values = [
        row["team1_average_survival"]
        for row in paired_rows
    ]

    team2_values = [
        row["team2_average_survival"]
        for row in paired_rows
    ]

    # Bootstrap CI using the complete set of paired differences.
    ci_low, ci_high = bootstrap_mean_confidence_interval(
        position_differences,
        seed=bootstrap_seed,
        resamples=resamples,
    )

    # Compare survival by starting position.
    northwest_better = sum(
        difference < 0
        for difference in position_differences
    )

    southeast_better = sum(
        difference > 0
        for difference in position_differences
    )

    equal = sum(
        difference == 0
        for difference in position_differences
    )

    # Aggregate winners across both placement configurations.
    location_wins = {
        "NORTHWEST": 0,
        "SOUTHEAST": 0,
        "DRAW": 0,
    }

    for row in paired_rows:

        for field in (
            "nw_se_winner_location",
            "se_nw_winner_location",
        ):

            location_wins[row[field]] += 1

    decisive_games = (
        location_wins["NORTHWEST"]
        + location_wins["SOUTHEAST"]
    )

    if decisive_games > 0:
        northwest_win_rate = (
            location_wins["NORTHWEST"] / decisive_games
        )

        southeast_win_rate = (
            location_wins["SOUTHEAST"] / decisive_games
        )
    else:
        northwest_win_rate = 0
        southeast_win_rate = 0

    # Aggregate the relationship between paired winners.
    outcome_counts = {
        category: sum(
            row["pair_outcome_relation"] == category
            for row in paired_rows
        )
        for category in OUTCOME_CATEGORIES
    }

    return {
        "experiment_seeds": experiment_seeds,
        "number_of_experiment_batches": len(experiment_seeds),
        "runs_per_experiment_seed": runs_per_seed,
        "matched_episode_pairs": len(paired_rows),
        "individual_episodes_across_both_configs": (
            len(paired_rows) * 2
        ),

        "average_northwest_survival": statistics.fmean(
            northwest_values
        ),

        "average_southeast_survival": statistics.fmean(
            southeast_values
        ),

        "mean_southeast_minus_northwest": statistics.fmean(
            position_differences
        ),

        "stddev_paired_position_difference": (
            statistics.stdev(position_differences)
            if len(position_differences) >= 2
            else 0
        ),

        "position_difference_ci95_low": ci_low,
        "position_difference_ci95_high": ci_high,

        "bootstrap_resamples": resamples,
        "bootstrap_seed": bootstrap_seed,
        "confidence_interval_method": (
            "95% percentile bootstrap CI using paired "
            "episode differences."
        ),

        "northwest_better_pairs": northwest_better,
        "southeast_better_pairs": southeast_better,
        "equal_survival_pairs": equal,

        "average_team1_survival": statistics.fmean(
            team1_values
        ),

        "average_team2_survival": statistics.fmean(
            team2_values
        ),

        "mean_team1_minus_team2": statistics.fmean(
            team_differences
        ),

        "northwest_wins_across_both_configs": (
            location_wins["NORTHWEST"]
        ),

        "southeast_wins_across_both_configs": (
            location_wins["SOUTHEAST"]
        ),

        "draws_across_both_configs": location_wins["DRAW"],

        "northwest_win_rate_excluding_draws": northwest_win_rate,
        "southeast_win_rate_excluding_draws": southeast_win_rate,

        "paired_outcome_counts": outcome_counts,

        "winner_location_changed_pairs": sum(
            row["winner_location_changed"]
            for row in paired_rows
        ),
    }


def write_csv(path, rows):
    """Write a list of dictionaries to CSV."""

    if not rows:
        raise ValueError(
            f"No rows to write to {path}."
        )

    fieldnames = list(rows[0].keys())

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def print_combined_summary(summary):
    """Print the combined position analysis."""

    print("\n" + "=" * 65)
    print("             COMBINED STARTING POSITION ANALYSIS")
    print("=" * 65)

    print(
        f"Experiment seeds: {summary['experiment_seeds']}"
    )

    print(
        f"Number of experiment batches: "
        f"{summary['number_of_experiment_batches']}"
    )

    print(
        f"Matched episode pairs: "
        f"{summary['matched_episode_pairs']}"
    )

    print(
        f"Individual episodes across both configurations: "
        f"{summary['individual_episodes_across_both_configs']}"
    )

    print("\nAVERAGE SURVIVAL BY STARTING POSITION")
    print("-" * 50)

    print(
        f"Northwest: "
        f"{summary['average_northwest_survival']:.2f}"
    )

    print(
        f"Southeast: "
        f"{summary['average_southeast_survival']:.2f}"
    )

    difference = summary["mean_southeast_minus_northwest"]

    print(
        f"\nMean paired difference (SE - NW): "
        f"{difference:+.2f}"
    )

    print(
        "95% bootstrap confidence interval: "
        f"[{summary['position_difference_ci95_low']:.2f}, "
        f"{summary['position_difference_ci95_high']:.2f}]"
    )

    print("\nPAIRED SCENARIO COUNTS")
    print("-" * 50)

    print(
        f"Northwest performed better: "
        f"{summary['northwest_better_pairs']}"
    )

    print(
        f"Southeast performed better: "
        f"{summary['southeast_better_pairs']}"
    )

    print(
        f"Equal survival: "
        f"{summary['equal_survival_pairs']}"
    )

    print("\nTEAM IDENTITY COMPARISON")
    print("-" * 50)

    print(
        f"Team 1 average survival: "
        f"{summary['average_team1_survival']:.2f}"
    )

    print(
        f"Team 2 average survival: "
        f"{summary['average_team2_survival']:.2f}"
    )

    print(
        f"Mean Team 1 - Team 2 difference: "
        f"{summary['mean_team1_minus_team2']:+.2f}"
    )

    print("\nWINNER BY STARTING LOCATION")
    print("-" * 50)

    print(
        f"Northwest wins: "
        f"{summary['northwest_wins_across_both_configs']}"
    )

    print(
        f"Southeast wins: "
        f"{summary['southeast_wins_across_both_configs']}"
    )

    print(
        f"Draws: "
        f"{summary['draws_across_both_configs']}"
    )

    print(
        f"Northwest win rate (excluding draws): "
        f"{summary['northwest_win_rate_excluding_draws'] * 100:.1f}%"
    )

    print(
        f"Southeast win rate (excluding draws): "
        f"{summary['southeast_win_rate_excluding_draws'] * 100:.1f}%"
    )

    print("\nPAIRED OUTCOME RELATIONSHIP")
    print("-" * 50)

    for category, count in summary["paired_outcome_counts"].items():
        label = category.replace("_", " ").title()
        print(f"{label}: {count}")

    print(
        "\nWinner location changed between configurations: "
        f"{summary['winner_location_changed_pairs']}"
    )

    print("=" * 65)


def parse_args(argv=None):
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Combine multiple paired starting-position experiments."
        )
    )

    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[123, 456],
        help=(
            "Experiment seeds to combine. "
            "Example: --seeds 123 456"
        ),
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=50,
        help="Matched episode pairs per experiment seed.",
    )

    parser.add_argument(
        "--results-dir",
        default="results/baseline_v1/position_bias",
        help="Root directory containing paired analysis results.",
    )

    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=2026,
        help="Random seed used for reproducible bootstrap resampling.",
    )

    parser.add_argument(
        "--resamples",
        type=int,
        default=10000,
        help="Number of bootstrap resamples.",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional custom output directory.",
    )

    return parser.parse_args(argv)


def main(args=None):
    """Combine paired position analyses from multiple experiment seeds."""

    if args is None:
        args = parse_args()

    if len(args.seeds) < 2:
        raise ValueError(
            "At least two experiment seeds are required."
        )

    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError(
            "Experiment seeds must be unique."
        )

    if args.runs < 2:
        raise ValueError(
            "At least two matched pairs per experiment seed are required."
        )

    if args.resamples < 1000:
        raise ValueError(
            "Use at least 1000 bootstrap resamples."
        )

    project_root = Path(__file__).resolve().parents[1]

    results_root = Path(args.results_dir)

    if not results_root.is_absolute():
        results_root = project_root / results_root

    print("Reading paired analysis results...")

    all_paired_rows = []
    all_episode_seeds = set()

    for experiment_seed in args.seeds:

        experiment_folder = (
            f"seed_{experiment_seed}_runs_{args.runs}"
        )

        paired_path = (
            results_root
            / "paired_analysis"
            / experiment_folder
            / "paired_position_analysis.csv"
        )

        print(
            f"\nLoading experiment seed {experiment_seed}..."
        )

        rows = read_paired_csv(
            paired_path,
            experiment_seed=experiment_seed,
            expected_runs=args.runs,
        )

        current_episode_seeds = {
            row["episode_master_seed"]
            for row in rows
        }

        duplicate_seeds = (
            all_episode_seeds & current_episode_seeds
        )

        if duplicate_seeds:
            raise ValueError(
                "Episode master seeds overlap between experiment batches: "
                f"{sorted(duplicate_seeds)}"
            )

        all_episode_seeds.update(current_episode_seeds)
        all_paired_rows.extend(rows)

        print(
            f"Validated {len(rows)} matched pairs "
            f"for seed {experiment_seed}."
        )

    expected_total = len(args.seeds) * args.runs

    if len(all_paired_rows) != expected_total:
        raise ValueError(
            f"Expected {expected_total} total pairs, "
            f"found {len(all_paired_rows)}."
        )

    print("\nAll experiment batches validated successfully.")

    summary = calculate_combined_summary(
        paired_rows=all_paired_rows,
        experiment_seeds=args.seeds,
        runs_per_seed=args.runs,
        bootstrap_seed=args.bootstrap_seed,
        resamples=args.resamples,
    )

    print_combined_summary(summary)

    # --------------------------------------------------
    # Save combined analysis results.
    # --------------------------------------------------

    if args.output_dir:

        output_path = Path(args.output_dir)

        if not output_path.is_absolute():
            output_path = project_root / output_path

    else:

        seed_label = "_".join(
            str(seed) for seed in args.seeds
        )

        output_path = (
            results_root
            / "combined_analysis"
            / f"seeds_{seed_label}_runs_{args.runs}"
        )

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_csv(
        output_path / "combined_paired_position_analysis.csv",
        all_paired_rows,
    )

    with (
        output_path / "combined_position_summary.json"
    ).open("w", encoding="utf-8") as file:

        json.dump(
            summary,
            file,
            indent=4,
        )

    print("\nCombined analysis files saved to:")
    print(output_path.resolve())


if __name__ == "__main__":
    main()
