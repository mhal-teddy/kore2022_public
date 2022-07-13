from typing import Optional, Union
from board import Board
from cell import Field, Route
from board_decorator import Info
from point import Direction, Point
from helpers import (
    collection_rate_for_ship_count, 
    min_ship_count_for_flight_plan_len, 
    max_flight_plan_len_for_ship_count, 
    max_ships_to_spawn, 
    cached_property
)

class FlightPlan:
    def __init__(self, 
            flight_plan: str, 
            start_cell: Point, 
            field: Field, 
            plan_type: str, 
            is_longitude=True, 
            **kwargs
        ):
        self._command = flight_plan
        self._start_cell = start_cell
        self._field = field
        self._is_longitude = is_longitude
        self._plan_type = plan_type
        self._direction = None

        if plan_type == "CONVERT":
            self._convert_const = kwargs["convert_cost"]
        if plan_type == "EXISTING":
            self._direction = kwargs["direction"]
    
    @property
    def command(self) -> str:
        return self._command
    
    @property
    def is_longitude(self) -> bool:
        return self._is_longitude
    
    @property
    def plan_type(self) -> str:
        return self._plan_type
    
    @cached_property
    def min_ship_count(self) -> int:
        min_ships = min_ship_count_for_flight_plan_len(len(self._command))
        if self._plan_type == "CONVERT":
            return max(min_ships, self._convert_const)
        else:
            return min_ships
    
    @staticmethod
    def shortest_plan(start: Point, end: Point, field: Field, is_longitude=True) -> "FlightPlan":
        flight_plan = shortest_path_between(start, end, is_longitude)
        if flight_plan[-1].isdigit():
            flight_plan = flight_plan[:-1]
        return FlightPlan(flight_plan, start, field, "ONEWAY", is_longitude)
    
    @staticmethod
    def circle_plan(start: Point, diag: Point, field: Field, is_longitude=True) -> "FlightPlan":
        flight_plan = shortest_path_between(start, diag, is_longitude=is_longitude)
        flight_plan += shortest_path_between(diag, start, is_longitude=is_longitude)
        
        if flight_plan and flight_plan[-1].isdigit():
            flight_plan = flight_plan[:-1]
        return FlightPlan(flight_plan, start, field, "RETURN", is_longitude)
    
    @staticmethod
    def l_shaped_plan(start: Point, diag: Point, field: Field, is_longitude=True) -> "FlightPlan":
        flight_plan = shortest_path_between(start, diag, is_longitude=is_longitude)
        flight_plan += shortest_path_between(diag, start, is_longitude=not is_longitude)
        
        if flight_plan and flight_plan[-1].isdigit():
            flight_plan = flight_plan[:-1]
        return FlightPlan(flight_plan, start, field, "RETURN", is_longitude)

    @staticmethod
    def s_shaped_plan(
        start: Point, 
        end: Point, 
        curve: Point, 
        field: Field, 
        is_longitude=True, 
        is_convert=False
    ) -> "FlightPlan":
        if is_longitude:
            assert start.x == curve.x
            curve2 = Point(end.x, curve.y, field.size)
        else:
            assert start.y == curve.y
            curve2 = Point(curve.x, end.y, field.size)

        flight_plan = shortest_path_between(start, curve, is_longitude)
        flight_plan += shortest_path_between(curve, curve2, not is_longitude)
        flight_plan += shortest_path_between(curve2, end, is_longitude)

        if is_convert:
            flight_plan += "C"
            return FlightPlan(flight_plan, start, field, "CONVERT", is_longitude, convert_cost=50)
        else:
            if flight_plan and flight_plan[-1].isdigit():
                flight_plan = flight_plan[:-1]
            return FlightPlan(flight_plan, start, field, "ONEWAY", is_longitude)
    
    @staticmethod
    def convert_plan(start: Point, end: Point, field: Field, convert_cost: int, is_longitude=True) -> "FlightPlan":
        flight_plan = shortest_path_between(start, end, is_longitude=is_longitude)
        flight_plan += "C"
        return FlightPlan(flight_plan, start, field, "CONVERT", is_longitude, convert_cost=convert_cost)
    
    @staticmethod
    def existing_fleet_plan(start: Point, flight_plan: str, direction: str, field: Field) -> "FlightPlan":
        return FlightPlan(flight_plan, start, field, "EXISTING", direction=direction)
    
    @cached_property
    def flight_plan_route(self) -> Route:
        return Route.from_str(self._start_cell, self._field, self._command, self._direction)
    
    @staticmethod
    def find_best_s_shaped_plan(
        start: Point, 
        end: Point, 
        ship_count: int, 
        board: Board, 
        info: Info, 
        is_max_kore: bool = True, 
        is_convert: bool = False
    ) -> "FlightPlan":
        if start.x == end.x or start.y == end.y:
            if is_convert:
                return FlightPlan.convert_plan(start, end, board.field, 50, is_longitude=True)
            else:
                return FlightPlan.shortest_plan(start, end, board.field)
        
        size = board.configuration.size
        total_distance = start.distance(end)
        if is_max_kore:
            best_score = {"kore": 0, "plan": None}
        else:
            best_score = {"kore": 10**9, "plan": None}

        for is_longitude in {False, True}:
            for i in range(size):
                if not is_longitude:
                    point = Point(i, start.y, size)
                else:
                    point = Point(start.x, i, size)

                if start.distance(point) + point.distance(end) != total_distance:
                    continue

                plan = FlightPlan.s_shaped_plan(start, end, point, board.field, is_longitude, is_convert)
                if ship_count < plan.min_ship_count:
                    continue

                kore = plan.expected_total_assets(ship_count, board, info, is_my_shipyard=True)

                if is_max_kore and kore > best_score["kore"]:
                    best_score["plan"] = plan
                    best_score["kore"] = kore
                elif not is_max_kore and 0 < kore < best_score["kore"]:
                    best_score["plan"] = plan
                    best_score["kore"] = kore
        
        if best_score["plan"] is None:
            if is_convert:
                return FlightPlan.convert_plan(start, end, board.field, 50, is_longitude=True)
            else:
                return FlightPlan.shortest_plan(start, end, board.field)
        return best_score["plan"]
    
    def expected_total_assets(
        self, 
        ship_count: int, 
        board: Board, 
        info: Info, 
        is_my_shipyard: bool = False
    ) -> Union[int, float]:
        assert ship_count >= 1, f"ship_count: {ship_count} must be positive"
        me = board.current_player
        spawn_cost = board.configuration.spawn_cost

        if self.flight_plan_route:
            score = {"kore": 0, "damage": 0, "destroyed": set(), "opp_kore": 0}
            delta_kore = round(collection_rate_for_ship_count(ship_count), 3)

            route_kore = {}
            total_turn = 0
            for i, point in enumerate(self.flight_plan_route):
                
                if i == 0 or i == self.flight_plan_route.time:
                    continue

                total_turn += 1

                future_field = info.future_field(turn=i)
                if future_field is None:
                    future_field = info.future_field(turn=info.total_turn)

                
                cell = future_field[point.to_tuple()]
                if cell.shipyard is not None:
                    if cell.shipyard.player_id == me.player_id:
                        if is_my_shipyard:
                            return -10**9
                        else:
                            break
                    else:
                        return -10**9

                is_attacked = check_fleet_attacked(point, self._start_cell, ship_count, board, info)
                if is_attacked:
                    return -10**9
                
                if future_field is not None and i != self.flight_plan_route.time:
                    cell = future_field[point.to_tuple()]
                    
                    if cell.fleet is not None:
                        if cell.fleet.player_id == me.player_id:
                            return -10**9
                        
                        elif cell.fleet.player_id != me.player_id and cell.fleet.id not in score["destroyed"]:
                            score["damage"] += cell.fleet.ship_count
                            score["destroyed"].add(cell.fleet.id)
                            score["opp_kore"] += cell.fleet.expected_kore
                    
                    for fleet in cell.adjacent_fleets:
                        if fleet.id != me.player_id and fleet.id not in score["destroyed"]:
                            score["damage"] += fleet.ship_count
                            score["destroyed"].add(fleet.id)
                            score["opp_kore"] += fleet.expected_kore

                if (point.x, point.y) in route_kore:
                    previous, gain = route_kore[(point.x, point.y)]
                    mined_kore = gain * 1.02**(i - previous)
                else:
                    mined_kore = 0

                distance = self._start_cell.distance(point)
                if future_field is not None:
                    gain = (future_field[point.to_tuple()].kore / 1.02 - mined_kore) * delta_kore
                    alpha = gain * 1.02 ** distance
                    score["kore"] += alpha
                else:
                    field_kore = future_field[point.to_tuple()].kore * (i - info.total_turn)**1.02
                    gain = (field_kore / 1.02 - mined_kore) * delta_kore
                    alpha = gain * 1.02 ** distance
                    score["kore"] += alpha
                
                route_kore[(point.x, point.y)] = (i, gain)
            
            if score["damage"] >= 1:
                return -10**9

            total_assets = score["kore"] + score["opp_kore"]
            return total_assets / (total_turn + 1)
        else:
            return -10**9

    def future_damage(self, player_id: int, info: Info) -> int:
        damage = 0
        attack = set()
        for i, point in enumerate(self.flight_plan_route):
            if i == 0 and i == len(self.flight_plan_route) - 1:
                continue

            future_field = info.future_field(turn=i)
            if future_field is not None:
                dmg, attack_id = future_field[point.to_tuple()].damage(player_id, attack)
                damage += dmg
                attack |= attack_id
        return damage, attack
    
    def __repr__(self):
        return f"FlightPlan(start=({self._start_cell.x}, {self._start_cell.y}), " \
            f"flight_plan={self._command}, " \
            f"plan_type='{self.plan_type}')"
    
def shortest_path_between(start: Point, end: Point, is_longitude=True) -> str:
    flight_path_x = ""
    flight_path_y = ""
    abs_x = abs(end.x - start.x)
    if abs_x == 0:
        pass
    elif abs_x < start._size / 2:
        flight_path_x += "E" if end.x > start.x else "W"
        distance = abs_x - 1
        if distance > 0:
            flight_path_x += str(distance)
    else:
        flight_path_x += "W" if end.x > start.x else "E"
        distance = min(start.x, end.x) + start._size - max(start.x, end.x) - 1
        if distance > 0:
            flight_path_x += str(distance)

    abs_y = abs(end.y - start.y)
    if abs_y == 0:
        pass
    elif abs_y < start._size / 2:
        flight_path_y += "S" if end.y > start.y else "N"
        distance = abs_y - 1
        if distance > 0:
            flight_path_y += str(distance)
    else:
        flight_path_y += "N" if end.y > start.y else "S"
        distance = min(start.y, end.y) + start._size - max(start.y, end.y) - 1
        if distance > 0:
            flight_path_y += str(distance)
    
    if is_longitude:
        return flight_path_y + flight_path_x
    else:
        return flight_path_x + flight_path_y

def check_fleet_attacked(point: Point, start: Point, num_ships: int, board: Board, info: Info) -> bool:
    me = board.current_player
    opp = board.opponent_player

    closest_me = board.field.closest_shipyard(point, me.player_id)
    closest_opp = board.field.closest_shipyard(point, opp.player_id)
    if closest_me is None or closest_opp is None:
        return False

    if (closest_me.point == start
        and closest_me.point.distance(point) < closest_opp.point.distance(point)
    ):
        return False
    
    elif (not closest_me.point == start
        and closest_me.point.distance(point) < closest_opp.point.distance(point) - 1
    ):
        return False

    me_distance = start.distance(point)
    opp_distance = closest_opp.point.distance(point)

    turn = me_distance - opp_distance + 1
    field = info.future_field(turn=turn)
    if field is None and turn == 0:
        field = board.field
    elif field is None and turn < 0:
        return False
    elif field is None:
        field = info.future_field(turn=info.total_turn)
    
    spawn_power = 0
    for i in range(turn):
        spawn_power += max_ships_to_spawn(closest_opp.turns_controlled + i)

    if num_ships > field[closest_opp.point.to_tuple()].shipyard.ship_count + spawn_power:
        return False
    else:
        return True