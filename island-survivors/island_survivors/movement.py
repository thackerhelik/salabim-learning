import random

from island_survivors.map_renderer import get_tile_center


class ExplorerMovement:
    """Handles the movement and animation of an explorer."""

    def __init__(
        self,
        explorer,
        animation_objects,
        map_layout,
        blocked_positions,
        occupied_positions,
        map_options,
        move_duration=0.75,
        pause_duration=0.15,
        seed=42,
    ):
        self.explorer = explorer
        self.animation_objects = animation_objects

        self.map_layout = map_layout
        self.blocked_positions = blocked_positions
        self.occupied_positions = occupied_positions

        self.tile_size = map_options["tile_size"]
        self.origin_x = map_options["origin_x"]
        self.origin_y = map_options["origin_y"]

        self.move_duration = move_duration
        self.pause_duration = pause_duration

        self.rng = random.Random(seed)

    def find_next_position(self):
        """Find a valid neighbouring tile."""

        current_row = self.explorer.row
        current_col = self.explorer.col

        num_rows = len(self.map_layout)
        num_cols = len(self.map_layout[0])

        directions = [
            (-1, 0),  # North
            (1, 0),   # South
            (0, -1),  # West
            (0, 1),   # East
        ]

        self.rng.shuffle(directions)

        for drow, dcol in directions:

            new_row = current_row + drow
            new_col = current_col + dcol

            new_position = (new_row, new_col)

            # Check map boundaries.
            if not (
                0 <= new_row < num_rows
                and 0 <= new_col < num_cols
            ):
                continue

            # Check walkable terrain.
            if self.map_layout[new_row][new_col] not in {"g", "s"}:
                continue

            # Avoid map features.
            if new_position in self.blocked_positions:
                continue

            # Avoid other explorers.
            if new_position in self.occupied_positions:
                continue

            return new_position

        return None

    def move_one_step(self, process):
        """Move the explorer by one tile, with smooth animation."""

        next_position = self.find_next_position()

        if next_position is None:
            return False

        current_position = (
            self.explorer.row,
            self.explorer.col,
        )

        # Reserve the destination to prevent collisions.
        self.occupied_positions.add(next_position)

        new_row, new_col = next_position

        target_x, target_y = get_tile_center(
            new_row,
            new_col,
            len(self.map_layout),
            self.tile_size,
            self.origin_x,
            self.origin_y,
        )

        position = self.animation_objects["position"]

        start_x = position["x"]
        start_y = position["y"]

        # Smooth movement through interpolation.
        animation_steps = 10
        step_duration = self.move_duration / animation_steps

        for i in range(1, animation_steps + 1):

            fraction = i / animation_steps

            position["x"] = (
                start_x + (target_x - start_x) * fraction
            )

            position["y"] = (
                start_y + (target_y - start_y) * fraction
            )

            # Advance the calling Salabim component.
            process.hold(step_duration)

        # Update the explorer's actual grid position.
        self.explorer.row = new_row
        self.explorer.col = new_col

        # Release the previous tile.
        self.occupied_positions.remove(current_position)

        process.hold(self.pause_duration)

        return True
