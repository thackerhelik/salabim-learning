
import unittest

from island_survivors.map_data import (
    generate_scenario,
    rotate_position,
)


class TestScenarioGeneration(unittest.TestCase):

    def test_map_dimensions(self):

        scenario = generate_scenario(seed=42)

        layout = scenario["map_layout"]

        self.assertEqual(len(layout), 20)

        for row in layout:
            self.assertEqual(len(row), 20)

    def test_same_seed_generates_same_scenario(self):

        first = generate_scenario(seed=42)
        second = generate_scenario(seed=42)

        self.assertEqual(
            first["map_layout"],
            second["map_layout"],
        )

        self.assertEqual(
            first["features"],
            second["features"],
        )

    def test_map_is_rotationally_symmetric(self):

        scenario = generate_scenario(seed=42)
        layout = scenario["map_layout"]

        for row in range(20):
            for col in range(20):

                rotated_row, rotated_col = rotate_position(
                    (row, col)
                )

                self.assertEqual(
                    layout[row][col],
                    layout[rotated_row][rotated_col],
                )

    def test_features_are_rotationally_symmetric(self):

        scenario = generate_scenario(seed=42)

        features = set(scenario["features"])

        for kind, row, col in features:

            rotated = rotate_position((row, col))

            self.assertIn(
                (kind, *rotated),
                features,
            )

    def test_four_bases_exist(self):

        scenario = generate_scenario(seed=42)

        bases = scenario["bases"]

        self.assertEqual(len(bases), 4)

        for index in range(4):

            current = bases[index]
            following = bases[(index + 1) % 4]

            rotated_storage = rotate_position(
                current["storage_position"]
            )

            self.assertEqual(
                rotated_storage,
                following["storage_position"],
            )

    def test_spawn_positions_are_valid(self):

        scenario = generate_scenario(seed=42)

        layout = scenario["map_layout"]
        features = set(scenario["features"])

        occupied_by_features = {
            (row, col)
            for _, row, col in features
        }

        all_spawns = []

        for base in scenario["bases"]:

            self.assertEqual(
                len(base["spawn_positions"]),
                2,
            )

            for position in base["spawn_positions"]:

                row, col = position

                self.assertIn(
                    layout[row][col],
                    {"g", "s"},
                )

                self.assertNotIn(
                    position,
                    occupied_by_features,
                )

                self.assertNotIn(position, all_spawns)

                all_spawns.append(position)

    def test_feature_positions_are_unique(self):

        scenario = generate_scenario(seed=42)

        positions = [
            (row, col)
            for _, row, col in scenario["features"]
        ]

        self.assertEqual(
            len(positions),
            len(set(positions)),
        )


if __name__ == "__main__":
    unittest.main()
