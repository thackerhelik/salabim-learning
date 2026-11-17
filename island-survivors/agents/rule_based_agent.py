class RuleBasedAgent:
    """Makes decisions using predefined survival priorities."""

    def __init__(self, hunger_threshold=60):
        self.hunger_threshold = hunger_threshold

        # Resources discovered by this explorer.
        self.known_resources = {}

        # Tiles visited by this explorer.
        self.visited_positions = set()

    
    def decide(self, observation):
        """Choose an action based on the current observation."""

        # Dead explorers cannot perform actions.
        if not observation["is_alive"]:
            return {"action": "none"}

        self.update_memory(observation)

        hunger = observation["hunger"]
        inventory = observation["inventory"]

        # Priority 1: Eat when hungry and carrying berries.
        if hunger >= self.hunger_threshold:

            if inventory.get("berries", 0) > 0:
                return {
                    "action": "eat",
                    "amount": 1,
                }

            # Priority 2: Gather berries from nearby bushes.
            for resource in observation["nearby_resources"]:

                if (
                    resource["resource_type"] == "berries"
                    and resource["quantity"] > 0
                ):
                    return {
                        "action": "gather",
                        "target_position": resource["position"],
                        "amount": 2,
                    }

            # Priority 3: Loot berries from nearby caches.
            for cache in observation.get("nearby_loot_caches", []):

                if cache["inventory"].get("berries", 0) > 0:
                    return {
                        "action": "loot",
                        "target_position": cache["position"],
                        "resource_type": "berries",
                        "amount": 2,
                    }

            # Priority 4: Navigate towards a remembered berry bush.
            current_position = observation["position"]

            known_berries = [
                resource
                for resource in self.known_resources.values()
                if (
                    resource["resource_type"] == "berries"
                    and resource["quantity"] > 0
                )
            ]

            if known_berries:

                # Select the closest remembered berry bush
                # using Manhattan distance.
                target = min(
                    known_berries,
                    key=lambda resource: (
                        abs(current_position[0] - resource["position"][0])
                        + abs(current_position[1] - resource["position"][1])
                    ),
                )

                return {
                    "action": "navigate",
                    "target_position": target["position"],
                }

        # Priority 5: Explore.
        return {
            "action": "explore",
        }


    def update_memory(self, observation):
        """Update the explorer's memory using current observations."""

        # Remember the current position.
        current_position = tuple(observation["position"])

        self.visited_positions.add(current_position)

        # Update known resources.
        for resource in observation["nearby_resources"]:

            position = tuple(resource["position"])

            if resource["quantity"] > 0:
                # Remember or update the resource.
                self.known_resources[position] = resource.copy()
            else:
                # Forget depleted resources.
                self.known_resources.pop(position, None)