import salabim as sim

from island_survivors.map_renderer import (
    draw_map,
    draw_explorers,
)

from island_survivors.explorers import EXPLORERS
from island_survivors.map_data import MAP_LAYOUT, FEATURES
from island_survivors.movement import ExplorerMovement
from island_survivors.survival import ExplorerNeeds

from environment import create_resources
from agents.rule_based_agent import RuleBasedAgent
from orchestration.game_controller import ExplorerController


def main():

    # Initialize simulation environment
    env = sim.Environment(
        trace=False,
        random_seed=42,
    )

    # Configure animation window
    env.animation_parameters(
        animate=True,
        width=1000,
        height=600,
        title="Island Survivors",
        background_color="#173449",
        speed=1,
    )

    # Map configuration
    map_options = {
        "tile_size": 40,
        "origin_x": 40,
        "origin_y": 50,
    }

    # Draw the island
    draw_map(env, **map_options)

    resources = create_resources()
    loot_caches = {}

    # Draw explorers
    explorer_animations = draw_explorers(
        env,
        EXPLORERS,
        **map_options,
    )


    # Positions occupied by map features
    blocked_positions = {
        (row, col)
        for _, row, col in FEATURES
    }

    # Initial positions occupied by explorers
    occupied_positions = {
        (explorer.row, explorer.col)
        for explorer in EXPLORERS
    }

    # Create a movement component for each explorer
    for index, explorer in enumerate(EXPLORERS):
        # Create a movement helper for this explorer.
        movement = ExplorerMovement(
            explorer=explorer,
            animation_objects=explorer_animations[explorer.name],

            map_layout=MAP_LAYOUT,
            blocked_positions=blocked_positions,
            occupied_positions=occupied_positions,

            map_options=map_options,

            move_duration=0.75,
            pause_duration=0.15,

            seed=42 + index,
        )

        # Create a decision-making controller.
        ExplorerController(
            env=env,
            explorer=explorer,
            agent=RuleBasedAgent(),
            resources=resources,
            movement=movement,

            loot_caches=loot_caches,
            occupied_positions=occupied_positions,

            decision_interval=1,
        )

        # Continue tracking hunger and health independently.
        ExplorerNeeds(
            env=env,
            explorer=explorer,
            update_interval=5,
        )

    # Side panel
    env.AnimateRectangle(
        spec=(665, 50, 900, 490),
        fillcolor="#24485B",
        linecolor="#52798A",
        linewidth=2,
        layer=12,
    )

    env.AnimateText(
        text="ISLAND SURVIVORS",
        x=670,
        y=465,
        fontsize=22,
        textcolor="#F4EBD0",
    )

    env.AnimateText(
        text="YOUR OBJECTIVES",
        x=670,
        y=440,
        fontsize=16,
        textcolor="#E9C879",
    )

    env.AnimateText(
        text=(
            "1. Explore the island\n"
            "2. Gather wood and food\n"
            "3. Discover hidden treasure\n"
            "4. Build a settlement\n"
            "5. Survive!"
        ),
        x=670,
        y=350,
        fontsize=14,
        textcolor="#FFFFFF",
    )

    env.AnimateText(
        text="WORLD INFORMATION",
        x=670,
        y=310,
        fontsize=16,
        textcolor="#E9C879",
    )

    env.AnimateText(
        text=(
            "Map size: 15 x 11\n"
            "Terrain: Island\n"
            "Explorers: 4\n"
            "Status: Preparing expedition"
        ),
        x=670,
        y=230,
        fontsize=14,
        textcolor="#FFFFFF",
    )

    # Keep the animation running
    env.run(env.inf)


if __name__ == "__main__":
    main()