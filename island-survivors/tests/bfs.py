from island_survivors.explorers import Explorer
from island_survivors.movement import ExplorerMovement
from island_survivors.map_data import MAP_LAYOUT, FEATURES


# Initialize explorer.
ava = Explorer(
    name="Ava",
    row=7,
    col=4,
    color="#E76F51",
)

# Map features that cannot be traversed.
blocked_positions = {
    (row, col)
    for _, row, col in FEATURES
}

# Initially, only Ava's starting tile is occupied.
occupied_positions = {
    (ava.row, ava.col)
}

# Initialize movement helper.
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

# Initially visited tile.
visited_positions = {
    (ava.row, ava.col)
}

# Find the next unexplored tile.
next_position = movement.find_next_unvisited_position(
    visited_positions
)

print("Current position:", (ava.row, ava.col))
print("Visited positions:", visited_positions)
print("Next unexplored position:", next_position)

assert next_position is not None
assert next_position not in visited_positions

assert MAP_LAYOUT[next_position[0]][next_position[1]] in {"g", "s"}
assert next_position not in blocked_positions


if next_position is not None:

    old_position = (ava.row, ava.col)

    # Update visited positions.
    visited_positions.add(next_position)

    # Update occupied positions.
    occupied_positions.remove(old_position)
    occupied_positions.add(next_position)

    # Update Ava's location.
    ava.row, ava.col = next_position

    # Find the next unexplored tile.
    next_position = movement.find_next_unvisited_position(
        visited_positions
    )

    print("Updated position:", (ava.row, ava.col))
    print("Updated memory:", visited_positions)
    print("Next step:", next_position)