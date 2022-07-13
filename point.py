from enum import Enum
from typing import Tuple, List

class Direction(Enum):
    """
    ex) Direction(0).name = 'N'
    ex) Direction['N'].value = 0
    """
    N = 0
    E = 1
    S = 2
    W = 3
    
    @classmethod
    def next_position(cls, direction: str) -> Tuple[int, int]:
        if direction == "N":
            dx, dy = 0, -1
        elif direction == "E":
            dx, dy = 1, 0
        elif direction == "S":
            dx, dy = 0, 1
        elif direction == "W":
            dx, dy = -1, 0
        else:
            raise ValueError("invalid")
        return dx, dy
    
    @classmethod
    def opposite(cls, direction: str) -> str:
        assert direction in "NESW"
        if direction == "N":
            return "S"
        elif direction == "E":
            return "W"
        elif direction == "S":
            return "N"
        else:
            return "E"
    
    @classmethod
    def list_directions(cls) -> List:
        return [cls.N,cls.E,cls.S,cls.W]

class Point:
    def __init__(self, x: int, y: int, size: int):
        self._x = x % size
        self._y = y % size
        self._size = size
    
    @property
    def x(self) -> int:
        return self._x
    
    @property
    def y(self) -> int:
        return self._y
    
    def to_tuple(self) -> Tuple[int, int]:
        return self._x, self._y

    @property
    def adjacent_point(self) -> List["Point"]:
        points = []
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            points.append(Point(self.x + dx, self.y + dy, self._size))
        return points
    
    def __eq__(self, point: "Point"):
        if not isinstance(point, Point):
            return False
        return self.x == point.x and self.y == point.y
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def distance(self, point: "Point") -> int:
        dx = min(abs(self.x - point.x), min(self.x, point.x) + self._size - max(self.x, point.x))
        dy = min(abs(self.y - point.y), min(self.y, point.y) + self._size - max(self.y, point.y))
        return dx + dy
    
    def __repr__(self):
        return f"(x={self.x}, y={self.y})"