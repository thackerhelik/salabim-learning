from environment import loot_from_cache
from entities.loot_cache import LootCache
from island_survivors.explorers import Explorer


# Create an explorer adjacent to the cache.
ava = Explorer(
    name="Ava",
    row=4,
    col=4,
    color="#E76F51",
)

# Create a loot cache.
loot_caches = {
    (4, 5): LootCache(
        row=4,
        col=5,
        inventory={
            "wood": 5,
            "stone": 2,
            "berries": 3,
        },
    )
}

# Collect wood.
result = loot_from_cache(
    explorer=ava,
    loot_caches=loot_caches,
    target_position=(4, 5),
    resource_type="wood",
    amount=2,
)

print(result)
print("Ava's inventory:", ava.inventory)
print("Cache inventory:", loot_caches[(4, 5)].inventory)

# Collect all remaining resources.
loot_from_cache(ava, loot_caches, (4, 5), "wood", 3)
loot_from_cache(ava, loot_caches, (4, 5), "stone", 2)
loot_from_cache(ava, loot_caches, (4, 5), "berries", 3)

print("Ava's final inventory:", ava.inventory)
print("Remaining loot caches:", loot_caches)