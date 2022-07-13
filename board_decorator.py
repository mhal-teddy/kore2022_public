from collections import defaultdict
from copy import deepcopy
from functools import wraps
import numpy as np
from typing import Dict, List, Optional, Set
from board import Board
from configuration import Configuration
from cell import Field
from player import Player

class Info:
    def __init__(self, config: Configuration):
        self._allied_fleet_position = set()
        self._incoming_hostile_fleet_power = defaultdict(int)
        self._future_field: Dict[int, Field] = {}
        self._player_kore: Dict[int, Dict[str, float]] = {}
        self._shipyard_count: Dict[int, Dict[str, int]] = {}
        self._field_kore: Dict[int, float] = {}
        self._field_damage: Dict[int, np.ndarray] = {}
        self.config = config
    
    @property
    def total_turn(self) -> int:
        """calculation turn"""
        return len(self._future_field)
    
    def future_field(self, *, turn: int = -1) -> Optional[Field]:
        assert isinstance(turn, int), f"turn must be integer"
        try:
            return self._future_field[turn]
        except KeyError:
            return None
    
    def player_kore(self, *, turn: int = -1) -> Dict[str, float]:
        return self._player_kore[turn]
    
    def shipyard_count(self, *, turn: int = -1) -> Dict[str, int]:
        return self._shipyard_count[turn]
    
    def field_kore(self, *, turn: int = -1) -> float:
        """average kore"""
        return self._field_kore[turn]
    
    def field_damage(self, *, turn: int = -1) -> np.ndarray:
        return self._field_damage[turn]
    
    def add_future_field(self, board: Board, turn: int) -> None:
        self._future_field[turn] = deepcopy(board.field)
    
    def add_player_kore(self, board: Board, turn: int) -> None:
        self._player_kore[turn] = {}
        for player_id, player in board.players.items():
            self._player_kore[turn][player_id] = player.kore
    
    def add_shipyard_count(self, board: Board, turn: int) -> None:
        self._shipyard_count[turn] = {}
        for player_id, player in board.players.items():
            self._shipyard_count[turn][player_id] = len(player.shipyards)
        
    def add_field_kore(self, board: Board, turn: int) -> None:
        size = board.configuration.size
        kore = 0
        for x in range(size):
            for y in range(size):
                if board.field[x, y].shipyard is None:
                    kore += board.field[x, y].kore
        self._field_kore[turn] = kore / size / size
    
    def add_field_damage(self, board: Board, turn: int) -> None:
        size = board.configuration.size
        field = np.zeros((size, size), dtype=np.int8)

        for fleet in board.opponent_player.fleets:
            field[fleet.x, fleet.y] += fleet.ship_count
            for dx, dy in {(0, 1), (0, -1), (1, 0), (-1, 0)}:
                next_x, next_y = (fleet.x + dx) % size, (fleet.y + dy) % size
                field[next_x, next_y] += fleet.ship_count
        self._field_damage[turn] = field

def future_board(agent) -> Dict[str, str]:
    @wraps(agent)
    def wrapper(obs, config):
        board: Board = Board(obs, config)
        me: Player = board.current_player
        info: Info = Info(board.configuration)

        # calculate board after 20 turns
        for i, _board in enumerate(board.next()):
            if i > 0:
                info.add_future_field(_board, i)
                info.add_player_kore(_board, i)
                info.add_shipyard_count(_board, i)
                info.add_field_kore(_board, i)
                info.add_field_damage(_board, i)

            if i == 20:
                break
        
        agent(board, info)
        return me.next_actions
    return wrapper