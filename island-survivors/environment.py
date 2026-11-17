from entities.resource import Resource
from island_survivors.map_data import FEATURES
from entities.loot_cache import LootCache


# Default quantities for collectible resources
RESOURCE_CONFIG = {
    "tree": {
        "resource_type": "wood",
        "quantity": 5,
    },
    "rock": {
        "resource_type": "stone",
        "quantity": 3,
    },
    "berry": {
        "resource_type": "berries",
        "quantity": 4,
    },
}


def create_resources():
    """Create resource objects from the predefined map features."""

    resources = {}

    for kind, row, col in FEATURES:

        # Skip features that cannot be collected
        if kind not in RESOURCE_CONFIG:
            continue

        config = RESOURCE_CONFIG[kind]

        resource = Resource(
            kind=kind,
            row=row,
            col=col,
            resource_type=config["resource_type"],
            quantity=config["quantity"],
        )

        # Use grid coordinates as dictionary keys
        resources[(row, col)] = resource

    return resources


def gather_resource(explorer, resources, target_position, amount=2):
    """Collect resources from a neighbouring resource object."""

    # Check whether explorer is alive
    if not explorer.is_alive:
        return {
            "success": False,
            "message": "Explorer is not alive.",
            "collected": 0,
        }

    if amount <= 0:
        raise ValueError("Collection amount must be positive.")

    # Check whether target is adjacent
    target_row, target_col = target_position

    distance = (
        abs(explorer.row - target_row)
        + abs(explorer.col - target_col)
    )

    if distance > 1:
        return {
            "success": False,
            "message": "Resource is not adjacent.",
            "collected": 0,
        }

    # Find resource
    resource = resources.get(target_position)

    if resource is None:
        return {
            "success": False,
            "message": "No resource at the target position.",
            "collected": 0,
        }

    # Check whether inventory supports this resource
    if resource.resource_type not in explorer.inventory:
        return {
            "success": False,
            "message": "Unknown inventory resource type.",
            "collected": 0,
        }

    # Collect resource
    collected = resource.collect(amount)

    if collected == 0:
        return {
            "success": False,
            "message": "Resource is depleted.",
            "collected": 0,
        }

    # Update explorer inventory
    explorer.inventory[resource.resource_type] += collected

    return {
        "success": True,
        "message": f"Collected {collected} {resource.resource_type}.",
        "collected": collected,
    }



def loot_from_cache(
    explorer,
    loot_caches,
    target_position,
    resource_type,
    amount=1,
):
    """Collect resources from a nearby loot cache."""

    if not explorer.is_alive:
        return {
            "success": False,
            "message": "Explorer is not alive.",
            "collected": 0,
        }

    if amount <= 0:
        raise ValueError("Collection amount must be positive.")

    # Check whether the cache is adjacent.
    target_row, target_col = target_position

    distance = (
        abs(explorer.row - target_row)
        + abs(explorer.col - target_col)
    )

    if distance > 1:
        return {
            "success": False,
            "message": "Loot cache is not adjacent.",
            "collected": 0,
        }

    # Find the loot cache.
    cache = loot_caches.get(target_position)

    if cache is None:
        return {
            "success": False,
            "message": "No loot cache at the target position.",
            "collected": 0,
        }

    # Check whether inventory supports this resource.
    if resource_type not in explorer.inventory:
        return {
            "success": False,
            "message": "Unknown inventory resource type.",
            "collected": 0,
        }

    # Collect the requested resource.
    collected = cache.collect(resource_type, amount)

    if collected == 0:
        return {
            "success": False,
            "message": f"No {resource_type} available in cache.",
            "collected": 0,
        }

    # Update explorer inventory.
    explorer.inventory[resource_type] += collected

    # Remove the cache once completely depleted.
    if cache.is_empty:
        del loot_caches[target_position]

    return {
        "success": True,
        "message": f"Collected {collected} {resource_type} from loot cache.",
        "collected": collected,
    }



HUNGER_REDUCTION_PER_BERRY = 25
MAX_HUNGER = 100
HUNGER_INCREASE_PER_UPDATE = 10
STARVATION_DAMAGE = 10


def eat_berries(explorer, amount=1):
    """Consume berries to reduce explorer hunger."""

    if not explorer.is_alive:
        return {
            "success": False,
            "message": "Explorer is not alive.",
            "consumed": 0,
        }

    if amount <= 0:
        raise ValueError("Eating amount must be positive.")

    if explorer.hunger <= 0:
        return {
            "success": False,
            "message": "Explorer is not hungry.",
            "consumed": 0,
        }

    available = explorer.inventory.get("berries", 0)

    if available <= 0:
        return {
            "success": False,
            "message": "No berries available.",
            "consumed": 0,
        }

    # Calculate how many berries are actually needed.
    needed = (
        explorer.hunger + HUNGER_REDUCTION_PER_BERRY - 1
    ) // HUNGER_REDUCTION_PER_BERRY

    consumed = min(amount, available, needed)

    # Update inventory and hunger.
    explorer.inventory["berries"] -= consumed

    hunger_reduction = consumed * HUNGER_REDUCTION_PER_BERRY

    explorer.hunger = max(
        0,
        explorer.hunger - hunger_reduction,
    )

    return {
        "success": True,
        "message": f"Consumed {consumed} berries.",
        "consumed": consumed,
        "hunger": explorer.hunger,
    }


def update_survival_needs(explorer):
    """Update hunger and health for an explorer."""

    if not explorer.is_alive:
        return

    # Increase hunger.
    explorer.hunger = min(
        MAX_HUNGER,
        explorer.hunger + HUNGER_INCREASE_PER_UPDATE,
    )

    health_lost = 0

    # Apply starvation damage.
    if explorer.hunger >= MAX_HUNGER:

        previous_health = explorer.health

        explorer.health = max(
            0,
            explorer.health - STARVATION_DAMAGE,
        )

        health_lost = previous_health - explorer.health

        # Mark explorer as dead.
        if explorer.health == 0:
            explorer.is_alive = False

    return {
        "hunger": explorer.hunger,
        "health": explorer.health,
        "health_lost": health_lost,
        "is_alive": explorer.is_alive,
    }


def get_observation(explorer, resources, loot_caches=None):
    """Generate an observation of the explorer's current situation."""

    nearby_resources = []

    nearby_loot_caches = []

    if loot_caches is not None:

        for position, cache in loot_caches.items():

            distance = (
                abs(explorer.row - cache.row)
                + abs(explorer.col - cache.col)
            )

            if distance <= 1 and not cache.is_empty:

                nearby_loot_caches.append({
                    "position": position,
                    "inventory": cache.inventory.copy(),
                })

    for position, resource in resources.items():

        distance = (
            abs(explorer.row - resource.row)
            + abs(explorer.col - resource.col)
        )

        # Consider resources on the current or adjacent tiles.
        if distance <= 1:

            nearby_resources.append({
                "kind": resource.kind,
                "resource_type": resource.resource_type,
                "position": position,
                "quantity": resource.quantity,
            })

    return {
        "name": explorer.name,
        "position": (explorer.row, explorer.col),
        "health": explorer.health,
        "hunger": explorer.hunger,
        "inventory": explorer.inventory.copy(),
        "is_alive": explorer.is_alive,
        "nearby_resources": nearby_resources,
        "nearby_loot_caches": nearby_loot_caches,
    }


def validate_storage_access(explorer, storage):
    """Validate whether an explorer can access team storage."""

    if not explorer.is_alive:
        return "Explorer is not alive."

    if explorer.team_id != storage.team_id:
        return "Explorer does not belong to this team."

    distance = (
        abs(explorer.row - storage.row)
        + abs(explorer.col - storage.col)
    )

    if distance > 1:
        return "Storage is not adjacent."

    return None



def deposit_to_storage(
    explorer,
    storage,
    resource_type,
    amount,
):
    """Deposit resources from an explorer into team storage."""

    error = validate_storage_access(explorer, storage)

    if error:
        return {
            "success": False,
            "message": error,
            "transferred": 0,
        }

    if amount <= 0:
        raise ValueError("Deposit amount must be positive.")

    if resource_type not in explorer.inventory:
        return {
            "success": False,
            "message": "Unknown inventory resource type.",
            "transferred": 0,
        }

    available = explorer.inventory[resource_type]

    deposited = min(amount, available)

    if deposited == 0:
        return {
            "success": False,
            "message": f"No {resource_type} available to deposit.",
            "transferred": 0,
        }

    # Add resources to shared storage.
    storage.deposit(resource_type, deposited)

    # Remove resources from explorer inventory.
    explorer.inventory[resource_type] -= deposited

    return {
        "success": True,
        "message": f"Deposited {deposited} {resource_type}.",
        "transferred": deposited,
    }


def withdraw_from_storage(
    explorer,
    storage,
    resource_type,
    amount,
):
    """Withdraw resources from team storage into an explorer's inventory."""

    error = validate_storage_access(explorer, storage)

    if error:
        return {
            "success": False,
            "message": error,
            "transferred": 0,
        }

    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive.")

    if resource_type not in explorer.inventory:
        return {
            "success": False,
            "message": "Unknown inventory resource type.",
            "transferred": 0,
        }

    # Withdraw available resources.
    withdrawn = storage.withdraw(resource_type, amount)

    if withdrawn == 0:
        return {
            "success": False,
            "message": f"No {resource_type} available in storage.",
            "transferred": 0,
        }

    # Update explorer inventory.
    explorer.inventory[resource_type] += withdrawn

    return {
        "success": True,
        "message": f"Withdrew {withdrawn} {resource_type}.",
        "transferred": withdrawn,
    }
