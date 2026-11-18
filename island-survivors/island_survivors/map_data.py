
import math
import random


MAP_SIZE = 20

BASE_NAMES = [
    "northwest",
    "northeast",
    "southeast",
    "southwest",
]


def rotate_position(position, size=MAP_SIZE):
    """Rotate a position 90 degrees clockwise."""

    row, col = position

    return col, size - 1 - row


def get_rotation_orbit(position, size=MAP_SIZE):
    """Return the four rotationally symmetric positions."""

    positions = []
    current = position

    for _ in range(4):
        positions.append(current)
        current = rotate_position(current, size)

    return positions


def create_map_layout(size=MAP_SIZE):
    """Generate a circular-ish island with water, sand and grass."""

    center = (size - 1) / 2

    outer_radius = size / 2 - 0.5
    grass_radius = size / 2 - 2.0

    layout = []

    for row in range(size):

        row_tiles = []

        for col in range(size):

            distance = math.hypot(
                row - center,
                col - center,
            )

            if distance > outer_radius:
                tile = "~"

            elif distance > grass_radius:
                tile = "s"

            else:
                tile = "g"

            row_tiles.append(tile)

        layout.append("".join(row_tiles))

    return layout


def create_bases():
    """Create four rotationally symmetric team-base locations."""

    # Define the northwest base, then rotate it.
    template = {
        "storage_position": (4, 4),
        "campfire_position": (4, 5),
        "spawn_positions": [
            (5, 4),
            (3, 4),
        ],
    }

    bases = []

    for index, name in enumerate(BASE_NAMES):

        turns = index

        storage = template["storage_position"]
        campfire = template["campfire_position"]
        spawns = template["spawn_positions"]

        for _ in range(turns):

            storage = rotate_position(storage)
            campfire = rotate_position(campfire)

            spawns = [
                rotate_position(position)
                for position in spawns
            ]

        bases.append({
            "base_id": name,
            "storage_position": storage,
            "campfire_position": campfire,
            "spawn_positions": spawns,
        })

    return bases


def add_resource_orbit(
    features,
    used_positions,
    kind,
    position,
):
    """Add four identical resources in rotationally symmetric positions."""

    orbit = get_rotation_orbit(position)

    if len(set(orbit)) != 4:
        raise ValueError(
            f"Resource orbit is not unique: {orbit}"
        )

    if any(position in used_positions for position in orbit):
        raise ValueError(
            f"Resource placement overlaps another feature: {orbit}"
        )

    for row, col in orbit:

        features.append((kind, row, col))
        used_positions.add((row, col))


def generate_scenario(seed=42):
    """
    Generate a reproducible island scenario.

    The island geometry and four bases are fixed and symmetrical.
    Resource locations are randomized while preserving symmetry.
    """

    rng = random.Random(seed)

    map_layout = create_map_layout()

    bases = create_bases()

    features = []
    used_positions = set()

    # --------------------------------------------------
    # 1. Add base structures.
    # --------------------------------------------------

    for base in bases:

        storage = base["storage_position"]
        campfire = base["campfire_position"]

        features.append(("chest", *storage))
        features.append(("campfire", *campfire))

        used_positions.add(storage)
        used_positions.add(campfire)

        # Worker spawn locations must remain free.
        used_positions.update(base["spawn_positions"])

    # --------------------------------------------------
    # 2. Add local resources around each base.
    # --------------------------------------------------

    # These regions describe possible resource locations
    # around the northwest base. The generator rotates each
    # selected location to the other three quadrants.

    resource_regions = {
        "tree": [
            (row, col)
            for row in range(4, 6)
            for col in range(7, 10)
        ],

        "rock": [
            (row, col)
            for row in range(7, 10)
            for col in range(4, 7)
        ],

        "berry": [
            (row, col)
            for row in range(6, 8)
            for col in range(7, 10)
        ],
    }

    for kind, candidates in resource_regions.items():

        available = [
            position
            for position in candidates
            if (
                map_layout[position[0]][position[1]] == "g"
                and not any(
                    orbit_position in used_positions
                    for orbit_position in get_rotation_orbit(position)
                )
            )
        ]

        if not available:
            raise ValueError(
                f"No available positions for {kind} resources."
            )

        selected_position = rng.choice(available)

        add_resource_orbit(
            features=features,
            used_positions=used_positions,
            kind=kind,
            position=selected_position,
        )

    # --------------------------------------------------
    # 3. Add additional resources near the central region.
    # --------------------------------------------------

    central_candidates = [
        (8, 8),
        (8, 9),
        (9, 8),
        (9, 9),
    ]

    available_central = [
        position
        for position in central_candidates
        if not any(
            orbit_position in used_positions
            for orbit_position in get_rotation_orbit(position)
        )
    ]

    selected_central = rng.sample(
        available_central,
        k=2,
    )

    for position in selected_central:

        kind = rng.choice([
            "tree",
            "rock",
            "berry",
        ])

        add_resource_orbit(
            features=features,
            used_positions=used_positions,
            kind=kind,
            position=position,
        )

    return {
        "seed": seed,
        "map_layout": map_layout,
        "features": features,
        "bases": bases,
    }
