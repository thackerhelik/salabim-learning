
import argparse
import csv
import json

from itertools import permutations
from pathlib import Path

from island_survivors.main import (
    BASE_POSITIONS,
    run_episode,
)

from island_survivors.experiment_runner import (
    run_experiments,
    build_episode_row,
    build_economy_rows,
    write_csv,
    get_git_metadata,
)


TEAM_IDS = (1, 2, 3, 4)
NUMBER_OF_CONFIGURATIONS = 24


def generate_assignments():
    """
    Generate all 24 permutations of team assignments.

    Each assignment maps a starting position to a team ID.
    """

    assignments = []

    for index, team_order in enumerate(
        permutations(TEAM_IDS),
        start=1,
    ):

        team_assignment = dict(
            zip(BASE_POSITIONS, team_order)
        )

        configuration_label = "_".join(
            f"{position}{team_assignment[position]}"
            for position in BASE_POSITIONS
        )

        configuration_id = (
            f"config_{index:02d}_{configuration_label}"
        )

        assignments.append({
            "configuration_index": index,
            "configuration_id": configuration_id,
            "team_assignment": team_assignment,
        })

    if len(assignments) != NUMBER_OF_CONFIGURATIONS:
        raise RuntimeError(
            f"Expected 24 configurations, "
            f"generated {len(assignments)}."
        )

    # Ensure every team occupies every position exactly six times.
    for position in BASE_POSITIONS:

        counts = {
            team_id: 0
            for team_id in TEAM_IDS
        }

        for configuration in assignments:

            team_id = configuration["team_assignment"][position]
            counts[team_id] += 1

        if any(count != 6 for count in counts.values()):
            raise RuntimeError(
                f"Unbalanced assignments for position {position}: "
                f"{counts}"
            )

    return assignments


def scenario_signature(results):
    """
    Extract the seed information for each episode.

    This is used to verify matched scenarios across configurations.
    """

    return [
        (
            result["master_seed"],
            result["map_seed"],
            result["sim_seed"],
        )
        for result in results
    ]


def validate_configuration_results(
    results,
    expected_assignment,
    expected_runs,
    configuration_id,
):
    """Validate results returned by one rotation configuration."""

    if len(results) != expected_runs:
        raise ValueError(
            f"{configuration_id}: expected {expected_runs} "
            f"episodes, got {len(results)}."
        )

    expected_team_ids = set(TEAM_IDS)

    for run_index, result in enumerate(results, start=1):

        actual_team_ids = set(result["episode"]["teams"])

        if actual_team_ids != expected_team_ids:
            raise ValueError(
                f"{configuration_id}, run {run_index}: "
                "unexpected team IDs."
            )

        economy_team_ids = set(
            result["resource_economy"]["teams"]
        )

        if economy_team_ids != expected_team_ids:
            raise ValueError(
                f"{configuration_id}, run {run_index}: "
                "resource economy team IDs do not match."
            )

        # Validate resource accounting for every team.
        for team_id, team_metrics in result["resource_economy"]["teams"].items():

            for resource, balance in team_metrics["storage_balance"].items():

                if not balance["ok"]:
                    raise ValueError(
                        f"{configuration_id}, run {run_index}, "
                        f"Team {team_id}: storage balance mismatch "
                        f"for {resource}. "
                        f"Expected {balance['expected']}, "
                        f"actual {balance['actual']}."
                    )

        if result["placement"] != "four-corners":
            raise ValueError(
                f"{configuration_id}, run {run_index}: "
                "incorrect placement label."
            )

        actual_assignment = result.get("team_assignment")

        if actual_assignment != expected_assignment:
            raise ValueError(
                f"{configuration_id}, run {run_index}: "
                f"unexpected team assignment: {actual_assignment}"
            )

        if not result["episode"]["episode_finished"]:
            raise ValueError(
                f"{configuration_id}, run {run_index}: "
                "episode did not finish."
            )


def build_team_position_rows(
    result,
    run_index,
    experiment_seed,
    configuration,
):
    """Create one observation for every team's position in an episode."""

    assignment = configuration["team_assignment"]

    # Convert position -> team into team -> position.
    position_by_team = {
        team_id: position
        for position, team_id in assignment.items()
    }

    episode = result["episode"]
    economy = result["resource_economy"]

    winner_team_id = result["winner_team_id"]
    is_draw = episode["outcome"] == "DRAW"

    rows = []

    for team_id in TEAM_IDS:

        team = episode["teams"][team_id]
        team_economy = economy["teams"][team_id]

        rows.append({
            "configuration_index": (
                configuration["configuration_index"]
            ),
            "configuration_id": (
                configuration["configuration_id"]
            ),
            "experiment_seed": experiment_seed,
            "run_index": run_index,
            "episode_master_seed": result["master_seed"],
            "map_seed": result["map_seed"],
            "sim_seed": result["sim_seed"],

            "team_assignment": json.dumps(
                assignment,
                sort_keys=True,
            ),

            "team_id": team_id,
            "starting_position": position_by_team[team_id],

            "survival_time": team["survival_time"],
            "leader_final_health": team.get(
                "leader_final_health"
            ),
            "leader_final_hunger": team.get(
                "leader_final_hunger"
            ),

            "won": winner_team_id == team_id,
            "episode_draw": is_draw,
            "episode_outcome": episode["outcome"],

            "berries_gathered": (
                team_economy["gathered"]["berries"]
            ),
            "berries_looted": (
                team_economy["looted"]["berries"]
            ),
            "berries_deposited": (
                team_economy["deposited"]["berries"]
            ),
            "worker_berries_consumed": (
                team_economy["worker_berries_consumed"]
            ),
            "leader_berries_consumed": (
                team_economy["leader_berries_consumed"]
            ),
        })

    return rows


def parse_args(argv=None):
    """Parse rotation experiment configuration."""

    parser = argparse.ArgumentParser(
        description=(
            "Run matched four-team experiments across "
            "all 24 starting-position permutations."
        )
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=123,
        help="Master experiment seed.",
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=20,
        help="Number of matched scenarios per configuration.",
    )

    parser.add_argument(
        "--results-dir",
        default="results/baseline_v2/four_team_rotations",
        help="Root directory for rotation experiment results.",
    )

    args = parser.parse_args(argv)

    if args.runs < 1:
        parser.error("--runs must be at least 1.")

    return args


def main(args=None):
    """Execute all 24 matched four-team configurations."""

    if args is None:
        args = parse_args()

    configurations = generate_assignments()

    project_root = Path(__file__).resolve().parents[1]

    results_root = Path(args.results_dir)

    if not results_root.is_absolute():
        results_root = project_root / results_root

    print("=" * 65)
    print("             FOUR-TEAM ROTATION EXPERIMENT")
    print("=" * 65)

    print(f"Experiment seed: {args.seed}")
    print(f"Runs per configuration: {args.runs}")
    print(f"Number of configurations: {len(configurations)}")
    print(
        f"Total individual episodes: "
        f"{len(configurations) * args.runs}"
    )

    print("\nGenerating all 24 assignments...")
    print("Assignment balance validation passed.")

    combined_episode_rows = []
    combined_economy_rows = []
    team_position_rows = []
    configuration_summary_rows = []

    reference_signature = None
    reference_results = None

    # --------------------------------------------------
    # Execute every configuration.
    # --------------------------------------------------

    for configuration in configurations:

        configuration_index = configuration[
            "configuration_index"
        ]

        configuration_id = configuration[
            "configuration_id"
        ]

        assignment = configuration["team_assignment"]

        print("\n" + "-" * 65)
        print(
            f"[{configuration_index}/24] "
            f"{configuration_id}"
        )
        print(f"Assignment: {assignment}")

        configuration_output_dir = (
            results_root / configuration_id
        )

        batch = run_experiments(
            run_episode_fn=run_episode,
            experiment_seed=args.seed,
            runs=args.runs,
            log_level="quiet",
            output_dir=str(configuration_output_dir),
            placement="four-corners",
            teams=4,
            team_assignment=assignment,
            print_summary=False,
        )

        results = batch["results"]

        validate_configuration_results(
            results=results,
            expected_assignment=assignment,
            expected_runs=args.runs,
            configuration_id=configuration_id,
        )

        # --------------------------------------------------
        # Check matched scenario seeds.
        # --------------------------------------------------

        current_signature = scenario_signature(results)

        if reference_signature is None:

            reference_signature = current_signature
            reference_results = results

        elif current_signature != reference_signature:

            raise ValueError(
                f"Scenario seed mismatch in {configuration_id}. "
                "Matched configurations must use identical "
                "episode, map and simulation seeds."
            )

        # --------------------------------------------------
        # Collect per-episode data.
        # --------------------------------------------------

        for run_index, result in enumerate(
            results,
            start=1,
        ):

            episode_seed = result["master_seed"]

            episode_row = build_episode_row(
                run_index=run_index,
                experiment_seed=args.seed,
                episode_seed=episode_seed,
                result=result,
            )

            episode_row["configuration_index"] = (
                configuration_index
            )

            episode_row["configuration_id"] = (
                configuration_id
            )

            combined_episode_rows.append(episode_row)

            economy_rows = build_economy_rows(
                run_index=run_index,
                experiment_seed=args.seed,
                episode_seed=episode_seed,
                result=result,
            )

            for economy_row in economy_rows:

                economy_row["configuration_index"] = (
                    configuration_index
                )

                economy_row["configuration_id"] = (
                    configuration_id
                )

                economy_row["team_assignment"] = json.dumps(
                    assignment,
                    sort_keys=True,
                )

                combined_economy_rows.append(economy_row)

            team_position_rows.extend(
                build_team_position_rows(
                    result=result,
                    run_index=run_index,
                    experiment_seed=args.seed,
                    configuration=configuration,
                )
            )

        # --------------------------------------------------
        # Collect configuration-level summary.
        # --------------------------------------------------

        summary_row = dict(batch["summary"])

        summary_row["configuration_index"] = (
            configuration_index
        )

        summary_row["configuration_id"] = (
            configuration_id
        )

        summary_row["team_assignment"] = json.dumps(
            assignment,
            sort_keys=True,
        )

        configuration_summary_rows.append(summary_row)

        print(
            f"Validated {len(results)} episodes. "
            "Matched seeds confirmed."
        )

    # --------------------------------------------------
    # Validate the complete experiment.
    # --------------------------------------------------

    expected_episodes = (
        NUMBER_OF_CONFIGURATIONS * args.runs
    )

    expected_team_observations = expected_episodes * 4

    if len(combined_episode_rows) != expected_episodes:
        raise RuntimeError(
            "Unexpected number of combined episode rows."
        )

    if len(combined_economy_rows) != expected_team_observations:
        raise RuntimeError(
            "Unexpected number of combined economy rows."
        )

    if len(team_position_rows) != expected_team_observations:
        raise RuntimeError(
            "Unexpected number of team-position observations."
        )

    # --------------------------------------------------
    # Save consolidated outputs.
    # --------------------------------------------------

    output_path = (
        results_root
        / f"combined_seed_{args.seed}_runs_{args.runs}"
    )

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_csv(
        output_path / "combined_episodes.csv",
        combined_episode_rows,
    )

    write_csv(
        output_path / "combined_resource_economy.csv",
        combined_economy_rows,
    )

    write_csv(
        output_path / "team_position_observations.csv",
        team_position_rows,
    )

    write_csv(
        output_path / "configuration_summaries.csv",
        configuration_summary_rows,
    )

    # Save the common scenarios used in every configuration.
    scenario_rows = []

    for run_index, result in enumerate(
        reference_results,
        start=1,
    ):

        scenario_rows.append({
            "run_index": run_index,
            "experiment_seed": args.seed,
            "episode_master_seed": result["master_seed"],
            "map_seed": result["map_seed"],
            "sim_seed": result["sim_seed"],
        })

    write_csv(
        output_path / "matched_scenarios.csv",
        scenario_rows,
    )

    # --------------------------------------------------
    # Save experiment metadata.
    # --------------------------------------------------

    metadata = {
        "experiment_seed": args.seed,
        "number_of_teams": 4,
        "number_of_configurations": len(configurations),
        "runs_per_configuration": args.runs,
        "total_episodes": expected_episodes,
        "total_team_position_observations": (
            expected_team_observations
        ),

        "positions": list(BASE_POSITIONS),
        "team_ids": list(TEAM_IDS),

        "assignment_generation": (
            "All 24 lexicographic permutations of "
            "team IDs across NW, NE, SE and SW."
        ),

        "assignments": configurations,

        "matched_scenario_validation": {
            "episode_master_seeds_match": True,
            "map_seeds_match": True,
            "simulation_seeds_match": True,
        },

        "episode_master_seeds": [
            result["master_seed"]
            for result in reference_results
        ],

        "seed_derivation": (
            "Each episode master seed is derived from "
            "random.Random(experiment_seed)."
        ),

        "randomness_note": (
            "Map and simulation seeds are identical across matched "
            "configurations. Subsequent stochastic event sequences "
            "may diverge because different assignments can change "
            "agent behaviour and event scheduling."
        ),

        "git": get_git_metadata(),
    }

    with (
        output_path / "metadata.json"
    ).open("w", encoding="utf-8") as file:

        json.dump(
            metadata,
            file,
            indent=4,
        )

    # --------------------------------------------------
    # Final report.
    # --------------------------------------------------

    print("\n" + "=" * 65)
    print("             ROTATION EXPERIMENT COMPLETED")
    print("=" * 65)

    print(f"Configurations completed: {len(configurations)}")
    print(f"Matched scenarios: {args.runs}")
    print(f"Total episodes: {expected_episodes}")
    print(
        f"Team-position observations: "
        f"{expected_team_observations}"
    )

    print("Episode master seeds: MATCHED")
    print("Map seeds: MATCHED")
    print("Simulation seeds: MATCHED")
    print("Team assignments: VALIDATED")

    print("\nConsolidated files saved to:")
    print(output_path.resolve())

    return {
        "experiment_seed": args.seed,
        "runs": args.runs,
        "configurations": len(configurations),
        "output_directory": str(output_path),
    }


if __name__ == "__main__":
    main()
