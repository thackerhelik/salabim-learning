# Task A

from agents.rule_based_agent import RuleBasedAgent

agent = RuleBasedAgent()

observation = {
    "name": "Ava",
    "position": (6, 6),
    "health": 100,
    "hunger": 20,
    "inventory": {
        "wood": 5,
        "stone": 0,
        "berries": 1,
    },
    "is_alive": True,
    "nearby_resources": [],
    "nearby_loot_caches": [],
    "team_resources": [],
    "resource_claims": {},
    "team_storage": {
        "position": (6, 7),
        "inventory": {
            "wood": 0,
            "stone": 0,
            "berries": 0,
        },
    },
}

action = agent.decide(observation)

print(action)


# Task B
observation["name"] = "Bram"
observation["hunger"] = 80
observation["inventory"] = {
    "wood": 0,
    "stone": 0,
    "berries": 0,
}

observation["team_storage"]["inventory"]["berries"] = 5

action = agent.decide(observation)

print(action)


# Task C
observation["position"] = (3, 8)

action = agent.decide(observation)

print(action)