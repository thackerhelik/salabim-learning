from island_survivors.explorers import Explorer
from entities.team_storage import TeamStorage

from environment import (
    deposit_to_storage,
    withdraw_from_storage,
)


# Create two teammates.
ava = Explorer(
    name="Ava",
    row=6,
    col=6,
    color="#E76F51",
    team_id=1,
)

bram = Explorer(
    name="Bram",
    row=6,
    col=8,
    color="#457BCE",
    team_id=1,
)

# Create Team 1 storage at the chest (6, 7).
storage = TeamStorage(
    team_id=1,
    row=6,
    col=7,
)

# Ava starts with resources.
ava.inventory["wood"] = 5
ava.inventory["berries"] = 4


print("---------- INITIAL STATE ----------")
print("Ava:", ava.inventory)
print("Bram:", bram.inventory)
print("Storage:", storage.inventory)


# Ava deposits resources.
print("\n---------- AVA DEPOSITS ----------")

result = deposit_to_storage(
    ava,
    storage,
    "wood",
    3,
)
print(result)

result = deposit_to_storage(
    ava,
    storage,
    "berries",
    4,
)
print(result)


print("\nAva:", ava.inventory)
print("Storage:", storage.inventory)


# Bram withdraws resources.
print("\n---------- BRAM WITHDRAWS ----------")

result = withdraw_from_storage(
    bram,
    storage,
    "berries",
    2,
)
print(result)

print("\nBram:", bram.inventory)
print("Storage:", storage.inventory)


cleo = Explorer(
    name="Cleo",
    row=6,
    col=6,
    color="#E9C74B",
    team_id=2,
)

result = withdraw_from_storage(
    cleo,
    storage,
    "berries",
    1,
)

print(result)