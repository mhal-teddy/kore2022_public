from typing import Generator, List, Optional, Tuple
from point import Direction, Point
from piece import Fleet, Shipyard
from helpers import cached_property

class Cell:
    def __init__(self, x: int, y: int, kore: float, shipyard: Optional[Shipyard], fleet: Optional[Fleet], size: int):
        self._point = Point(x, y, size)
        self._kore = kore
        self._shipyard = shipyard
        self._fleet = fleet
        self._adjacent_fleets = []
    
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
    def kore(self) -> float:
        return self._kore
    
    @property
    def shipyard(self) -> Optional[Shipyard]:
        return self._shipyard
    
    @property
    def fleet(self) -> Optional[Fleet]:
        return self._fleet
    
    @property
    def adjacent_fleets(self) -> List[Fleet]:
        return self._adjacent_fleets
    
    def damage(self, player_id: int, destroyed: set) -> int:
        dmg = 0
        attack = set()
        if (self.fleet is not None) and (self.fleet.player_id != player_id) and (self.fleet.id not in destroyed):
            dmg += self.fleet.ship_count
            attack.add(self.fleet.id)
        
        for fleet in self._adjacent_fleets:
            if fleet.player_id != player_id and fleet.id not in destroyed:
                dmg += fleet.ship_count
                attack.add(fleet.id)
        return dmg, attack
    
    def __repr__(self):
        if self._shipyard and self._fleet:
            return f"Cell(x={self.x}, y={self.y}, " \
                f"shipyard_id={self._shipyard.id}, fleet_id={self._fleet.id})"
        elif self._shipyard:
            return f"Cell(x={self.x}, y={self.y}, shipyard_id={self._shipyard.id})"
        elif self._fleet:
            return f"Cell(x={self.x}, y={self.y}, fleet_id={self._fleet.id})"
        else:
            return f"Cell(x={self.x}, y={self.y}, kore={self._kore})"

class Field:
    def __init__(self, size: int):
        self._size = size
        self._shipyards: List[Shipyard] = []
        self._fleets: List[Fleet] = []

        self._position = [[None] * size for _ in range(size)]
        for x in range(size):
            for y in range(size):
                self._position[x][y] = Cell(x, y, 0, None, None, size)
    
    def __getitem__(self, item) -> Cell:
        x, y = item
        return self._position[(x % self._size)][(y % self._size)]
    
    @property
    def size(self) -> int:
        return self._size
    
    def surrounding_cells(self, point: Point, start: int, stop: int, step: int = 1) -> Generator[Cell, None, None]:
        assert start >= 1
        for r in range(start, stop, step):
            for dx in range(r):
                dy = r - abs(dx)
                # 90 degree rotation
                yield self[point.x + dx, point.y + dy]

                dx, dy = -dy, dx
                yield self[point.x + dx, point.y + dy]

                dx, dy = -dy, dx
                yield self[point.x + dx, point.y + dy]

                dx, dy = -dy, dx
                yield self[point.x + dx, point.y + dy]
    
    def cells_away(self, point: Point, distance: int) -> Generator[Cell, None, None]:
        assert int(distance) > 0, "distance must be positive"
        for dx in range(distance):
            dy = distance - abs(dx)
            # 90 degree rotation
            yield self[point.x + dx, point.y + dy]

            dx, dy = -dy, dx
            yield self[point.x + dx, point.y + dy]

            dx, dy = -dy, dx
            yield self[point.x + dx, point.y + dy]

            dx, dy = -dy, dx
            yield self[point.x + dx, point.y + dy]
    
    def closest_shipyard(self, point: Point, player_id: Optional[int]) -> Optional[Shipyard]:
        assert player_id is None or player_id in {0, 1}, "player_id is invalid"
        here = self[point.to_tuple()]
        target = {"shipyard": None, "distance": self._size}

        for shipyard in self._shipyards:
            distance = here.point.distance(shipyard.point)
            if distance == 0:
                continue

            if distance < target["distance"]:
                if player_id is None:
                    target["shipyard"] = shipyard
                    target["distance"] = distance
                elif shipyard.player_id == player_id:
                    target["shipyard"] = shipyard
                    target["distance"] = distance

        return target["shipyard"]
    
    def closest_distance(self, point: Point, player_id: Optional[int]) -> Optional[int]:
        assert player_id is None or player_id in {0, 1}, "player_id is invalid"
        here = self[point.to_tuple()]
        target = {"shipyard": None, "distance": self._size}

        for shipyard in self._shipyards:
            distance = here.point.distance(shipyard.point)
            if distance == 0:
                continue

            if distance < target["distance"]:
                if player_id is None:
                    target["shipyard"] = shipyard
                    target["distance"] = distance
                elif shipyard.player_id == player_id:
                    target["shipyard"] = shipyard
                    target["distance"] = distance

        return target["distance"]
    
    def closest_fleet(self, point: Point, player_id: Optional[int]) -> Optional[Fleet]:
        assert player_id is None or player_id in {0, 1}, "player_id is invalid"
        here = self[point.to_tuple()]
        target = {"fleet": None, "distance": self._size}

        for fleet in self._fleets:
            distance = here.point.distance(fleet.point)
            if distance == 0:
                continue
            
            if distance < target["distance"]:
                if player_id is None:
                    target["fleet"] = fleet
                    target["distance"] = distance
                elif fleet.player_id == player_id:
                    target["fleet"] = fleet
                    target["distance"] = distance

        return target["fleet"]
    
    def surrounding_kore(self, point: Point, player_id: int, max_distance=5) -> Tuple[float, int]:
        total = 0
        num_ships = 0
        for cell in self.surrounding_cells(point, 1, max_distance + 1):
            if cell.shipyard is None:
                total += cell.kore
            elif cell.shipyard is not None and cell.shipyard.player_id != player_id:
                num_ships += cell.shipyard.ship_count
        return total, num_ships

class Route:
    def __init__(self, route_cell: List[Point], is_convert: bool):
        self._route_cell = route_cell
        self._is_convert = is_convert
    
    def __iter__(self):
        return self._route_cell.__iter__()
    
    def __len__(self):
        return len(self._route_cell)
    
    @property
    def route_cell(self) -> List[Point]:
        return self._route_cell

    @property
    def end(self) -> Tuple[int, int]:
        return self._route_cell[-1]
    
    @property
    def time(self) -> int:
        return max(len(self._route_cell) - 1, 0)
    
    @property
    def is_convert(self) -> bool:
        return self._is_convert

    @classmethod
    def from_str(cls, point: Point, field: Field, flight_plan: str, direction: Optional[str]) -> "Route":

        def find_first_non_digit(flight_plan: str):
            for i in range(len(flight_plan)):
                if not flight_plan[i].isdigit():
                    return i
            return len(flight_plan) + 1

        _flight_plan = flight_plan[:]
        size = field.size
        is_convert = False

        dx, dy = 0, 0
        if direction is not None:
            if not _flight_plan or (_flight_plan and _flight_plan[0].isdigit()):
                dx, dy = Direction.next_position(direction)

        route_cell = [point]
        empty_counter = 0
        count = 0
        while True:
            x, y = route_cell[-1].x, route_cell[-1].y

            # continue to move
            if not _flight_plan:
                next_point = Point(x + dx, y + dy, size)
                empty_counter += 1

            if _flight_plan and _flight_plan[0] == "0":
                _flight_plan = _flight_plan[1:]
                continue
            elif _flight_plan and _flight_plan[0] == "C":
                is_convert = True
                break

            # change direction
            if _flight_plan and _flight_plan[0].isalpha():
                direction = _flight_plan[0]
                dx, dy = Direction.next_position(direction)
                next_point = Point(x + dx, y + dy, size)
                _flight_plan = _flight_plan[1:]
            
            # continue to move
            elif _flight_plan and _flight_plan[0].isdigit():
                idx = find_first_non_digit(_flight_plan)
                digits = int(_flight_plan[:idx]) - 1
                next_point = Point(x + dx, y + dy, size)
                _flight_plan = str(digits) + _flight_plan[idx:]
            
            route_cell.append(next_point)

            if not _flight_plan:
                empty_counter += 1
            if empty_counter >= size:
                break
            if len(route_cell) > 1 and field[next_point.to_tuple()].shipyard is not None:
                break
            
            if count == 100:
                raise RuntimeError("loop")
            count += 1
        return cls(route_cell, is_convert)
    
    def __repr__(self):
        return f"Route(len={len(self)}, {[(point.x, point.y) for point in self.route_cell]})"