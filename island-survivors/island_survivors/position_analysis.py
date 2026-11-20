import argparse
import csv
import json
import random
import statistics

from pathlib import Path


PLACEMENTS = ("nw-se", "se-nw")


def read_episode_csv(path, expected_placement):
    """Read and validate an episode CSV, indexed by episode master seed."""

    if not path.exists():
        raise FileNotFoundError(
            f"Episode CSV not found: {path}"
        )

    episodes = {}

    required_columns = {
        "episode_master_seed",
        "map_seed",
        "sim_seed",
        "placement",
        "episode_finished",
        "episode_duration",
        "outcome",
        "winner_team_id",
        "team_1_survival_time",
        "team_2_survival_time",
    }

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(file)

        missing = required_columns - set(reader.fieldnames or [])

        if missing:
            raise ValueError(
                f"{path} is missing columns: {sorted(missing)}"
            )

        for row in reader:

            seed = row["episode_master_seed"]

            if not seed:
                raise ValueError(
                    f"Missing episode master seed in {path}."
                )

            if seed in episodes:
                raise ValueError(
                    f"Duplicate episode seed {seed} in {path}."
                )

            if row["placement"] != expected_placement:
                raise ValueError(
                    f"Expected placement {expected_placement}, "
                    f"found {row['placement']} in {path}."
                )

            if row["episode_finished"].lower() != "true":
                raise ValueError(
                    f"Episode {seed} did not finish. "
                    "Position analysis currently requires completed episodes."
                )

            # Validate numeric fields now, rather than failing later.
            float(row["team_1_survival_time"])
            float(row["team_2_survival_time"])

            episodes[seed] = row

    if not episodes:
        raise ValueError(f"No episodes found in {path}.")

    return episodes


def validate_matched_episodes(nw_episodes, se_episodes):
    """Ensure both configurations contain identical scenarios."""

    nw_seeds = set(nw_episodes)
    se_seeds = set(se_episodes)

    if nw_seeds != se_seeds:

        missing_from_se = nw_seeds - se_seeds
        missing_from_nw = se_seeds - nw_seeds

        raise ValueError(
            "The two configurations do not contain identical episode seeds.\n"
            f"Missing from se-nw: {len(missing_from_se)}\n"
            f"Missing from nw-se: {len(missing_from_nw)}"
        )

    for seed in sorted(nw_seeds):

        nw = nw_episodes[seed]
        se = se_episodes[seed]

        # Both configurations must use the same experiment.
        if nw["experiment_seed"] != se["experiment_seed"]:
            raise ValueError(
                f"Experiment seed mismatch for episode {seed}."
            )

        # Same map and simulation randomness.
        for field in ("map_seed", "sim_seed"):

            if nw[field] != se[field]:
                raise ValueError(
                    f"{field} mismatch for episode {seed}: "
                    f"{nw[field]} vs {se[field]}."
                )

    return sorted(nw_seeds)


def get_winner_location(row, placement):
    """Convert the winning team ID into its starting location."""

    winner = row["winner_team_id"].strip()

    if not winner:
        return "DRAW" if row["outcome"] == "DRAW" else "UNKNOWN"

    winner = int(winner)

    location_by_team = {
        "nw-se": {
            1: "NORTHWEST",
            2: "SOUTHEAST",
        },
        "se-nw": {
            1: "SOUTHEAST",
            2: "NORTHWEST",
        },
    }

    if winner not in location_by_team[placement]:
        raise ValueError(
            f"Unexpected winning team ID {winner} "
            f"for placement {placement}."
        )

    return location_by_team[placement][winner]


def build_paired_rows(nw_episodes, se_episodes, matched_seeds):
    """Calculate position and team comparisons for each matched seed."""

    rows = []

    for seed in matched_seeds:

        nw_run = nw_episodes[seed]
        se_run = se_episodes[seed]

        # Configuration A: Team 1 NW, Team 2 SE.
        nw_a = float(nw_run["team_1_survival_time"])
        se_a = float(nw_run["team_2_survival_time"])

        # Configuration B: Team 1 SE, Team 2 NW.
        nw_b = float(se_run["team_2_survival_time"])
        se_b = float(se_run["team_1_survival_time"])

        # Average survival by starting position.
        northwest_average = statistics.fmean([nw_a, nw_b])
        southeast_average = statistics.fmean([se_a, se_b])

        # Positive means Southeast has an advantage.
        position_difference = (
            southeast_average - northwest_average
        )

        # Average survival by team identity.
        team1_average = statistics.fmean([
            float(nw_run["team_1_survival_time"]),
            float(se_run["team_1_survival_time"]),
        ])

        team2_average = statistics.fmean([
            float(nw_run["team_2_survival_time"]),
            float(se_run["team_2_survival_time"]),
        ])

        # Positive means Team 1 has an identity advantage.
        team_difference = team1_average - team2_average

        winner_nw_se = get_winner_location(nw_run, "nw-se")
        winner_se_nw = get_winner_location(se_run, "se-nw")

        winner_team_nw_se = (
            nw_run["winner_team_id"].strip() or "DRAW"
        )

        winner_team_se_nw = (
            se_run["winner_team_id"].strip() or "DRAW"
        )

        if (
            winner_team_nw_se == "DRAW"
            and winner_team_se_nw == "DRAW"
        ):
            pair_outcome_relation = "DRAW_BOTH"

        elif (
            winner_team_nw_se == "DRAW"
            or winner_team_se_nw == "DRAW"
        ):
            pair_outcome_relation = "ONE_DRAW_ONE_DECISIVE"

        elif winner_team_nw_se == winner_team_se_nw:
            pair_outcome_relation = "SAME_TEAM_WINS_BOTH"

        else:
            pair_outcome_relation = "DIFFERENT_TEAMS_WIN"

        rows.append({
            "episode_master_seed": seed,
            "map_seed": nw_run["map_seed"],
            "sim_seed": nw_run["sim_seed"],

            "nw_se_team1_nw_survival": nw_a,
            "nw_se_team2_se_survival": se_a,

            "se_nw_team2_nw_survival": nw_b,
            "se_nw_team1_se_survival": se_b,

            "northwest_average_survival": northwest_average,
            "southeast_average_survival": southeast_average,

            "southeast_minus_northwest": position_difference,

            "team1_average_survival": team1_average,
            "team2_average_survival": team2_average,

            "team1_minus_team2": team_difference,

            "nw_se_winner_location": winner_nw_se,
            "se_nw_winner_location": winner_se_nw,

            "nw_se_winner_team": winner_team_nw_se,
            "se_nw_winner_team": winner_team_se_nw,
            "pair_outcome_relation": pair_outcome_relation,

            "winner_location_changed": (
                winner_nw_se != winner_se_nw
            ),
        })

    return rows


def percentile(values, quantile):
    """Calculate a percentile using linear interpolation."""

    ordered = sorted(values)

    if not ordered:
        raise ValueError("Cannot calculate percentile of empty data.")

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
    """Estimate a 95% bootstrap confidence interval for the mean."""

    if len(values) < 2:
        return None, None

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


def calculate_position_summary(paired_rows, experiment_seed):
    """Calculate aggregate position and team identity statistics."""

    if not paired_rows:
        raise ValueError("No paired episodes available.")

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

    # Bootstrap confidence interval for the paired position effect.
    ci_low, ci_high = bootstrap_mean_confidence_interval(
        position_differences,
        seed=experiment_seed ^ 0x5A17,
    )

    # Count which position performed better in each matched scenario.
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

    # Count which starting location won across both configurations.
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

            winner_location = row[field]

            if winner_location in location_wins:
                location_wins[winner_location] += 1

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

    outcome_relations = [
        row["pair_outcome_relation"]
        for row in paired_rows
    ]

    outcome_counts = {
        category: outcome_relations.count(category)
        for category in [
            "SAME_TEAM_WINS_BOTH",
            "DIFFERENT_TEAMS_WIN",
            "DRAW_BOTH",
            "ONE_DRAW_ONE_DECISIVE",
        ]
    }

    return {
        "experiment_seed": experiment_seed,
        "matched_episode_pairs": len(paired_rows),

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

        "northwest_better_pairs": northwest_better,
        "southeast_better_pairs": southeast_better,
        "equal_survival_pairs": equal,

        "average_team1_survival": statistics.fmean(team1_values),
        "average_team2_survival": statistics.fmean(team2_values),

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
        raise ValueError(f"No rows to write to {path}.")

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


def print_position_summary(summary):
    """Display the paired position analysis."""

    print("\n" + "=" * 60)
    print("             STARTING POSITION ANALYSIS")
    print("=" * 60)

    print(f"Experiment seed: {summary['experiment_seed']}")

    print(
        f"Matched episode pairs: "
        f"{summary['matched_episode_pairs']}"
    )

    print("\nAVERAGE SURVIVAL BY STARTING POSITION")
    print("-" * 45)

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
    print("-" * 45)

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
    print("-" * 45)

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
    print("-" * 45)

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
    print("---------------------------------------------")

    for category, count in summary["paired_outcome_counts"].items():
        label = category.replace("_", " ").title()
        print(f"{label}: {count}")

    print("=" * 60)


def parse_args(argv=None):
    """Parse analysis command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Analyse paired starting-position experiments."
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=123,
        help="Experiment seed used in both placement configurations.",
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=50,
        help="Number of matched episodes per configuration.",
    )

    parser.add_argument(
        "--results-dir",
        default="results/baseline_v1/position_bias",
        help="Root directory containing nw-se and se-nw results.",
    )

    return parser.parse_args(argv)


def main(args=None):
    """Run the paired starting-position analysis."""

    if args is None:
        args = parse_args()

    if args.runs < 2:
        raise ValueError(
            "At least two matched episodes are required."
        )

    project_root = Path(__file__).resolve().parents[1]

    results_root = Path(args.results_dir)

    if not results_root.is_absolute():
        results_root = project_root / results_root

    experiment_folder = (
        f"seed_{args.seed}_runs_{args.runs}"
    )

    nw_path = (
        results_root
        / "nw-se"
        / experiment_folder
        / "episodes.csv"
    )

    se_path = (
        results_root
        / "se-nw"
        / experiment_folder
        / "episodes.csv"
    )

    print("Reading experiment results...")

    nw_episodes = read_episode_csv(
        nw_path,
        expected_placement="nw-se",
    )

    se_episodes = read_episode_csv(
        se_path,
        expected_placement="se-nw",
    )

    matched_seeds = validate_matched_episodes(
        nw_episodes,
        se_episodes,
    )

    if len(matched_seeds) != args.runs:
        raise ValueError(
            f"Expected {args.runs} matched episodes, "
            f"but found {len(matched_seeds)}."
        )

    print(
        f"Validated {len(matched_seeds)} matched episodes. "
        "Map and simulation seeds match."
    )

    paired_rows = build_paired_rows(
        nw_episodes,
        se_episodes,
        matched_seeds,
    )

    summary = calculate_position_summary(
        paired_rows,
        experiment_seed=args.seed,
    )

    print_position_summary(summary)

    # --------------------------------------------------
    # Save analysis results.
    # --------------------------------------------------

    output_path = (
        results_root
        / "paired_analysis"
        / experiment_folder
    )

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_csv(
        output_path / "paired_position_analysis.csv",
        paired_rows,
    )

    write_csv(
        output_path / "position_analysis_summary.csv",
        [summary],
    )

    metadata = {
        "experiment_seed": args.seed,
        "matched_episode_pairs": len(matched_seeds),
        "nw_se_source": str(nw_path),
        "se_nw_source": str(se_path),
        "confidence_interval": (
            "95% percentile bootstrap interval "
            "using 10000 resamples of paired differences."
        ),
    }

    with (
        output_path / "metadata.json"
    ).open("w", encoding="utf-8") as file:

        json.dump(
            metadata,
            file,
            indent=4,
        )

    print("\nAnalysis files saved to:")
    print(output_path.resolve())


if __name__ == "__main__":
    main()