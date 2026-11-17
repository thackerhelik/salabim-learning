
import salabim as sim

from environment import (
    gather_resource,
    eat_berries,
    loot_from_cache,
    get_observation,
)

from entities.loot_cache import LootCache



def execute_action(explorer, resources, loot_caches, action):
    """Execute an action selected by an agent."""

    action_type = action.get("action")

    if action_type == "gather":

        return gather_resource(
            explorer=explorer,
            resources=resources,
            target_position=action["target_position"],
            amount=action.get("amount", 2),
        )

    elif action_type == "eat":

        return eat_berries(
            explorer=explorer,
            amount=action.get("amount", 1),
        )

    elif action_type == "loot":

        return loot_from_cache(
            explorer=explorer,
            loot_caches=loot_caches,
            target_position=action["target_position"],
            resource_type=action["resource_type"],
            amount=action.get("amount", 1),
        )

    elif action_type == "none":

        return {
            "success": True,
            "message": "No action required.",
        }

    return {
        "success": False,
        "message": f"Unknown action: {action_type}",
    }



class ExplorerController(sim.Component):
    """Coordinates the decisions and actions of an explorer."""

    def setup(
        self,
        explorer,
        agent,
        resources,
        movement,
        loot_caches,
        occupied_positions,
        decision_interval=1,
    ):
        self.explorer = explorer
        self.agent = agent
        self.resources = resources
        self.movement = movement
        self.loot_caches = loot_caches
        self.occupied_positions = occupied_positions
        self.decision_interval = decision_interval
        self.death_handled = False

    def process(self):

        while self.explorer.is_alive:

            # 1. Observe the current situation.
            observation = get_observation(
                self.explorer,
                self.resources,
                self.loot_caches,
            )

            # 2. Ask the agent to decide.
            action = self.agent.decide(observation)

            action_type = action.get("action")

            # Track how much simulation time the action consumes.
            action_duration = 0

            # 3. Execute the selected action.
            if action_type == "explore":

                moved = self.movement.move_one_step(self)

                if moved:
                    action_duration = (
                        self.movement.move_duration
                        + self.movement.pause_duration
                    )

                    result = {
                        "success": True,
                        "message": (
                            f"Moved to "
                            f"({self.explorer.row}, "
                            f"{self.explorer.col})."
                        ),
                    }
                else:
                    result = {
                        "success": False,
                        "message": "No valid neighbouring tile.",
                    }

            else:

                result = execute_action(
                    self.explorer,
                    self.resources,
                    self.loot_caches,
                    action,
                )

            # 4. Log the decision and outcome.
            print(
                f"{self.explorer.name} | "
                f"{action_type} | "
                f"{result['message']}"
            )

            # 5. Wait only for the remaining decision interval.
            remaining_time = max(
                0,
                self.decision_interval - action_duration,
            )

            if remaining_time > 0:
                self.hold(remaining_time)

        # The explorer is no longer alive.
        self.handle_death()


    def handle_death(self):
        """Handle the consequences of an explorer's death."""

        if self.death_handled:
            return

        # Record the explorer's last position.
        position = (
            self.explorer.row,
            self.explorer.col,
        )

        # Release the occupied tile.
        self.occupied_positions.discard(position)

        # Copy non-empty inventory items.
        inventory = {
            resource: quantity
            for resource, quantity in self.explorer.inventory.items()
            if quantity > 0
        }

        # Create a loot cache if the explorer carried resources.
        if inventory:

            # Check whether a cache already exists at this position.
            existing_cache = self.loot_caches.get(position)

            if existing_cache is None:

                self.loot_caches[position] = LootCache(
                    row=position[0],
                    col=position[1],
                    inventory=inventory,
                )

            else:

                # Merge inventory into an existing cache.
                for resource, quantity in inventory.items():

                    existing_cache.inventory[resource] = (
                        existing_cache.inventory.get(resource, 0)
                        + quantity
                    )

        # Clear the explorer's inventory after transferring it.
        for resource in self.explorer.inventory:
            self.explorer.inventory[resource] = 0

        self.death_handled = True

        if inventory:
            print(
                f"{self.explorer.name} died at {position}. "
                f"Loot cache created: {inventory}"
            )
        else:
            print(
                f"{self.explorer.name} died at {position}. "
                "No resources dropped."
            )
