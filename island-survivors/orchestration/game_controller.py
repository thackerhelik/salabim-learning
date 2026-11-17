
import salabim as sim

from environment import (
    gather_resource,
    eat_berries,
    get_observation,
)


def execute_action(explorer, resources, action):
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
        decision_interval=1,
    ):
        self.explorer = explorer
        self.agent = agent
        self.resources = resources
        self.movement = movement

        self.decision_interval = decision_interval

    def process(self):

        while self.explorer.is_alive:

            # 1. Observe the current situation.
            observation = get_observation(
                self.explorer,
                self.resources,
            )

            # 2. Ask the agent to decide.
            action = self.agent.decide(observation)

            action_type = action.get("action")

            # 3. Execute the selected action.
            if action_type == "explore":

                moved = self.movement.move_one_step(self)

                if moved:
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
                    action,
                )

            # 4. Log the decision and outcome.
            print(
                f"{self.explorer.name} | "
                f"{action_type} | "
                f"{result['message']}"
            )

            # 5. Wait before the next decision.
            self.hold(self.decision_interval)
