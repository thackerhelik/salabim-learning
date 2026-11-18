class RuleBasedAgent:
    """Makes decisions using predefined survival priorities."""

    def __init__(self, hunger_threshold=60):
        self.hunger_threshold = hunger_threshold

        # Personally discovered resources.
        self.known_resources = {}

        # Resources discovered by team members.
        self.shared_resources = {}

        # Personally visited tiles.
        self.visited_positions = set()

    
    
    def decide(self, observation):
        """Choose an action and explain the reason behind it."""

        if not observation["is_alive"]:
            return {
                "action": "none",
                "reason": "Explorer is no longer alive.",
            }

        # Update individual and shared memory.
        self.update_memory(observation)

        hunger = observation["hunger"]
        inventory = observation["inventory"]
        current_position = observation["position"]

        storage = observation.get("team_storage")

        # --------------------------------------------------
        # PRIORITY 1: Eat when hungry and carrying berries.
        # --------------------------------------------------

        if hunger >= self.hunger_threshold:

            if inventory.get("berries", 0) > 0:
                return {
                    "action": "eat",
                    "amount": 1,
                    "reason": (
                        f"Hunger is {hunger}, above the threshold "
                        f"of {self.hunger_threshold}. "
                        "Eating available berries."
                    ),
                }

            # --------------------------------------------------
            # PRIORITY 2: Gather nearby berries.
            # --------------------------------------------------

            for resource in observation["nearby_resources"]:

                if (
                    resource["resource_type"] == "berries"
                    and resource["quantity"] > 0
                    and not self.is_resource_claimed_by_other(
                        resource["position"],
                        observation,
                    )
                ):
                    return {
                        "action": "gather",
                        "target_position": resource["position"],
                        "amount": 2,
                        "reason": (
                            "Hungry and an unclaimed berry resource "
                            "is within gathering distance."
                        ),
                    }

            # --------------------------------------------------
            # PRIORITY 3: Loot nearby berries.
            # --------------------------------------------------

            for cache in observation.get("nearby_loot_caches", []):

                if cache["inventory"].get("berries", 0) > 0:
                    return {
                        "action": "loot",
                        "target_position": cache["position"],
                        "resource_type": "berries",
                        "amount": 2,
                        "reason": (
                            "Hungry and a nearby loot cache "
                            "contains berries."
                        ),
                    }

            # --------------------------------------------------
            # PRIORITY 4: Withdraw food from team storage.
            # --------------------------------------------------

            if storage is not None:

                storage_position = tuple(storage["position"])

                storage_berries = storage["inventory"].get(
                    "berries", 0
                )

                distance = (
                    abs(current_position[0] - storage_position[0])
                    + abs(current_position[1] - storage_position[1])
                )

                if storage_berries > 0:

                    if distance <= 1:
                        return {
                            "action": "withdraw",
                            "resource_type": "berries",
                            "amount": 2,
                            "reason": (
                                "Hungry and berries are available "
                                "in team storage."
                            ),
                        }

                    return {
                        "action": "navigate",
                        "target_position": storage_position,
                        "target_type": "storage",
                        "reason": (
                            "Hungry and team storage contains berries. "
                            "Moving towards storage."
                        ),
                    }

            # --------------------------------------------------
            # PRIORITY 5: Navigate towards remembered berries.
            # --------------------------------------------------

            all_known_resources = {
                **self.shared_resources,
                **self.known_resources,
            }

            known_berries = [
                resource
                for resource in all_known_resources.values()
                if (
                    resource["resource_type"] == "berries"
                    and resource["quantity"] > 0
                    and not self.is_resource_claimed_by_other(
                        resource["position"],
                        observation,
                    )
                )
            ]

            if known_berries:

                target = min(
                    known_berries,
                    key=lambda resource: (
                        abs(
                            current_position[0]
                            - resource["position"][0]
                        )
                        + abs(
                            current_position[1]
                            - resource["position"][1]
                        )
                    ),
                )

                return {
                    "action": "navigate",
                    "target_position": target["position"],
                    "target_type": "resource",
                    "reason": (
                        "Hungry and a known, unclaimed berry resource "
                        "is available. Moving towards it."
                    ),
                }

        # --------------------------------------------------
        # PRIORITY 6: Deposit surplus resources.
        # --------------------------------------------------

        if storage is not None:

            storage_position = tuple(storage["position"])

            distance = (
                abs(current_position[0] - storage_position[0])
                + abs(current_position[1] - storage_position[1])
            )

            # Wood and stone can be deposited completely.
            wood_surplus = inventory.get("wood", 0)
            stone_surplus = inventory.get("stone", 0)

            # Keep one berry for personal consumption.
            berry_surplus = max(
                0,
                inventory.get("berries", 0) - 1,
            )

            surplus = {
                "wood": wood_surplus,
                "stone": stone_surplus,
                "berries": berry_surplus,
            }

            # Deposit one resource type at a time.
            for resource_type, amount in surplus.items():

                if amount <= 0:
                    continue

                if distance <= 1:
                    return {
                        "action": "deposit",
                        "resource_type": resource_type,
                        "amount": amount,
                        "reason": (
                            f"Carrying {amount} surplus {resource_type}. "
                            "Depositing it for team use."
                        ),
                    }

                return {
                    "action": "navigate",
                    "target_position": storage_position,
                    "target_type": "storage",
                    "reason": (
                        f"Carrying surplus {resource_type}. "
                        "Moving towards team storage."
                    ),
                }

        # --------------------------------------------------
        # PRIORITY 7: Explore.
        # --------------------------------------------------

        if hunger >= self.hunger_threshold:

            all_known_resources = {
                **self.shared_resources,
                **self.known_resources,
            }

            known_berries = [
                resource
                for resource in all_known_resources.values()
                if (
                    resource["resource_type"] == "berries"
                    and resource["quantity"] > 0
                )
            ]

            available_berries = [
                resource
                for resource in known_berries
                if not self.is_resource_claimed_by_other(
                    resource["position"],
                    observation,
                )
            ]

            if known_berries and not available_berries:

                reason = (
                    f"Hungry (hunger={hunger}), but all known "
                    "berry resources are currently claimed "
                    "by teammates. Exploring for alternatives."
                )

            elif not known_berries:

                reason = (
                    f"Hungry (hunger={hunger}), but no available "
                    "berry resources are known. Exploring to "
                    "search for food."
                )

            else:

                reason = (
                    f"Hungry (hunger={hunger}), but no immediate "
                    "food action is currently possible. Exploring."
                )

        else:

            reason = (
                f"Hunger is {hunger}, below the threshold "
                f"of {self.hunger_threshold}. Exploring to "
                "discover new resources."
            )

        return {
            "action": "explore",
            "reason": reason,
        }

    
    def update_memory(self, observation):
        """Update individual and shared memory."""

        # Remember the current position.
        current_position = tuple(observation["position"])
        self.visited_positions.add(current_position)

        # Update personally observed resources.
        for resource in observation["nearby_resources"]:

            position = tuple(resource["position"])

            if resource["quantity"] > 0:

                self.known_resources[position] = resource.copy()

            else:

                self.known_resources.pop(position, None)
                self.shared_resources.pop(position, None)

        # Update knowledge obtained from the team.
        for resource in observation.get("team_resources", []):

            position = tuple(resource["position"])

            if resource["quantity"] > 0:

                self.shared_resources[position] = resource.copy()

            else:

                # A teammate has reported that this resource is depleted.
                self.shared_resources.pop(position, None)
                self.known_resources.pop(position, None)


    def is_resource_claimed_by_other(self, position, observation):
        """Check whether another explorer has claimed a resource."""

        claims = observation.get("resource_claims", {})

        claim = claims.get(tuple(position))

        if claim is None:
            return False

        return claim["assigned_to"] != observation["name"]