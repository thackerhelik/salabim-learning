import salabim as sim

from environment import update_survival_needs


class ExplorerNeeds(sim.Component):
    """Manages the survival needs of an explorer."""

    def setup(
        self,
        explorer,
        update_interval=5,
    ):
        self.explorer = explorer
        self.update_interval = update_interval

    def process(self):

        while self.explorer.is_alive:

            # Wait until the next survival update.
            self.hold(self.update_interval)

            if not self.explorer.is_alive:
                break

            # Update hunger and health.
            result = update_survival_needs(self.explorer)

            # Temporary console output for debugging.
            print(
                f"{self.explorer.name}: "
                f"Hunger={result['hunger']}, "
                f"Health={result['health']}"
            )