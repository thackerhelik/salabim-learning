
from collections.abc import Mapping


RESOURCE_TYPES = {
    "wood",
    "stone",
    "berries",
}

RESOURCE_TARGET_TYPES = {
    "resource",
    "storage",
}

DEFAULT_AMOUNTS = {
    "gather": 2,
    "eat": 1,
    "loot": 1,
    "deposit": 1,
    "withdraw": 1,
}

MAX_ACTION_AMOUNT = 1000


# These schemas describe the actions currently supported
# by our simulation.
ACTION_FIELDS = {
    "explore": {"action"},
    "navigate": {"action", "target_position", "target_type"},
    "gather": {"action", "target_position", "amount"},
    "eat": {"action", "amount"},
    "loot": {
        "action",
        "target_position",
        "resource_type",
        "amount",
    },
    "deposit": {
        "action",
        "resource_type",
        "amount",
    },
    "withdraw": {
        "action",
        "resource_type",
        "amount",
    },
    "none": {"action"},
}


def validate_action(
    raw_action,
    map_rows,
    map_cols,
):
    """
    Validate and normalize an action returned by an agent.

    Returns:
        (normalized_action, None) on success.
        (None, error_message) on failure.

    Position lists from JSON are normalized into tuples.
    Default action amounts and reasons are added here.
    """

    # --------------------------------------------------
    # 1. Validate the overall action structure.
    # --------------------------------------------------

    if not isinstance(raw_action, Mapping):
        return None, (
            "Action must be a dictionary-like object."
        )

    action = dict(raw_action)

    action_type = action.get("action")

    if not isinstance(action_type, str):
        return None, "Action type must be a string."

    if action_type not in ACTION_FIELDS:
        return None, f"Unknown action type: {action_type}"

    # --------------------------------------------------
    # 2. Validate allowed fields.
    # --------------------------------------------------

    allowed_fields = ACTION_FIELDS[action_type] | {"reason"}

    unexpected_fields = (
        set(action.keys()) - allowed_fields
    )

    if unexpected_fields:
        return None, (
            f"Unexpected fields for {action_type}: "
            f"{sorted(unexpected_fields, key=str)}"
        )

    # --------------------------------------------------
    # 3. Validate optional explanation.
    # --------------------------------------------------

    reason = action.get("reason", "")

    if not isinstance(reason, str):
        return None, "Action reason must be a string."

    if len(reason) > 500:
        return None, "Action reason is too long (maximum 500 characters)."

    action["reason"] = reason

    # --------------------------------------------------
    # 4. Validate target position.
    # --------------------------------------------------

    if action_type in {"navigate", "gather", "loot"}:

        position = action.get("target_position")

        if not isinstance(position, (list, tuple)):
            return None, "Target position must be a list or tuple."

        if len(position) != 2:
            return None, (
                "Target position must contain exactly two coordinates."
            )

        row, col = position

        # Use exact type checks because bool is a subclass of int.
        if type(row) is not int or type(col) is not int:
            return None, (
                "Target coordinates must be integers."
            )

        if not (0 <= row < map_rows):
            return None, f"Target row is outside the map: {row}"

        if not (0 <= col < map_cols):
            return None, f"Target column is outside the map: {col}"

        # Normalize JSON lists to tuples for dictionary lookups.
        action["target_position"] = (row, col)

    # --------------------------------------------------
    # 5. Validate navigation target type.
    # --------------------------------------------------

    if action_type == "navigate":

        target_type = action.get("target_type")

        if (
            not isinstance(target_type, str)
            or target_type not in RESOURCE_TARGET_TYPES
        ):
            return None, (
                "Navigation target_type must be "
                "'resource' or 'storage'."
            )

    # --------------------------------------------------
    # 6. Validate resource type.
    # --------------------------------------------------

    if action_type in {"loot", "deposit", "withdraw"}:

        resource_type = action.get("resource_type")

        if (
            not isinstance(resource_type, str)
            or resource_type not in RESOURCE_TYPES
        ):
            return None, (
                f"Invalid resource type: {resource_type!r}"
            )

    # --------------------------------------------------
    # 7. Validate action amount.
    # --------------------------------------------------

    if action_type in DEFAULT_AMOUNTS:

        amount = action.get(
            "amount",
            DEFAULT_AMOUNTS[action_type],
        )

        if type(amount) is not int:
            return None, "Action amount must be an integer."

        if amount <= 0:
            return None, "Action amount must be positive."

        if amount > MAX_ACTION_AMOUNT:
            return None, (
                f"Action amount cannot exceed {MAX_ACTION_AMOUNT}."
            )

        action["amount"] = amount

    return action, None
