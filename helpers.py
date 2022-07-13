from collections import defaultdict
import math
from typing import Callable, Iterable, Optional, Tuple

def from_index(index: int, size: int) -> Tuple[int, int]:
    y, x = divmod(index, size)
    return (x, y)

def to_index(x: int, y: int, size: int) -> int:
    return (size - y - 1) * size + x

def max_ships_to_spawn(turns_controlled: int) -> int:
    upgrade_times = [pow(i,2) + 1 for i in range(1, 10)]
    spawn_values = []
    current = 0
    for t in upgrade_times:
        current += t
        spawn_values.append(current)

    for idx, target in enumerate(spawn_values):
        if turns_controlled < target:
            return idx + 1
    return len(spawn_values) + 1

def max_flight_plan_len_for_ship_count(ship_count: int) -> int:
    return math.floor(2 * math.log(ship_count) + 1)

def min_ship_count_for_flight_plan_len(flight_plan_len: int) -> int:
    return math.ceil(math.exp((flight_plan_len - 1) / 2))

def collection_rate_for_ship_count(ship_count: int) -> float:
    return min(math.log(ship_count) / 20, 0.99)

def create_spawn_ships_command(num_ships: int) -> str:
    return f"SPAWN_{num_ships}"

def create_launch_fleet_command(num_ships: int, plan: str) -> str:
    return f"LAUNCH_{num_ships}_{plan}"

def is_valid_flight_plan(flight_plan: str) -> bool:
    return len([c for c in flight_plan if c not in "NESW0123456789"]) == 0

def group_by(items: Iterable, selector: Callable) -> dict:
    results = defaultdict(list)
    for item in items:
        key = selector(item)
        results[key].append(item)
    return results

class cached_property:
    def __init__(self, func):
        self.func = func
        self.key = "__" + func.__name__
    
    def __get__(self, instance, owner):
        try:
            return instance.__getattribute__(self.key)
        except AttributeError:
            value = self.func(instance)
            instance.__setattr__(self.key, value)
            return value