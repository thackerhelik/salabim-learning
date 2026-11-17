from environment import get_observation
from entities.loot_cache import LootCache
from island_survivors.explorers import Explorer
from agents.rule_based_agent import RuleBasedAgent
from orchestration.game_controller import execute_action


# No natural resources nearby.
resources = {}

# Create a nearby loot cache.
loot_caches = {
    (4, 5): LootCache(
        row=4,
        col=5,
        inventory={
            "wood": 5,
            "stone": 2,
            "berries": 3,
        },
    )
}

# Initialize Ava.
ava = Explorer(
    name="Ava",
    row=4,
    col=4,
    color="#E76F51",
    hunger=70,
)

agent = RuleBasedAgent()


# Obtain observation.
observation = get_observation(
    ava,
    resources,
    loot_caches,
)

# Ask agent to decide.
action = agent.decide(observation)

print("Decision:", action)

# Execute the selected action.
result = execute_action(
    ava,
    resources,
    loot_caches,
    action,
)

print("Result:", result)
print("Ava's inventory:", ava.inventory)
print("Remaining cache:", loot_caches[(4, 5)].inventory)