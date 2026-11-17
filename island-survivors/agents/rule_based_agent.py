class RuleBasedAgent:
    """Makes decisions using predefined survival priorities."""

    def __init__(self, hunger_threshold=60):
        self.hunger_threshold = hunger_threshold

    
    def decide(self, observation):
        """Choose an action based on the current observation."""

        # Dead explorers cannot perform actions.
        if not observation["is_alive"]:
            return {"action": "none"}

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

                if resource["resource_type"] == "berries":

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

        # Priority 4: Explore.
        return {
            "action": "explore",
        }