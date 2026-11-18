from entities.loot_cache import LootCache


print("----------- test 1 -------------")
cache = LootCache(
    row=4,
    col=5,
    inventory={
        "wood": 5,
        "stone": 2,
        "berries": 3,
    },
)

print("Initial inventory:", cache.inventory)

# Collect some wood.
collected = cache.collect("wood", 2)
print("Wood collected:", collected)

# Collect berries.
collected = cache.collect("berries", 1)
print("Berries collected:", collected)

print("Remaining inventory:", cache.inventory)
print("Is cache empty?", cache.is_empty)

print("----------- test 2 -------------")
# Test complete depletion
cache = LootCache(
    row=4,
    col=5,
    inventory={"berries": 2},
)

cache.collect("berries", 2)

print(cache.is_empty)  # True