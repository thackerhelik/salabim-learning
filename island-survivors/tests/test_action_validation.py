import unittest

from orchestration.action_validation import validate_action


class TestActionValidation(unittest.TestCase):

    def validate(self, action):
        return validate_action(
            raw_action=action,
            map_rows=10,
            map_cols=10,
        )

    def test_valid_gather_action(self):

        action, error = self.validate({
            "action": "gather",
            "target_position": [4, 5],
            "reason": "Collect berries.",
        })

        self.assertIsNone(error)
        self.assertEqual(action["action"], "gather")
        self.assertEqual(action["target_position"], (4, 5))
        self.assertEqual(action["amount"], 2)

    def test_valid_navigation_action(self):

        action, error = self.validate({
            "action": "navigate",
            "target_position": [6, 7],
            "target_type": "storage",
        })

        self.assertIsNone(error)
        self.assertEqual(action["target_position"], (6, 7))

    def test_non_dictionary_action_is_rejected(self):

        action, error = self.validate(None)

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_unknown_action_is_rejected(self):

        action, error = self.validate({
            "action": "teleport",
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_string_amount_is_rejected(self):

        action, error = self.validate({
            "action": "gather",
            "target_position": [4, 5],
            "amount": "two",
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_boolean_amount_is_rejected(self):

        action, error = self.validate({
            "action": "gather",
            "target_position": [4, 5],
            "amount": True,
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_zero_amount_is_rejected(self):

        action, error = self.validate({
            "action": "gather",
            "target_position": [4, 5],
            "amount": 0,
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_invalid_position_is_rejected(self):

        action, error = self.validate({
            "action": "gather",
            "target_position": [100, 5],
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_boolean_coordinate_is_rejected(self):

        action, error = self.validate({
            "action": "gather",
            "target_position": [True, 5],
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_invalid_resource_type_is_rejected(self):

        action, error = self.validate({
            "action": "deposit",
            "resource_type": "gold",
            "amount": 1,
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_invalid_navigation_target_type_is_rejected(self):

        action, error = self.validate({
            "action": "navigate",
            "target_position": [4, 5],
            "target_type": "unknown",
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_unexpected_fields_are_rejected(self):

        action, error = self.validate({
            "action": "eat",
            "amount": 1,
            "teleport": True,
        })

        self.assertIsNone(action)
        self.assertIsNotNone(error)

    def test_valid_json_style_loot_action(self):

        action, error = self.validate({
            "action": "loot",
            "target_position": [2, 3],
            "resource_type": "wood",
            "amount": 2,
            "reason": "Recover dropped wood.",
        })

        self.assertIsNone(error)
        self.assertEqual(action["target_position"], (2, 3))
        self.assertEqual(action["resource_type"], "wood")


if __name__ == "__main__":
    unittest.main()