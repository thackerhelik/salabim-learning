import salabim as sim

from environment import (
    update_survival_needs,
    HUNGER_REDUCTION_PER_BERRY,
    HUNGER_INCREASE_PER_UPDATE,
    MAX_HUNGER,
    STARVATION_DAMAGE,
)


LEADER_EAT_THRESHOLD = 60


def update_leader_survival_needs(leader, team_storage):
    """Update leader hunger and health using shared team storage."""

    if not leader.is_alive:
        return None

    # Increase hunger, following the existing worker survival rules.
    leader.hunger = min(
        MAX_HUNGER,
        leader.hunger + HUNGER_INCREASE_PER_UPDATE,
    )

    berries_consumed = 0

    # Automatically consume berries when hunger reaches the threshold.
    if leader.hunger >= LEADER_EAT_THRESHOLD:

        needed = (
            leader.hunger + HUNGER_REDUCTION_PER_BERRY - 1
        ) // HUNGER_REDUCTION_PER_BERRY

        berries_consumed = team_storage.withdraw(
            "berries",
            needed,
        )

        hunger_reduction = (
            berries_consumed * HUNGER_REDUCTION_PER_BERRY
        )

        leader.hunger = max(
            0,
            leader.hunger - hunger_reduction,
        )

    # Apply starvation damage if the leader remains completely hungry.
    health_lost = 0

    if leader.hunger >= MAX_HUNGER:

        previous_health = leader.health

        leader.health = max(
            0,
            leader.health - STARVATION_DAMAGE,
        )

        health_lost = previous_health - leader.health

        if leader.health == 0:
            leader.is_alive = False

    return {
        "hunger": leader.hunger,
        "health": leader.health,
        "berries_consumed": berries_consumed,
        "health_lost": health_lost,
        "is_alive": leader.is_alive,
    }


class ExplorerNeeds(sim.Component):
    """Manages the survival needs of an explorer."""

    def setup(
        self,
        explorer,
        update_interval=5,
        event_logger=None,
        death_handler=None,
    ):
        self.explorer = explorer
        self.update_interval = update_interval
        self.event_logger = event_logger
        self.death_handler = death_handler

    def process(self):

        while self.explorer.is_alive:

            # Wait until the next survival update.
            self.hold(self.update_interval)

            if not self.explorer.is_alive:
                break

            previous_hunger = self.explorer.hunger
            previous_health = self.explorer.health

            # Apply the survival rules.
            update_survival_needs(self.explorer)

            current_hunger = self.explorer.hunger
            current_health = self.explorer.health

            details = []

            if previous_hunger != current_hunger:
                details.append(
                    f"Hunger: {previous_hunger} -> {current_hunger}"
                )

            if previous_health != current_health:
                details.append(
                    f"Health: {previous_health} -> {current_health}"
                )

            if not self.explorer.is_alive:
                details.append("Status: DEAD")

            elif current_hunger >= 100:
                details.append("Status: STARVING")

            if self.event_logger is not None and details:

                self.event_logger.log(
                    sim_time=self.env.now(),
                    team_id=self.explorer.team_id,
                    explorer_name=self.explorer.name,
                    event="SURVIVAL_UPDATE",
                    message="Survival needs updated.",
                    details=details,
                )

            # Handle death immediately after the lethal update.
            if not self.explorer.is_alive:

                if self.death_handler is not None:
                    self.death_handler()

                break


class LeaderNeeds(sim.Component):
    """Manages the survival needs of a stationary team leader."""

    def setup(
        self,
        leader,
        team_storage,
        update_interval=5,
        event_logger=None,
    ):
        self.leader = leader
        self.team_storage = team_storage
        self.update_interval = update_interval
        self.event_logger = event_logger

    def process(self):

        while self.leader.is_alive:

            self.hold(self.update_interval)

            if not self.leader.is_alive:
                break

            previous_hunger = self.leader.hunger
            previous_health = self.leader.health

            result = update_leader_survival_needs(
                self.leader,
                self.team_storage,
            )

            details = [
                f"Hunger: {previous_hunger} -> {result['hunger']}",
                f"Health: {previous_health} -> {result['health']}",
                f"Berries consumed: {result['berries_consumed']}",
                (
                    "Storage berries remaining: "
                    f"{self.team_storage.inventory['berries']}"
                ),
            ]

            if result["health_lost"] > 0:
                details.append(
                    f"Starvation damage: {result['health_lost']}"
                )

            if result["hunger"] >= MAX_HUNGER:
                details.append("Status: STARVING")

            if not result["is_alive"]:
                details.append("Status: DEAD")

            if self.event_logger is not None:

                event = (
                    "LEADER_DEATH"
                    if not result["is_alive"]
                    else (
                        "LEADER_FED"
                        if result["berries_consumed"] > 0
                        else "LEADER_UPDATE"
                    )
                )

                self.event_logger.log(
                    sim_time=self.env.now(),
                    team_id=self.leader.team_id,
                    explorer_name=self.leader.name,
                    event=event,
                    message="Leader survival updated.",
                    details=details,
                )

            if not self.leader.is_alive:
                break