from collections import defaultdict
from copy import deepcopy
from typing import Generator, Dict, List, Optional, Tuple
from cell import Field, Route
from configuration import Configuration
from piece import Fleet, Shipyard
from point import Direction
from player import Player
from helpers import (
    max_flight_plan_len_for_ship_count, 
    collection_rate_for_ship_count, 
    from_index, 
    to_index, 
    is_valid_flight_plan, 
    group_by
)

class Board:
    def __init__(self, obs, config):
        self._config = Configuration(config)
        self._obs = obs
        self._players = {}
        self._shipyards = {}
        self._fleets = {}
        self._step = obs["step"]

        size = self._config.size
        
        self._field = Field(size)
        for i in range(size ** 2):
            x, y = from_index(i, size)
            self._field[x, y]._kore = obs["kore"][i]

        for player_id, player_observation in enumerate(obs["players"]):
            # ex) player_observation = [500, {'0-1': [110, 0, 0]}, {}]
            player_kore, player_shipyards, player_fleets = player_observation

            self._players[player_id] = Player(player_id, player_kore, {}, {}, self.configuration)

            for shipyard_id, [shipyard_index, ship_count, turns_controlled] in player_shipyards.items():
                x, y = from_index(shipyard_index, size)
                self._add_shipyard(Shipyard(shipyard_id, player_id, x, y, ship_count, turns_controlled, self._config))

            for fleet_id, [fleet_index, fleet_kore, ship_count, direction, flight_plan] in player_fleets.items():
                x, y = from_index(fleet_index, size)
                self._add_fleet(Fleet(fleet_id, player_id, x, y, fleet_kore, ship_count, 
                                Direction(direction).name, flight_plan, self._config))
        
        self._field._shipyards = list(self._shipyards.values())
        self._field._fleets = list(self._fleets.values())

        # fleet route
        for fleet in self.fleets.values():
            fleet._route = Route.from_str(fleet.point, self.field, fleet.flight_plan, fleet.direction)
        
        # fleet to convert
        convert_point = []
        for fleet in self.fleets.values():
            if fleet.route.is_convert:
                convert_point.append({"point": fleet.route.end, "turn": fleet.route.time + 1, "fleet": fleet})
        
        for c in convert_point:
            for fleet in self.fleets.values():
                if c["point"] in fleet.route.route_cell:
                    turn = fleet.route.route_cell.index(c["point"])
                    
                    if turn >= c["turn"]:
                        c["fleet"].convert_attack.append(fleet)
        
        for shipyard in self.shipyards.values():
            for fleet in self.fleets.values():
                if shipyard.player_id == fleet.player_id and shipyard.point == fleet.route.end:
                    shipyard.incoming_allied_fleets.append(fleet)
                elif shipyard.player_id != fleet.player_id and shipyard.point == fleet.route.end:
                    shipyard.incoming_hostile_fleets.append(fleet)
        
        # expected kore
        for fleet in self.fleets.values():
            for i, point in enumerate(fleet.route):
                if i == 0 or i == fleet.route.time:
                    continue
                fleet._expected_kore += self.field[point.to_tuple()].kore * (1.02**(i-1))

    @property
    def configuration(self):
        return self._config

    @property
    def step(self) -> int:
        return self._step
    
    @property
    def steps_left(self) -> int:
        return 400 - self._step

    @property
    def players(self) -> Dict[str, Player]:
        return self._players
    
    @property
    def current_player(self) -> Player:
        player_id = self._obs["player"]
        return self._players[player_id]
    
    @property
    def opponent_player(self) -> Player:
        opponent_id = 1 if self._obs["player"] == 0 else 0
        return self._players[opponent_id]

    @property
    def shipyards(self) -> Dict[str, Shipyard]:
        return self._shipyards
    
    @property
    def fleets(self) -> Dict[str, Fleet]:
        return self._fleets
    
    @property
    def field(self) -> Field:
        return self._field
    
    def sort_player_shipyards(self) -> None:
        """sort shipyards by distance"""
        me = self.current_player
        
        distance = {}
        for shipyard in me.shipyards:
            closest = self.field.closest_shipyard(shipyard.point, self.opponent_player.player_id)
            if closest is None:
                distance[shipyard.id] = 100
            else:
                distance[shipyard.id] = closest.point.distance(shipyard.point)
        
        # overwrite
        self._players[me.player_id]._shipyards = sorted([sy for sy in me.shipyards], key=lambda x: distance[x.id])

    def _add_shipyard(self, shipyard: Shipyard) -> None:
        self._shipyards[shipyard.id] = shipyard
        self._players[shipyard.player_id]._shipyards[shipyard.id] = shipyard
        self._field[shipyard.point.to_tuple()]._shipyard = shipyard
    
    def _add_fleet(self, fleet: Fleet) -> None:
        self._fleets[fleet.id] = fleet
        self._players[fleet.player_id]._fleets[fleet.id] = fleet
        self._field[fleet.point.to_tuple()]._fleet = fleet

    def _delete_shipyard(self, shipyard: Shipyard) -> None:
        self._shipyards.pop(shipyard.id)
        self._players[shipyard.player_id]._shipyards.pop(shipyard.id)

        shipyard_cell = self._field[shipyard.point.to_tuple()]._shipyard
        if shipyard_cell is not None and shipyard_cell.id == shipyard.id:
            self._field[shipyard.point.to_tuple()]._shipyard = None

    def _delete_fleet(self, fleet: Fleet) -> None:
        self._fleets.pop(fleet.id)
        self._players[fleet.player_id]._fleets.pop(fleet.id)

        fleet_cell = self._field[fleet.point.to_tuple()]._fleet
        if fleet_cell is not None and fleet_cell.id == fleet.id:
            self._field[fleet.point.to_tuple()]._fleet = None
    
    def next(self) -> Generator["Board", None, None]:
        board = deepcopy(self)
        convert_cost = board.configuration.convert_cost
        spawn_cost = board.configuration.spawn_cost
        size = board.configuration.size

        # current board
        yield board

        while True:
            uid_counter = 0
            def create_uid():
                nonlocal uid_counter
                uid_counter += 1
                return f"{self.step + 1}-{uid_counter}"
            
            def find_first_non_digit(flight_plan: str):
                for i in range(len(flight_plan)):
                    if not flight_plan[i].isdigit():
                        return i
                return len(flight_plan) + 1
            
            for i in range(size ** 2):
                x, y = from_index(i, size)
                board._field[x, y]._adjacent_fleets.clear()

            for player in board.players.values():
                # Shipyard action
                for shipyard in player.shipyards:
                    if shipyard.next_action is None or shipyard.ship_count == 0:
                        pass
                    # Spawn ships
                    elif (shipyard.next_action.action_type == "SPAWN"
                            and player.kore >= spawn_cost * shipyard.next_action.num_ships
                            and shipyard.next_action.num_ships <= shipyard.max_spawn):
                        player._kore -= spawn_cost * shipyard.next_action.num_ships
                        shipyard._ship_count += shipyard.next_action.num_ships

                    # Launch
                    elif (shipyard.next_action.action_type == "LAUNCH"
                            and shipyard.ship_count >= shipyard.next_action.num_ships):
                        shipyard._ship_count -= shipyard.next_action.num_ships
                        flight_plan = shipyard.next_action.flight_plan
                        if not flight_plan or not is_valid_flight_plan(flight_plan):
                            continue
                        max_flight_plan_len = max_flight_plan_len_for_ship_count(shipyard.next_action.num_ships)
                        if len(flight_plan) > max_flight_plan_len:
                            flight_plan = flight_plan[:max_flight_plan_len]
                        board._add_fleet(Fleet(create_uid(), player.player_id, shipyard.x, shipyard.y, 0, 
                                            shipyard.next_action.num_ships, flight_plan[0], flight_plan, board.configuration))

                # Clear the shipyard's action
                for shipyard in player.shipyards:
                    shipyard.next_action = None
                    shipyard._turns_controlled += 1
                
                for fleet in list(player.fleets):
                    while fleet.flight_plan and fleet.flight_plan[0] == "0":
                        fleet._flight_plan = fleet.flight_plan[1:]
                    
                    # convert
                    if (fleet.flight_plan 
                            and fleet.flight_plan[0] == "C" 
                            and fleet.ship_count >= convert_cost 
                            and board._field[fleet.point.to_tuple()].shipyard is None):
                        player._kore += fleet.kore
                        board._field[fleet.point.to_tuple()]._kore = 0
                        new_shipyard = Shipyard(create_uid(), fleet.player_id, fleet.x, fleet.y, fleet.ship_count - convert_cost, 0, board.configuration)
                        board._add_shipyard(new_shipyard)
                        board._delete_fleet(fleet)
                        continue

                    while fleet.flight_plan and fleet.flight_plan[0] == "C":
                        fleet._flight_plan = fleet.flight_plan[1:]
                    
                    # move
                    if fleet.flight_plan and fleet.flight_plan[0].isalpha():
                        fleet._direction = fleet.flight_plan[0]
                        fleet._flight_plan = fleet.flight_plan[1:]
                    elif fleet.flight_plan:
                        idx = find_first_non_digit(fleet.flight_plan)
                        digits = int(fleet.flight_plan[:idx])
                        digits -= 1
                        if digits > 0:
                            fleet._flight_plan = str(digits) + fleet.flight_plan[idx:]
                        else:
                            fleet._flight_plan = fleet.flight_plan[idx:]
                    
                    board._field[fleet.point.to_tuple()]._fleet = None
                    fleet.move(fleet.direction)

                def combine_fleets(fleet1: Fleet, fleet2: Fleet) -> None:
                    fleet1._fleet_kore += fleet2.kore
                    fleet1._ship_count += fleet2.ship_count
                    board._delete_fleet(fleet2)

                fleets_by_loc = group_by(player.fleets, lambda fleet: to_index(fleet.x, fleet.y, size))
                for value in fleets_by_loc.values():
                    value.sort(key=lambda fleet: 
                        (fleet.ship_count, fleet.kore, -to_index(fleet.x, fleet.y, size)), reverse=True)
                    winner = value[0]
                    for i in range(1, len(value)):
                        combine_fleets(winner, value[i])
                    board._field[winner.point.to_tuple()]._fleet = winner
                
            def resolve_collision(fleets: List[Fleet]) -> Tuple[Optional[Fleet], List[Fleet]]:
                if len(fleets) == 1:
                    return fleets[0], []
                fleets_by_ship = group_by(fleets, lambda fleet: fleet.ship_count)
                largest_fleets = fleets_by_ship[max(fleets_by_ship.keys())]
                if len(largest_fleets) == 1:
                    winner = largest_fleets[0]
                    return winner, [fleet for fleet in fleets if fleet != winner]
                return None, fleets

            fleet_collision_groups = group_by(board.fleets.values(), lambda fleet: to_index(fleet.x, fleet.y, size))
            for position, collied_fleets in fleet_collision_groups.items():
                winner, deleted = resolve_collision(collied_fleets)
                x, y = from_index(position, size)
                shipyard = board._field[x, y]._shipyard
                if winner is not None:
                    max_enemy_size = max([fleet.ship_count for fleet in deleted]) if deleted else 0
                    winner._ship_count -= max_enemy_size
                    board._field[winner.point.to_tuple()]._fleet = winner
                for fleet in deleted:
                    board._delete_fleet(fleet)
                    if winner is not None:
                        winner._fleet_kore += fleet._fleet_kore
                    elif winner is None and shipyard is not None:
                        board.players[shipyard.player_id]._kore += fleet._fleet_kore
                    else:
                        board._field[fleet.point.to_tuple()]._kore += fleet.kore
            
            for shipyard in list(board.shipyards.values()):
                fleet = None
                for _fleet in board.fleets.values():
                    if shipyard.x == _fleet.x and shipyard.y == _fleet.y:
                        fleet = _fleet
                if fleet is not None and fleet.player_id != shipyard.player_id:
                    if fleet.ship_count > shipyard.ship_count:
                        count = fleet.ship_count - shipyard.ship_count
                        board._delete_shipyard(shipyard)
                        board._add_shipyard(Shipyard(create_uid(), fleet.player_id, 
                                            fleet.x, fleet.y, count, 1, board.configuration))
                        board.players[fleet.player_id]._kore += fleet.kore
                        board._delete_fleet(fleet)
                    else:
                        shipyard._ship_count -= fleet.ship_count
                        board.players[shipyard.player_id]._kore -= fleet.kore
                        board._delete_fleet(fleet)

                if fleet is not None and fleet.player_id == shipyard.player_id:
                    board.players[shipyard.player_id]._kore += fleet.kore
                    shipyard._ship_count += fleet.ship_count
                    board._delete_fleet(fleet)

            for fleet in board.fleets.values():
                for point in fleet.point.adjacent_point:
                    board.field[point.to_tuple()]._adjacent_fleets.append(fleet)

            incoming_fleet_dmg = defaultdict(lambda: defaultdict(int))
            for fleet in board.fleets.values():
                for direction in {"N", "E", "S", "W"}:
                    dx, dy = Direction.next_position(direction)
                    adjacent_fleet = board._field[fleet.x + dx, fleet.y + dy].fleet
                    if adjacent_fleet is not None and adjacent_fleet.player_id != fleet.player_id:
                        incoming_fleet_dmg[adjacent_fleet.id][fleet.id] = fleet.ship_count
            
            to_distribute = defaultdict(lambda: defaultdict(int))
            for fleet_id, fleet_dmg_dict in incoming_fleet_dmg.items():
                fleet = board.fleets[fleet_id]
                damage = sum(fleet_dmg_dict.values())
                if damage >= fleet.ship_count:
                    board._field[fleet.point.to_tuple()]._kore += fleet.kore / 2
                    to_split = fleet.kore / 2
                    for f_id, dmg in fleet_dmg_dict.items():
                        index = to_index(fleet.x, fleet.y, size)
                        to_distribute[f_id][index] = to_split * dmg / damage
                    board._delete_fleet(fleet)
                else:
                    fleet._ship_count -= damage
            
            # distribute kore
            for fleet_id, loc_kore_dict in to_distribute.items():
                fleet = board.fleets.get(fleet_id, False)
                if fleet:
                    fleet._fleet_kore += sum(loc_kore_dict.values())
                else:
                    for loc_idx, kore in loc_kore_dict.items():
                        x, y = from_index(loc_idx, size)
                        board._field[x, y]._kore += kore
            
            # collect kore
            for fleet in board.fleets.values():
                cell = board._field[fleet.point.to_tuple()]
                delta_kore = cell.kore * round(collection_rate_for_ship_count(fleet.ship_count), 3)
                if delta_kore > 0:
                    fleet._fleet_kore += delta_kore
                    board._field[fleet.point.to_tuple()]._kore -= delta_kore

            # regenerate kore
            for i in range(size ** 2):
                x, y = from_index(i, size)
                cell = board._field[x, y]
                if cell.fleet is None and cell.shipyard is None and cell.kore < board.configuration.max_cell_kore:
                    next_kore = round(cell.kore * (1 + board.configuration.regen_rate), 3)
                    cell._kore = next_kore
            
            board._field._shipyards = list(board._shipyards.values())
            board._field._fleets = list(board._fleets.values())

            board._step += 1
            yield board
    
    def __repr__(self):
        result = ""
        for y in range(self.configuration.size):
            for x in range(self.configuration.size):
                result += "|"
                cell = self._field[x, y]
                if cell.shipyard is not None:
                    result += chr(ord("A") + cell.shipyard.player_id)
                    result += f"{cell.shipyard.ship_count:04}"
                elif cell.fleet is not None:
                    result += chr(ord("a") + cell.fleet.player_id)
                    if cell.fleet.direction == "N":
                        result += "↑"
                    elif cell.fleet.direction == "E":
                        result += "→"
                    elif cell.fleet.direction == "S":
                        result += "↓"
                    else:
                        result += "←"
                    result += f"{cell.fleet.ship_count:03}"
                else:
                    result += f"  {int(cell.kore):03}"
            result += "|\n"
        return result