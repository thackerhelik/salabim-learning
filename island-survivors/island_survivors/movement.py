import random
from collections import deque


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

        # None in headless mode; otherwise references the sprite position.
        self.position = (
            animation_objects["position"]
            if animation_objects is not None
            else None
        )

        self.map_layout = map_layout
        self.blocked_positions = blocked_positions
        self.occupied_positions = occupied_positions

        self.tile_size = map_options["tile_size"]
        self.origin_x = map_options["origin_x"]
        self.origin_y = map_options["origin_y"]

        self.move_duration = move_duration
        self.pause_duration = pause_duration

        self.rng = random.Random(seed)

        # Information about a move that has not yet completed.
        self._active_move = None

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

    def find_next_position_towards(self, target_position):
        """Find the next step towards a resource using BFS."""

        current_position = (
            self.explorer.row,
            self.explorer.col,
        )

        target_row, target_col = target_position

        num_rows = len(self.map_layout)
        num_cols = len(self.map_layout[0])

        directions = [
            (-1, 0),  # North
            (1, 0),   # South
            (0, -1),  # West
            (0, 1),   # East
        ]

        # The explorer needs to reach a tile adjacent to the resource,
        # rather than the resource tile itself.
        approach_positions = set()

        for drow, dcol in directions:

            row = target_row + drow
            col = target_col + dcol

            if not (0 <= row < num_rows and 0 <= col < num_cols):
                continue

            position = (row, col)

            if self.map_layout[row][col] not in {"g", "s"}:
                continue

            if position in self.blocked_positions:
                continue

            approach_positions.add(position)

        if not approach_positions:
            return None

        if current_position in approach_positions:
            return None

        # Initialize BFS.
        queue = deque([current_position])

        # Store each position's predecessor.
        parents = {
            current_position: None,
        }

        while queue:

            current = queue.popleft()

            current_row, current_col = current

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

                # Avoid already visited positions.
                if new_position in parents:
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

                parents[new_position] = current

                # Check whether we reached an approach tile.
                if new_position in approach_positions:

                    # Reconstruct the path's first step.
                    step = new_position

                    while parents[step] != current_position:
                        step = parents[step]

                    return step

                queue.append(new_position)

        # No valid path exists.
        return None

    
    def find_next_unvisited_position(self, visited_positions):
        """Find the next step towards the nearest unvisited tile."""

        current_position = (
            self.explorer.row,
            self.explorer.col,
        )

        num_rows = len(self.map_layout)
        num_cols = len(self.map_layout[0])

        directions = [
            (-1, 0),  # North
            (1, 0),   # South
            (0, -1),  # West
            (0, 1),   # East
        ]
        # Randomize direction priority to break ties.
        self.rng.shuffle(directions)

        # Initialize BFS.
        queue = deque([current_position])

        # Store each position's predecessor.
        parents = {
            current_position: None,
        }

        while queue:

            current = queue.popleft()

            current_row, current_col = current

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

                # Avoid already visited BFS nodes.
                if new_position in parents:
                    continue

                # Check walkable terrain.
                if self.map_layout[new_row][new_col] not in {"g", "s"}:
                    continue

                # Avoid map features.
                if new_position in self.blocked_positions:
                    continue

                # Avoid other living explorers.
                if new_position in self.occupied_positions:
                    continue

                # Record the predecessor.
                parents[new_position] = current

                # Check if this is an unexplored destination.
                if new_position not in visited_positions:

                    # Reconstruct the path's first step.
                    step = new_position

                    while parents[step] != current_position:
                        step = parents[step]

                    return step

                # Visited tiles are still valid paths.
                queue.append(new_position)

        # No reachable unexplored tile exists.
        return None


    def cancel_current_move(self):
        """Cancel an unfinished move and release its destination."""

        move = self._active_move

        if move is None:
            return False

        # Mark the movement routine as cancelled.
        move["cancelled"] = True

        # Return the sprite to its last committed position, if animated.
        if move["position"] is not None:

            move["position"]["x"] = move["start_x"]
            move["position"]["y"] = move["start_y"]

        # Release the reserved destination.
        self.occupied_positions.discard(
            move["destination"]
        )

        self._active_move = None

        return True


    def move_one_step(self, process):
        """Move randomly by one neighbouring tile."""

        next_position = self.find_next_position()

        return self._move_to_position(process, next_position)


    def move_towards(self, process, target_position):
        """Move one step towards a target using BFS."""

        next_position = self.find_next_position_towards(
            target_position
        )

        return self._move_to_position(process, next_position)

    def move_towards_unvisited(self, process, visited_positions):
        """Move one step towards the nearest unexplored tile."""

        next_position = self.find_next_unvisited_position(
            visited_positions
        )

        # Fall back to random movement if nothing unexplored remains.
        if next_position is None:
            next_position = self.find_next_position()

        return self._move_to_position(
            process,
            next_position,
        )

    def _move_to_position(self, process, next_position):
        """Move one tile, optionally animating the sprite.

        Movement duration and scheduling are preserved in headless mode.
        """

        if not self.explorer.is_alive or next_position is None:
            return False

        current_position = (
            self.explorer.row,
            self.explorer.col,
        )

        if next_position in self.occupied_positions:
            return False

        # Reserve the destination.
        self.occupied_positions.add(next_position)

        new_row, new_col = next_position

        # Calculate screen coordinates only when animation is enabled.
        if self.position is not None:

            from island_survivors.map_renderer import get_tile_center

            target_x, target_y = get_tile_center(
                new_row,
                new_col,
                len(self.map_layout),
                self.tile_size,
                self.origin_x,
                self.origin_y,
            )

            start_x = self.position["x"]
            start_y = self.position["y"]

        else:
            start_x = None
            start_y = None
            target_x = None
            target_y = None

        move = {
            "destination": next_position,
            "position": self.position,
            "start_x": start_x,
            "start_y": start_y,
            "cancelled": False,
        }

        self._active_move = move

        animation_steps = 20
        step_duration = self.move_duration / animation_steps

        try:

            for i in range(1, animation_steps + 1):

                if move["cancelled"] or not self.explorer.is_alive:

                    if self._active_move is move:
                        self.cancel_current_move()

                    return False

                # Update graphical position only in visual mode.
                if self.position is not None:

                    fraction = i / animation_steps

                    self.position["x"] = (
                        start_x + (target_x - start_x) * fraction
                    )

                    self.position["y"] = (
                        start_y + (target_y - start_y) * fraction
                    )

                # Preserve simulation timing in both modes.
                process.hold(step_duration)

                if move["cancelled"] or not self.explorer.is_alive:

                    if self._active_move is move:
                        self.cancel_current_move()

                    return False

            # Commit the new grid position.
            self.explorer.row = new_row
            self.explorer.col = new_col

            # Release the previous tile.
            self.occupied_positions.remove(current_position)

            self._active_move = None

            if self.pause_duration > 0:
                process.hold(self.pause_duration)

            return self.explorer.is_alive

        except Exception:

            if self._active_move is move:
                self.cancel_current_move()

            raise
