from typing import Dict, List
from configuration import Configuration
from piece import Fleet, Shipyard
from helpers import cached_property

class Player:
    def __init__(
            self, 
            player_id: int, 
            player_kore: float, 
            shipyards: Dict[str, List[Shipyard]], 
            fleets: Dict[str, List[Fleet]], 
            config: Configuration
    ):
        self._player_id = player_id
        self._kore = player_kore
        self._shipyards = shipyards
        self._fleets = fleets
        self._config = config
        self.need_shipyard = 0
        self.counter = False

    @property
    def player_id(self) -> int:
        return self._player_id

    @property
    def kore(self) -> float:
        return self._kore

    @cached_property
    def shipyards(self) -> List[Shipyard]:
        return self._shipyards.values()
    
    @cached_property
    def fleets(self) -> List[Fleet]:
        return self._fleets.values()
    
    @cached_property
    def total_kore(self) -> float:
        fleet_kore = sum(fleet.kore for fleet in self.fleets)
        return self.kore + fleet_kore
    
    @cached_property
    def total_ship_count(self) -> int:
        total = sum(fleet.ship_count for fleet in self.fleets)
        total += sum(shipyard.ship_count for shipyard in self.shipyards)
        for fleet in self.fleets:
            if fleet.route.is_convert:
                total -= self._config.convert_cost
        return total
    
    def spawn_ship_count(self) -> int:
        return sum(
            sy.next_action.num_ships 
            for sy in self.shipyards 
            if sy.next_action is not None and sy.next_action.action_type == "SPAWN"
        )
    
    def available_kore(self) -> int:
        return self.kore - self._config.spawn_cost * self.spawn_ship_count()
    
    def expected_ship_count(self) -> int:
        total = sum(fleet.ship_count for fleet in self.fleets if not fleet.route.is_convert)
        total += sum(sy.ship_count for sy in self.shipyards)
        kore = self.kore + sum(fleet.expected_kore for fleet in self.fleets if not fleet.route.is_convert)
        total += kore // self._config.spawn_cost
        return total

    @property
    def next_actions(self) -> dict:
        return {
            shipyard.id: shipyard.next_action.command
            for shipyard in self.shipyards
            if shipyard.next_action is not None
        }
    
    def __repr__(self):
        return f"Player(player_id={self.player_id}, kore={self.kore}, " \
                f"shipyards={self._shipyards.keys()}, fleets={self._fleets.keys()})"