from entities.loot_cache import LootCache

cache = LootCache(2, 3, {"wood": 2})

assert cache.collect("berries") == 0
assert cache.collect("wood", 1) == 1
assert cache.collect("wood", 5) == 1
assert cache.is_empty

print("LootCache tests passed.")