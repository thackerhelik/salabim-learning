import salabim as sim

from environment import update_survival_needs


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