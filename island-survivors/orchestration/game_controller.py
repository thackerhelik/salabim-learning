
import salabim as sim

from environment import (
    gather_resource,
    eat_berries,
    loot_from_cache,
    get_observation,
    deposit_to_storage,
    withdraw_from_storage,
)

from entities.loot_cache import LootCache

from orchestration.event_logger import EventLogger


def execute_action(
        explorer,
        resources,
        loot_caches,
        action,
        team_storage=None,
    ):
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

    elif action_type == "deposit":

        if team_storage is None:
            return {
                "success": False,
                "message": "Team storage is unavailable.",
            }

        return deposit_to_storage(
            explorer=explorer,
            storage=team_storage,
            resource_type=action["resource_type"],
            amount=action.get("amount", 1),
        )

    elif action_type == "withdraw":

        if team_storage is None:
            return {
                "success": False,
                "message": "Team storage is unavailable.",
            }

        return withdraw_from_storage(
            explorer=explorer,
            storage=team_storage,
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
        team_knowledge,
        team_task_board,
        team_storage=None,
        decision_interval=1,
        event_logger=None,
    ):
        self.explorer = explorer
        self.agent = agent
        self.resources = resources
        self.movement = movement
        self.loot_caches = loot_caches
        self.occupied_positions = occupied_positions
        self.team_knowledge = team_knowledge
        self.team_task_board = team_task_board
        self.claimed_resource_position = None
        self.team_storage = team_storage
        self.decision_interval = decision_interval
        self.death_handled = False
        self.event_logger = (
            event_logger
            if event_logger is not None
            else EventLogger()
        )

    def process(self):

        while self.explorer.is_alive:

            # 1. Observe the current situation.
            observation = get_observation(
                self.explorer,
                self.resources,
                self.loot_caches,
            )

            # 2. Include active resource reservations.
            observation["resource_claims"] = (
                self.team_task_board.get_resource_claims(
                    self.env.now()
                )
            )

            # 3. Include team storage.
            if self.team_storage is not None:
                observation["team_storage"] = {
                    "position": (
                        self.team_storage.row,
                        self.team_storage.col,
                    ),
                    "inventory": self.team_storage.inventory.copy(),
                }

            # 4. Publish locally observed resources to team knowledge.
            for resource in observation["nearby_resources"]:

                position = tuple(resource["position"])
                quantity = resource["quantity"]

                previous_record = (
                    self.team_knowledge.known_resources.get(position)
                )

                previous_quantity = (
                    previous_record["quantity"]
                    if previous_record is not None
                    else None
                )

                self.team_knowledge.update_resource(
                    resource=resource,
                    discovered_by=self.explorer.name,
                    observed_at=self.env.now(),
                )

                # Log new discoveries and changes in resource quantity.
                if previous_record is None and quantity > 0:

                    self.event_logger.log(
                        sim_time=self.env.now(),
                        team_id=self.explorer.team_id,
                        explorer_name=self.explorer.name,
                        event="DISCOVERY",
                        message=(
                            f"Discovered {resource['kind']} "
                            f"at {position}."
                        ),
                        details=[
                            f"Resource: {resource['resource_type']}",
                            f"Quantity: {quantity}",
                        ],
                    )

                elif (
                    previous_quantity is not None
                    and previous_quantity > 0
                    and quantity == 0
                ):

                    self.event_logger.log(
                        sim_time=self.env.now(),
                        team_id=self.explorer.team_id,
                        explorer_name=self.explorer.name,
                        event="RESOURCE_DEPLETED",
                        message=f"Resource at {position} is depleted.",
                        details=[
                            f"Resource: {resource['resource_type']}"
                        ],
                    )

                elif (
                    previous_quantity is not None
                    and previous_quantity != quantity
                ):

                    self.event_logger.log(
                        sim_time=self.env.now(),
                        team_id=self.explorer.team_id,
                        explorer_name=self.explorer.name,
                        event="RESOURCE_UPDATE",
                        message=f"Resource quantity changed at {position}.",
                        details=[
                            f"Previous quantity: {previous_quantity}",
                            f"Current quantity: {quantity}",
                        ],
                    )

            # 5. Attach shared team knowledge to the observation.
            observation["team_resources"] = (
                self.team_knowledge.get_resources()
            )

            # 6. Ask the agent to decide.
            action = self.agent.decide(observation)

            action_type = action.get("action")
            reason = action.get("reason", "No reason provided.")

            # Record every decision, but only print it in debug mode.
            decision_details = [
                f"Reason: {reason}",
            ]

            if action.get("target_position") is not None:
                decision_details.append(
                    f"Target: {action['target_position']}"
                )

            self.event_logger.log(
                sim_time=self.env.now(),
                team_id=self.explorer.team_id,
                explorer_name=self.explorer.name,
                event="DECISION",
                message=f"Selected action: {action_type}",
                details=decision_details,
                debug_only=True,
            )

            # Track how much simulation time the action consumes.
            action_duration = 0

            # Capture state before executing an interaction.
            action_state_before = None

            # Remember position before possible movement.
            position_before = (
                self.explorer.row,
                self.explorer.col,
            )

            # 7. Prepare the resource reservation.
            claim_available = self.prepare_resource_claim(action)

            if not claim_available:

                result = {
                    "success": False,
                    "message": (
                        "Resource is already claimed by another explorer."
                    ),
                }

                moved = None

            else:

                # 8. Execute the selected action.
                if action_type == "explore":

                    moved = self.movement.move_towards_unvisited(
                        self,
                        self.agent.visited_positions,
                    )

                elif action_type == "navigate":

                    moved = self.movement.move_towards(
                        self,
                        action["target_position"],
                    )

                else:

                    # Capture state before an inventory interaction.
                    if action_type in {
                        "gather",
                        "eat",
                        "loot",
                        "deposit",
                        "withdraw",
                    }:
                        action_state_before = (
                            self.capture_action_state(action)
                        )

                    result = execute_action(
                        self.explorer,
                        self.resources,
                        self.loot_caches,
                        action,
                        team_storage=self.team_storage,
                    )

                    moved = None

                # 9. Handle movement results.
                if moved is not None:

                    if moved:

                        action_duration = (
                            self.movement.move_duration
                            + self.movement.pause_duration
                        )

                        new_position = (
                            self.explorer.row,
                            self.explorer.col,
                        )

                        result = {
                            "success": True,
                            "message": f"Moved to {new_position}.",
                        }

                        # Movement is useful for debugging but can be noisy.
                        if new_position != position_before:

                            self.event_logger.log(
                                sim_time=self.env.now(),
                                team_id=self.explorer.team_id,
                                explorer_name=self.explorer.name,
                                event="MOVE",
                                message=(
                                    f"Moved from {position_before} "
                                    f"to {new_position}."
                                ),
                                details=[
                                    f"Action: {action_type}",
                                    f"Reason: {reason}",
                                ],
                                debug_only=True,
                            )

                    else:

                        result = {
                            "success": False,
                            "message": "No valid movement path available.",
                        }

                        self.event_logger.log(
                            sim_time=self.env.now(),
                            team_id=self.explorer.team_id,
                            explorer_name=self.explorer.name,
                            event="MOVEMENT_BLOCKED",
                            message="Could not find a valid movement path.",
                            details=[
                                f"Action: {action_type}",
                                f"Reason: {reason}",
                            ],
                            debug_only=True,
                        )

            # 10. Log the outcome of inventory interactions.
            if action_state_before is not None:
                self.log_action_result(
                    action,
                    result,
                    action_state_before,
                )

            # Release a reservation if gathering fails.
            if action_type == "gather" and not result["success"]:
                self.release_resource_claim()

            # 11. Wait only for the remaining decision interval.
            remaining_time = max(
                0,
                self.decision_interval - action_duration,
            )

            if remaining_time > 0:
                self.hold(remaining_time)

        # The explorer is no longer alive.
        self.handle_death()


    def capture_action_state(self, action):
        """Capture relevant state before an inventory interaction."""

        action_type = action.get("action")

        target_position = action.get("target_position")

        if target_position is not None:
            target_position = tuple(target_position)

        resource = (
            self.resources.get(target_position)
            if target_position is not None
            else None
        )

        resource_type = action.get("resource_type")

        if action_type == "gather" and resource is not None:
            resource_type = resource.resource_type

        cache = (
            self.loot_caches.get(target_position)
            if target_position is not None
            else None
        )

        return {
            "target_position": target_position,
            "resource_type": resource_type,
            "inventory": self.explorer.inventory.copy(),
            "hunger": self.explorer.hunger,
            "health": self.explorer.health,
            "resource_quantity": (
                resource.quantity if resource is not None else None
            ),
            "cache_quantity": (
                cache.inventory.get(resource_type, 0)
                if cache is not None and resource_type is not None
                else None
            ),
            "storage_quantity": (
                self.team_storage.inventory.get(resource_type, 0)
                if self.team_storage is not None
                and resource_type is not None
                else None
            ),
        }


    def log_action_result(self, action, result, before):
        """Log an action together with the resulting state changes."""

        action_type = action.get("action")
        resource_type = before["resource_type"]
        position = before["target_position"]

        success = result.get("success", False)

        event_type = (
            action_type.upper()
            if success
            else "ACTION_FAILED"
        )

        message = result.get(
            "message",
            "Action completed.",
        )

        details = []

        if not success:
            details.append(f"Attempted action: {action_type}")

        if position is not None:
            details.append(f"Target position: {position}")

        if resource_type is not None:
            details.append(f"Resource type: {resource_type}")

        # Inventory changes.
        for resource, old_quantity in before["inventory"].items():

            new_quantity = self.explorer.inventory.get(resource, 0)

            if old_quantity != new_quantity:
                details.append(
                    f"Inventory - {resource}: "
                    f"{old_quantity} -> {new_quantity}"
                )

        # Resource depletion after gathering.
        if action_type == "gather" and position is not None:

            resource = self.resources.get(position)

            new_quantity = (
                resource.quantity
                if resource is not None
                else 0
            )

            if before["resource_quantity"] is not None:
                details.append(
                    f"Resource remaining: "
                    f"{before['resource_quantity']} -> {new_quantity}"
                )

        # Loot cache changes.
        if action_type == "loot" and position is not None:

            cache = self.loot_caches.get(position)

            new_quantity = (
                cache.inventory.get(resource_type, 0)
                if cache is not None
                else 0
            )

            if before["cache_quantity"] is not None:
                details.append(
                    f"Cache {resource_type}: "
                    f"{before['cache_quantity']} -> {new_quantity}"
                )

        # Team storage changes.
        if (
            action_type in {"deposit", "withdraw"}
            and self.team_storage is not None
        ):

            new_quantity = self.team_storage.inventory.get(
                resource_type, 0
            )

            details.append(
                f"Team storage - {resource_type}: "
                f"{before['storage_quantity']} -> {new_quantity}"
            )

        # Survival changes.
        if before["hunger"] != self.explorer.hunger:
            details.append(
                f"Hunger: {before['hunger']} -> {self.explorer.hunger}"
            )

        if before["health"] != self.explorer.health:
            details.append(
                f"Health: {before['health']} -> {self.explorer.health}"
            )

        self.event_logger.log(
            sim_time=self.env.now(),
            team_id=self.explorer.team_id,
            explorer_name=self.explorer.name,
            event=event_type,
            message=message,
            details=details,
        )
        

    def release_resource_claim(self):
        """Release the explorer's current resource reservation."""

        if self.claimed_resource_position is None:
            return

        position = self.claimed_resource_position

        self.team_task_board.release_resource(
            position,
            self.explorer.name,
        )

        self.claimed_resource_position = None

        self.event_logger.log(
            sim_time=self.env.now(),
            team_id=self.explorer.team_id,
            explorer_name=self.explorer.name,
            event="CLAIM_RELEASED",
            message=f"Released resource claim at {position}.",
        )


    def prepare_resource_claim(self, action):
        """Reserve a resource when the explorer decides to pursue it."""

        action_type = action.get("action")
        target_position = None

        if action_type == "gather":

            target_position = action["target_position"]

        elif (
            action_type == "navigate"
            and action.get("target_type") == "resource"
        ):

            target_position = action["target_position"]

        # Other actions don't require a resource reservation.
        if target_position is None:

            self.release_resource_claim()

            return True

        target_position = tuple(target_position)

        already_claimed = (
            self.claimed_resource_position == target_position
        )

        # Release an older claim if pursuing a different resource.
        if (
            self.claimed_resource_position is not None
            and not already_claimed
        ):
            self.release_resource_claim()

        # Try to claim or renew the resource.
        success = self.team_task_board.claim_resource(
            position=target_position,
            explorer_name=self.explorer.name,
            current_time=self.env.now(),
            lease_duration=5,
        )

        if success:

            self.claimed_resource_position = target_position

            # Don't log repeated renewals.
            if not already_claimed:

                self.event_logger.log(
                    sim_time=self.env.now(),
                    team_id=self.explorer.team_id,
                    explorer_name=self.explorer.name,
                    event="CLAIM",
                    message=f"Claimed resource at {target_position}.",
                )

        else:

            self.claimed_resource_position = None

            self.event_logger.log(
                sim_time=self.env.now(),
                team_id=self.explorer.team_id,
                explorer_name=self.explorer.name,
                event="CLAIM_DENIED",
                message=(
                    f"Could not claim resource at {target_position}. "
                    "Another explorer owns the reservation."
                ),
            )

        return success


    def handle_death(self):
        """Handle the consequences of an explorer's death."""

        if self.death_handled:
            return

        # Record the explorer's last position.
        position = (
            self.explorer.row,
            self.explorer.col,
        )

        # Release claims
        self.team_task_board.release_all(self.explorer.name)
        self.claimed_resource_position = None

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
            self.event_logger.log(
                sim_time=self.env.now(),
                team_id=self.explorer.team_id,
                explorer_name=self.explorer.name,
                event="DEATH",
                message=f"Explorer died at {position}.",
                details=[
                    f"Loot cache created: {inventory}",
                ],
            )
        else:
            self.event_logger.log(
                sim_time=self.env.now(),
                team_id=self.explorer.team_id,
                explorer_name=self.explorer.name,
                event="DEATH",
                message=f"Explorer died at {position}.",
                details=[
                    "No resources were dropped.",
                ],
            )