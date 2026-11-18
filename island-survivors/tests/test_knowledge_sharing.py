from entities.team_knowledge import TeamKnowledge
from agents.rule_based_agent import RuleBasedAgent


# Create a shared board for Team 1.
team_board = TeamKnowledge(team_id=1)

# Create two agents.
ava_agent = RuleBasedAgent()
bram_agent = RuleBasedAgent()


# Ava discovers a berry bush.
berry_discovery = {
    "kind": "berry",
    "resource_type": "berries",
    "position": (4, 5),
    "quantity": 4,
}

team_board.update_resource(
    resource=berry_discovery,
    discovered_by="Ava",
    observed_at=10,
)


# Ava's observation.
ava_observation = {
    "position": (4, 4),
    "nearby_resources": [berry_discovery],
    "team_resources": team_board.get_resources(),
}

ava_agent.update_memory(ava_observation)

print("Ava's personal memory:", ava_agent.known_resources)


# Bram has never visited the berry bush.
bram_observation = {
    "position": (7, 4),
    "nearby_resources": [],
    "team_resources": team_board.get_resources(),
}

bram_agent.update_memory(bram_observation)

print("Bram's personal memory:", bram_agent.known_resources)
print("Bram's shared memory:", bram_agent.shared_resources)


# Bram becomes hungry and makes a decision.
bram_observation.update({
    "health": 100,
    "hunger": 70,
    "inventory": {
        "wood": 0,
        "stone": 0,
        "berries": 0,
    },
    "is_alive": True,
    "nearby_loot_caches": [],
})

action = bram_agent.decide(bram_observation)

print("Bram's decision:", action)


# Test 2
team_1 = TeamKnowledge(team_id=1)
team_2 = TeamKnowledge(team_id=2)

team_1.update_resource(
    resource=berry_discovery,
    discovered_by="Ava",
    observed_at=10,
)

print("Team 1:", team_1.get_resources())
print("Team 2:", team_2.get_resources())