from environment import create_resources, gather_resource, eat_berries
from island_survivors.explorers import Explorer


resources = create_resources()

ava = Explorer(
    name="Ava",
    row=4,
    col=4,
    color="#E76F51",
)

# Simulate hunger.
ava.hunger = 60

# Gather berries from the adjacent bush.
result = gather_resource(
    ava,
    resources,
    (4, 5),
)

print(result)
print("Inventory:", ava.inventory)

# Eat one berry.
result = eat_berries(ava)

print(result)
print("Inventory:", ava.inventory)