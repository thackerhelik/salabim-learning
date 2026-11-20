from dataclasses import dataclass
from typing import Optional


@dataclass
class TeamState:
    """Tracks the state of a team."""

    team_id: int
    leader: object
    workers: list

    status: str = "ACTIVE"
    eliminated_at: Optional[float] = None
    elimination_reason: Optional[str] = None


class TeamManager:
    """Manages team elimination and episode state."""

    def __init__(
        self,
        env,
        team_leaders,
        explorers,
        controllers,
        event_logger=None,
        announce_episode_finished=True,
    ):

        if not team_leaders:
            raise ValueError("TeamManager requires at least one team.")
        
        self.env = env
        self.controllers = controllers
        self.event_logger = event_logger
        self.announce_episode_finished = announce_episode_finished

        self.teams = {}

        self.episode_finished = False
        self.episode_finished_at = None

        self.started_at = env.now()

        # Create a state object for each team.
        for team_id, leader in team_leaders.items():

            workers = [
                explorer
                for explorer in explorers
                if explorer.team_id == team_id
            ]

            self.teams[team_id] = TeamState(
                team_id=team_id,
                leader=leader,
                workers=workers,
            )

            # Every worker must have a corresponding controller.
            for worker in workers:

                if worker.name not in controllers:
                    raise ValueError(
                        f"Missing controller for {worker.name}."
                    )

    def eliminate_team(self, team_id):
        """Eliminate a team after its leader dies."""

        team = self.teams.get(team_id)

        if team is None:
            raise ValueError(f"Unknown team: {team_id}")

        # Avoid processing elimination more than once.
        if team.status == "ELIMINATED":
            return

        # Update team state first.
        team.status = "ELIMINATED"
        team.eliminated_at = self.env.now()
        team.elimination_reason = "leader_death"

        # Log team elimination.
        if self.event_logger is not None:

            self.event_logger.log(
                sim_time=self.env.now(),
                team_id=team_id,
                explorer_name=team.leader.name,
                event="TEAM_ELIMINATED",
                message=(
                    f"Team {team_id} eliminated because "
                    "its leader died."
                ),
                details=[
                    f"Elimination time: {self.env.now():.1f}",
                    f"Workers: {len(team.workers)}",
                ],
            )

        # Eliminate all remaining workers.
        for worker in team.workers:

            controller = self.controllers[worker.name]

            if worker.is_alive:

                # Mark the worker as dead.
                worker.is_alive = False

                # Reuse the existing death handler.
                # This cancels movement, releases claims,
                # and drops any carried resources.
                controller.handle_death(
                    cause="team_elimination"
                )

            elif not controller.death_handled:

                # Safety handling for a worker that died
                # but whose death handler has not run yet.
                controller.handle_death(
                    cause="previous_death"
                )

        # Check whether the entire episode has finished.
        if all(
            team.status == "ELIMINATED"
            for team in self.teams.values()
        ):

            self.episode_finished = True
            self.episode_finished_at = self.env.now()

            if self.announce_episode_finished:
                print(
                    f"\n[EPISODE FINISHED] "
                    f"All teams eliminated at T={self.env.now():.1f}"
                )

            # Return control to the main Python code.
            self.env.main().activate()


    def get_results(self):
        """Calculate the final episode results."""

        team_results = {}

        for team_id, team in self.teams.items():

            if team.eliminated_at is not None:
                survival_time = (
                    team.eliminated_at - self.started_at
                )
            else:
                survival_time = (
                    self.env.now() - self.started_at
                )

            team_results[team_id] = {
                "status": team.status,
                "eliminated_at": team.eliminated_at,
                "survival_time": survival_time,
            }

        outcome = "INCOMPLETE"

        if self.episode_finished:

            longest_survival = max(
                result["survival_time"]
                for result in team_results.values()
            )

            winners = [
                team_id
                for team_id, result in team_results.items()
                if abs(
                    result["survival_time"] - longest_survival
                ) < 1e-9
            ]

            if len(winners) > 1:
                outcome = "DRAW"
            else:
                outcome = f"TEAM {winners[0]} WINS"

        return {
            "episode_finished": self.episode_finished,
            "episode_duration": (
                self.episode_finished_at - self.started_at
                if self.episode_finished
                else self.env.now() - self.started_at
            ),
            "outcome": outcome,
            "teams": team_results,
        }


    def print_results(self):
        """Print a summary of the completed episode."""

        results = self.get_results()

        print("\n" + "=" * 45)
        print("           EPISODE RESULTS")
        print("=" * 45)

        print(
            f"Episode duration: "
            f"{results['episode_duration']:.1f}"
        )

        for team_id, team in results["teams"].items():

            eliminated_at = team["eliminated_at"]

            print(f"\nTeam {team_id}")
            print(f"  Status: {team['status']}")
            print(
                f"  Leader survival time: "
                f"{team['survival_time']:.1f}"
            )

            if eliminated_at is not None:
                print(
                    f"  Eliminated at: {eliminated_at:.1f}"
                )

        print("\nResult:", results["outcome"])
        print("=" * 45)