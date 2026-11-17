from environment import create_resources, get_observation

from agents.rule_based_agent import RuleBasedAgent
from island_survivors.explorers import Explorer
from island_survivors.movement import ExplorerMovement
from island_survivors.map_data import MAP_LAYOUT, FEATURES


# Initialize resources and explorer.
resources = create_resources()

ava = Explorer(
    name="Ava",
    row=4,
    col=4,
    color="#E76F51",
    hunger=70,
)

agent = RuleBasedAgent()

# First observation: discover the nearby berry bush.
observation = get_observation(
    ava,
    resources,
    {},
)

agent.update_memory(observation)

print("Initial memory:", agent.known_resources)


# Move Ava elsewhere.
ava.row = 7
ava.col = 4

observation = get_observation(
    ava,
    resources,
    {},
)

# Ask the agent to decide.
action = agent.decide(observation)

print("Agent decision:", action)


# Initialize movement helper.
blocked_positions = {
    (row, col)
    for _, row, col in FEATURES
}

occupied_positions = {
    (ava.row, ava.col)
}

movement = ExplorerMovement(
    explorer=ava,
    animation_objects={
        "position": {
            "x": 0,
            "y": 0,
        }
    },
    map_layout=MAP_LAYOUT,
    blocked_positions=blocked_positions,
    occupied_positions=occupied_positions,
    map_options={
        "tile_size": 40,
        "origin_x": 40,
        "origin_y": 50,
    },
)

# Find the first step towards the berry bush.
next_position = movement.find_next_position_towards(
    action["target_position"],
)

print("Next movement position:", next_position)