from environment import create_resources, gather_resource
from island_survivors.explorers import Explorer


# Initialize resources
resources = create_resources()

# Create an explorer adjacent to a tree at (3, 5)
ava = Explorer(
    name="Ava",
    row=3,
    col=4,
    color="#E76F51",
)

# Gather wood
result = gather_resource(
    explorer=ava,
    resources=resources,
    target_position=(3, 5),
)

print(result)
print("Inventory:", ava.inventory)
print("Remaining tree quantity:", resources[(3, 5)].quantity)

# Test resource depletion
for _ in range(3):
    result = gather_resource(
        ava,
        resources,
        (3, 5),
    )

    print(result)

print("Final inventory:", ava.inventory)