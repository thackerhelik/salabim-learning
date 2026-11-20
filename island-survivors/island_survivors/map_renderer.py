TERRAIN_COLORS = {
    "~": "#347DAB",  # Water
    "s": "#D9BD83",  # Sand
    "g": "#6C9C59",  # Grass
}


def get_tile_center(row, col, num_rows, tile_size, origin_x, origin_y):
    x = origin_x + col * tile_size + tile_size / 2
    y = origin_y + (num_rows - 1 - row) * tile_size + tile_size / 2

    return x, y


def draw_tree(env, x, y):

    # Tree trunk
    env.AnimateRectangle(
        spec=(x - 3, y - 12, x + 3, y + 5),
        fillcolor="#79512F",
        linecolor="#63412A",
        layer=6,
        screen_coordinates=False,
    )

    # Tree foliage
    env.AnimateCircle(
        radius=12,
        x=x,
        y=y + 7,
        fillcolor="#286642",
        linecolor="#19472D",
        layer=5,
        screen_coordinates=False,
    )

    env.AnimateCircle(
        radius=8,
        x=x - 6,
        y=y + 9,
        fillcolor="#438653",
        linecolor="#285A37",
        layer=4,
        screen_coordinates=False,
    )


def draw_rock(env, x, y):

    env.AnimateCircle(
        radius=9,
        x=x - 3,
        y=y,
        fillcolor="#858F96",
        linecolor="#59636A",
        layer=5,
        screen_coordinates=False,
    )

    env.AnimateCircle(
        radius=7,
        x=x + 5,
        y=y - 2,
        fillcolor="#AAB3B7",
        linecolor="#626C73",
        layer=4,
        screen_coordinates=False,
    )


def draw_berry(env, x, y):

    # Bush
    env.AnimateCircle(
        radius=9,
        x=x,
        y=y,
        fillcolor="#286642",
        linecolor="#19472D",
        layer=5,
        screen_coordinates=False,
    )

    # Berries
    for dx, dy in [(-4, 2), (3, 3), (0, -4)]:
        env.AnimateCircle(
            radius=2.5,
            x=x + dx,
            y=y + dy,
            fillcolor="#D94343",
            linecolor="#922626",
            layer=3,
            screen_coordinates=False,
        )


def draw_campfire(env, x, y):

    # Fire base
    env.AnimateCircle(
        radius=11,
        x=x,
        y=y,
        fillcolor="#656565",
        linecolor="#333333",
        layer=5,
        screen_coordinates=False,
    )

    # Flame
    env.AnimateCircle(
        radius=7,
        x=x,
        y=y + 1,
        fillcolor="#F28C28",
        linecolor="#B84A17",
        layer=3,
        screen_coordinates=False,
    )

    env.AnimateCircle(
        radius=3,
        x=x,
        y=y + 1,
        fillcolor="#FFE36B",
        linecolor="#E69A24",
        layer=2,
        screen_coordinates=False,
    )


def draw_chest(env, x, y):

    env.AnimateRectangle(
        spec=(x - 10, y - 7, x + 10, y + 7),
        fillcolor="#A66A2C",
        linecolor="#58391F",
        linewidth=2,
        layer=4,
        screen_coordinates=False,
    )

    env.AnimateRectangle(
        spec=(x - 2, y - 7, x + 2, y + 7),
        fillcolor="#E6C75C",
        linecolor="#8A6B28",
        layer=2,
        screen_coordinates=False,
    )


def draw_map(
    env,
    map_layout,
    features,
    tile_size=40,
    origin_x=40,
    origin_y=50,
):
    """Draw terrain and objects using Salabim."""

    rows = len(map_layout)
    cols = len(map_layout[0])

    # Validate map dimensions
    if any(len(row) != cols for row in map_layout):
        raise ValueError("All map rows must have the same length.")

    # Draw terrain
    for row_index, row in enumerate(map_layout):

        for col_index, tile in enumerate(row):

            if tile not in TERRAIN_COLORS:
                raise ValueError(f"Unknown terrain symbol: {tile}")

            x = origin_x + col_index * tile_size
            y = origin_y + (rows - 1 - row_index) * tile_size

            env.AnimateRectangle(
                spec=(
                    x,
                    y,
                    x + tile_size,
                    y + tile_size,
                ),
                fillcolor=TERRAIN_COLORS[tile],
                linecolor="#527E62",
                linewidth=1,
                layer=10,
                screen_coordinates=False,
            )

    # Draw objects on top of the terrain
    draw_functions = {
        "tree": draw_tree,
        "rock": draw_rock,
        "berry": draw_berry,
        "campfire": draw_campfire,
        "chest": draw_chest,
    }

    for kind, row, col in features:

        if kind not in draw_functions:
            raise ValueError(f"Unknown feature type: {kind}")

        if not (0 <= row < rows and 0 <= col < cols):
            raise ValueError(f"Feature outside map: {kind}, {row}, {col}")

        if map_layout[row][col] not in {"g", "s"}:
            raise ValueError(f"{kind} must be placed on grass.")

        x, y = get_tile_center(
            row, col, rows, tile_size, origin_x, origin_y
        )

        draw_functions[kind](env, x, y)


def draw_explorers(
    env,
    explorers,
    map_layout,
    features,
    tile_size=40,
    origin_x=40,
    origin_y=50,
):
    """Draw all explorers on the map."""

    num_rows = len(map_layout)
    num_cols = len(map_layout[0])

    feature_positions = {
        (row, col)
        for _, row, col in features
    }

    occupied_positions = set()
    animation_objects = {}

    for explorer in explorers:

        row = explorer.row
        col = explorer.col

        # Validate coordinates
        if not (0 <= row < num_rows and 0 <= col < num_cols):
            raise ValueError(
                f"Explorer {explorer.name} is outside the map."
            )

        if map_layout[row][col] not in {"g", "s"}:
            raise ValueError(
                f"Explorer {explorer.name} is not on grass."
            )

        if (row, col) in feature_positions:
            raise ValueError(
                f"Explorer {explorer.name} overlaps a map feature."
            )

        if (row, col) in occupied_positions:
            raise ValueError(
                f"Multiple explorers occupy ({row}, {col})."
            )

        occupied_positions.add((row, col))

        # Convert grid coordinates into screen coordinates
        x, y = get_tile_center(
            row,
            col,
            num_rows,
            tile_size,
            origin_x,
            origin_y,
        )

        # Shared dynamic position
        position = {
            "x": x,
            "y": y,
        }

        # Draw explorer body
        sprite = env.AnimateCircle(
            radius=11,
            x=lambda pos=position: pos["x"],
            y=lambda pos=position: pos["y"],
            fillcolor=explorer.color,
            linecolor="#F8EBD0",
            linewidth=2,
            text=explorer.name[0],
            textcolor="#FFFFFF",
            fontsize=11,
            layer=0,
            screen_coordinates=False,
        )

        # Draw explorer name
        label = env.AnimateText(
            text=explorer.name,
            x=lambda pos=position: pos["x"],
            y=lambda pos=position: pos["y"] + 15,
            fontsize=10,
            textcolor="#FFFFFF",
            text_anchor="s",
            layer=-1,
            screen_coordinates=False,
        )

        animation_objects[explorer.name] = {
            "sprite": sprite,
            "label": label,
            "position": position,
        }

    return animation_objects
