from environment import create_resources, get_observation
from island_survivors.explorers import Explorer
from agents.rule_based_agent import RuleBasedAgent
from orchestration.game_controller import execute_action


# Initialize the world.
resources = create_resources()

# Initialize Ava.
ava = Explorer(
    name="Ava",
    row=4,
    col=4,
    color="#E76F51",
    hunger=70,
)

# Initialize her decision-making agent.
agent = RuleBasedAgent()


# First decision.
observation = get_observation(ava, resources)
action = agent.decide(observation)

print("Decision 1:", action)

# Execute the decision.
result = execute_action(ava, resources, action)

print("Result 1:", result)
print("Inventory:", ava.inventory)


# Second decision, using the updated world state.
observation = get_observation(ava, resources)
action = agent.decide(observation)

print("\nDecision 2:", action)

result = execute_action(ava, resources, action)

print("Result 2:", result)
print("Inventory:", ava.inventory)
print("Hunger:", ava.hunger)