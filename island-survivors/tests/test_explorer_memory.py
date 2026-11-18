from environment import create_resources, get_observation
from island_survivors.explorers import Explorer
from agents.rule_based_agent import RuleBasedAgent


resources = create_resources()

ava = Explorer(
    name="Ava",
    row=4,
    col=4,
    color="#E76F51",
)

agent = RuleBasedAgent()


# First observation: Ava discovers the berry bush.
observation = get_observation(ava, resources)

action = agent.decide(observation)

print("Decision:", action)
print("Known resources:", agent.known_resources)


# Simulate another explorer depleting the berry bush.
resources[(4, 5)].quantity = 0


# Second observation: Ava discovers that the bush is empty.
observation = get_observation(ava, resources)

action = agent.decide(observation)

print("\nDecision:", action)
print("Known resources:", agent.known_resources)