# Fleet と Shipyard

from typing import List, Optional, Tuple, Union
from action import Action
from configuration import Configuration
from point import Direction, Point
from helpers import max_ships_to_spawn

class Fleet:
    def __init__(self, 
            fleet_id: str, 
            player_id: str, 
            x: int, 
            y: int, 
            fleet_kore: float, 
            ship_count: int, 
            direction: str, 
            flight_plan: str,
            config: Configuration
    ):
        self._point = Point(x, y, config.size)
        self._fleet_id = fleet_id
        self._player_id = player_id
        self._fleet_kore = fleet_kore
        self._ship_count = ship_count
        self._direction = direction
        self._flight_plan = flight_plan
        self._config = config
        self._route = []
        self._expected_kore = 0
        self.convert_attack = []

        assert direction in ["N", "E", "S", "W"], f"{direction} is invalid direction"
        assert len([c for c in flight_plan if c not in "NESWC0123456789"]) == 0, f"{flight_plan} is invalid"

    @property
    def id(self) -> str:
        return self._fleet_id
    
    @property
    def point(self) -> Point:
        return self._point
    
    @property
    def x(self) -> int:
        return self._point.x
    
    @property
    def y(self) -> int:
        return self._point.y
    
    @property
    def player_id(self) -> str:
        return self._player_id

    @property
    def kore(self) -> float:
        return self._fleet_kore
    
    @property
    def ship_count(self) -> int:
        return self._ship_count
    
    @property
    def direction(self) -> str:
        return self._direction
    
    @property
    def flight_plan(self) -> str:
        return self._flight_plan
    
    @property
    def route(self) -> List[Point]:
        return self._route
    
    @property
    def expected_kore(self) -> float:
        return self._expected_kore + self.kore
    
    def move(self, direction: str) -> None:
        assert direction in {"N", "E", "S", "W"}, f"{direction} is invalid."
        dx, dy = Direction.next_position(direction)

        self._point = Point(self.x + dx, self.y + dy, self._config.size)
    
    def __repr__(self):
        return f"Fleet(id={self.id}, player_id={self.player_id}, " \
            f"(x, y)=({self.x}, {self.y}), direction={self.direction})"

class Shipyard:
    def __init__(self, 
            shipyard_id: str, 
            player_id: str, 
            x: int, 
            y: int, 
            ship_count: int, 
            turns_controlled: int, 
            config: Configuration
    ):
        self._point = Point(x, y, config.size)
        self._shipyard_id = shipyard_id
        self._player_id = player_id
        self._ship_count = ship_count
        self._turns_controlled = turns_controlled
        self._next_action: Optional[Action] = None
        self._config = config
        self._guard_ship_count = 0
        self.guard_turn = 100
        self.expected_guard = 0
        self.incoming_allied_fleets = []
        self.incoming_hostile_fleets = []
        self.need_ship_count = 0
        self.capacity = []

    @property
    def id(self) -> str:
        return self._shipyard_id
    
    @property
    def point(self) -> Point:
        return self._point
    
    @property
    def x(self) -> int:
        return self._point.x
    
    @property
    def y(self) -> int:
        return self._point.y
    
    @property
    def player_id(self) -> str:
        return self._player_id

    @property
    def ship_count(self) -> int:
        return self._ship_count
    
    @property
    def guard_ship_count(self) -> int:
        return self._guard_ship_count
    
    @guard_ship_count.setter
    def guard_ship_count(self, ship_count: int) -> int:
        if ship_count > self._ship_count:
            ship_count = self._ship_count
            self.need_ship_count = ship_count - self._ship_count
        elif ship_count < 0:
            ship_count = 0
        self._guard_ship_count = ship_count
    
    @property
    def available_ship_count(self) -> int:
        return max(self._ship_count - self._guard_ship_count - self.expected_guard, 0)

    @property
    def turns_controlled(self) -> int:
        return self._turns_controlled

    @property
    def max_spawn(self) -> float:
        return max_ships_to_spawn(self._turns_controlled)

    @property
    def next_action(self) -> Optional[Action]:
        return self._next_action

    @next_action.setter
    def next_action(self, action: str) -> None:
        self._next_action = action
    
    def spawn_as_many_ships(self, player_kore: Union[int, float]) -> int:
        assert isinstance(player_kore, (int, float)), "Kore must be numeric."
        spawn_cost = self._config.spawn_cost
        if player_kore > spawn_cost * self.max_spawn:
            return self.max_spawn
        else:
            return int(player_kore // spawn_cost)
    
    def future_spawn(self, kore: Union[int, float], turn: int) -> Tuple[int, float]:
        spawn_cost = self._config.spawn_cost
        max_spawn = max_ships_to_spawn(self.turns_controlled + turn)
        if kore >= spawn_cost * max_spawn:
            return max_spawn, spawn_cost * max_spawn
        else:
            num_ships = kore // spawn_cost
            return num_ships, num_ships * spawn_cost
    
    def __repr__(self):
        if self._next_action is not None:
            return f"Shipyard(id={self.id}, player_id={self.player_id}, " \
                f"(x, y)=({self.x}, {self.y}), next_action={self.next_action.command})"
        else:
            return f"Shipyard(id={self.id}, player_id={self.player_id}, " \
                f"(x, y)=({self.x}, {self.y}), next_action=None)"