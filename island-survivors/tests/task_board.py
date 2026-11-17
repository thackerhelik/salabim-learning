from entities.team_task_board import TeamTaskBoard


board = TeamTaskBoard(team_id=1)

# Dax claims the berry bush.
result = board.claim_resource(
    position=(4, 5),
    explorer_name="Dax",
    current_time=10,
)

print("Dax claim:", result)


# Bram tries to claim the same resource.
result = board.claim_resource(
    position=(4, 5),
    explorer_name="Bram",
    current_time=10,
)

print("Bram claim:", result)


# Cleo claims a different resource.
result = board.claim_resource(
    position=(3, 5),
    explorer_name="Cleo",
    current_time=10,
)

print("Cleo claim:", result)


# Check whether the resource is claimed by someone else.
print(
    "Berries claimed by someone else:",
    board.is_claimed_by_other(
        (4, 5),
        "Bram",
        10,
    ),
)


# Dax finishes the task.
board.release_resource((4, 5), "Dax")


# Bram can now claim the berry bush.
result = board.claim_resource(
    position=(4, 5),
    explorer_name="Bram",
    current_time=12,
)

print("Bram claim after release:", result)

print("Remaining assignments:", board.resource_claims)