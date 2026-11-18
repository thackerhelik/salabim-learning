from environment import create_resources, get_observation
from island_survivors.explorers import Explorer
from agents.rule_based_agent import RuleBasedAgent


# Initialize resources.
resources = create_resources()

# Initialize agent.
agent = RuleBasedAgent()

# Initialize Ava next to the berry bush at (4, 5).
ava = Explorer(
    name="Ava",
    row=4,
    col=4,
    color="#E76F51",
    hunger=70,
)


# Test 1: Hungry, no food in inventory, berries nearby.
observation = get_observation(ava, resources)

action = agent.decide(observation)

print("Test 1:", action)


# Test 2: Hungry, but already carrying berries.
ava.inventory["berries"] = 1

observation = get_observation(ava, resources)

action = agent.decide(observation)

print("Test 2:", action)


# Test 3: Not hungry.
ava.hunger = 20

observation = get_observation(ava, resources)

action = agent.decide(observation)

print("Test 3:", action)