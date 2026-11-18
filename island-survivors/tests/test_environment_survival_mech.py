from environment import update_survival_needs
from island_survivors.explorers import Explorer


ava = Explorer(
    name="Ava",
    row=3,
    col=8,
    color="#E76F51",
    hunger=90,
)

for i in range(11):

    result = update_survival_needs(ava)

    print(f"Update {i + 1}: {result}")