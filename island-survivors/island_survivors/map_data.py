# Each string represents one row of the map.
# Rows are stored from top to bottom.

"""
 ~ water
 s sand
 g grass
"""
MAP_LAYOUT = [
    "~~~~~~~~~~~~~~~",
    "~~~~~ssssss~~~~",
    "~~~ssgggggss~~~",
    "~~ssgggggggss~~",
    "~ssgggggggggss~",
    "~ssgggggggggss~",
    "~ssgggggggggss~",
    "~~ssgggggggss~~",
    "~~~ssgggggss~~~",
    "~~~~~ssssss~~~~",
    "~~~~~~~~~~~~~~~",
]


# Objects are specified as (object_type, row, column).
# Coordinates start at the top-left: (0, 0).
FEATURES = [
    ("tree", 3, 5),
    # ("tree", 3, 6),
    ("tree", 4, 9),

    ("rock", 3, 6),
    ("rock", 6, 11),

    ("berry", 4, 5),

    ("campfire", 5, 6),
    ("chest", 6, 7),
]