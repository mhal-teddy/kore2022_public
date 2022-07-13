from collections import defaultdict
from typing import Dict, List, Tuple
from action import Action
from board import Board
from board_decorator import Info, future_board
from flight_plan import FlightPlan
from piece import Shipyard
from point import Point
from helpers import min_ship_count_for_flight_plan_len, max_ships_to_spawn

def attack3(board: Board, info: Info) -> None:
    """converted shipyard in the future"""
    me = board.current_player
    opp = board.opponent_player
    convert_cost = board.configuration.convert_cost

    # convert point
    targets = []
    for fleet in opp.fleets:
        if fleet.route.is_convert:
            targets.append((fleet.route.end, max(fleet.ship_count - convert_cost, 0)))

    if not targets:
        return
    
    for point, min_ships in targets:
        closest = board.field.closest_shipyard(point, me.player_id)
        closest_opp = board.field.closest_shipyard(point, opp.player_id)
        if closest is None or closest.next_action is not None:
            continue

        if closest.point.distance(point) > closest_opp.point.distance(point) * 1.5:
            continue
        
        num_ships = max(closest.available_ship_count, min_ships + 1, min_ship_count_for_flight_plan_len(7))
        if closest.available_ship_count >= num_ships:
            plan = FlightPlan.find_best_s_shaped_plan(closest.point, point, num_ships, board, info, False)
            damage, _ = plan.future_damage(me.player_id, info)
            if damage > 0:
                continue

            # overwrite
            closest.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)

def attack2(board: Board, info: Info) -> None:
    """shipyard attack"""
    me = board.current_player
    opp = board.opponent_player
    size = board.configuration.size
    target = find_attack_target(board, info)

    for shipyard in me.shipyards:
        attack_flag = False

        if shipyard.next_action is not None:
            continue

        if shipyard.available_ship_count < min_ship_count_for_flight_plan_len(7):
            continue

        if (target["point"] is not None 
            and shipyard.point.distance(target["point"]) <= target["turn"] <= size
        ):
            attack_flag = True

        if attack_flag:
            num_ships = shipyard.available_ship_count
            plan = FlightPlan.find_best_s_shaped_plan(
                shipyard.point, target["point"], num_ships, board, info, False
            )
            # overwrite
            shipyard.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)

def find_attack_target(board: Board, info: Info) -> dict:
    me = board.opponent_player
    opp = board.opponent_player
    spawn_cost = board.configuration.spawn_cost
    convert_cost = board.configuration.convert_cost
    target = {"point": None, "power": 0, "turn": 100}
    hostile = defaultdict(list)
    
    # opponent power and distance
    for opp_sy in opp.shipyards:
        attack_power = distance_power(opp_sy.point, board, info)
        
        # guard ships
        need_kore = 0
        spawn_power = 0
        hostile[opp_sy.id].append(0)
        for turn in range(1, info.total_turn + 1):
            cell_sy = info.future_field(turn=turn)[opp_sy.point.to_tuple()].shipyard
            
            if cell_sy.player_id != opp.player_id:
                hostile[opp_sy.id].append(0)
                continue

            # max spawn
            mining_kore = info.field_kore(turn=turn)
            max_spawn, need_kore = opp_sy.future_spawn(opp.kore + mining_kore - need_kore, turn)
            spawn_power += max_spawn

            # ships from other shipyards
            help_power = 0
            for other_sy in opp.shipyards:
                distance = opp_sy.point.distance(other_sy.point)
                if other_sy.id == opp_sy.id or cell_sy.player_id != opp.player_id:
                    continue

                if 0 < turn - distance <= info.total_turn:
                    future_sy = info.future_field(turn=turn - distance)[other_sy.point.to_tuple()].shipyard
                elif turn == distance:
                    future_sy = other_sy
                else:
                    future_sy = None

                if future_sy is not None and future_sy.player_id == opp.player_id:
                    help_power += future_sy.ship_count

            # maximum power
            opponent_power = cell_sy.ship_count + spawn_power + help_power
            hostile[opp_sy.id].append(opponent_power)
        
        for distance in attack_power:
            if attack_power[distance] > hostile[opp_sy.id][distance] and distance < target["turn"]:
                target["power"] = hostile[opp_sy.id][distance]
                target["point"] = opp_sy.point
                target["turn"] = distance
        
    # fleet to convert
    for fleet in opp.fleets:
        if not fleet.route.is_convert:
            continue
    
        convert_point = fleet.route.end
        attack_power = distance_power(convert_point, board, info)

        hostile[fleet.id].append(0)
        for turn in range(1, info.total_turn + 1):

            cell_sy = info.future_field(turn=turn)[convert_point.to_tuple()].shipyard

            if cell_sy is None:
                hostile[fleet.id].append(0)
                continue

            # max spawn
            spawn_power = turn - fleet.route.time + 1

            # ships from other shipyards
            help_power = 0
            for other_sy in opp.shipyards:
                distance = cell_sy.point.distance(other_sy.point)
                if other_sy.id == cell_sy.id or cell_sy.player_id != opp.player_id:
                    continue
                
                if 0 < turn - distance <= info.total_turn:
                    future_sy = info.future_field(turn=turn - distance)[other_sy.point.to_tuple()].shipyard
                elif turn == distance:
                    future_sy = other_sy
                else:
                    future_sy = None

                if future_sy is not None and future_sy.player_id == opp.player_id:
                    help_power += future_sy.ship_count
            
            # maximum power
            opponent_power = cell_sy.ship_count + spawn_power + help_power
            hostile[fleet.id].append(opponent_power)

        for distance in attack_power:
            if attack_power[distance] > hostile[fleet.id][distance] and distance < target["turn"]:
                target["power"] = hostile[fleet.id][distance]
                target["point"] = convert_point
                target["turn"] = distance
    
    return target

def distance_power(point: Point, board: Board, info: Info) -> dict:
    me = board.current_player
    closest = sorted([sy for sy in me.shipyards], key=lambda x: x.point.distance(point))

    attack_power = {}
    ship_count = 0
    for sy in closest:
        ship_count += sy.available_ship_count
        distance = sy.point.distance(point)

        attack_power[distance] = ship_count
    
    return attack_power

def build3(board: Board, info: Info) -> None:
    """expansion"""
    me = board.current_player
    opp = board.opponent_player
    convert_cost = board.configuration.convert_cost
    
    if len(me.shipyards) > 3 * len(board.opponent_player.shipyards):
        return
    
    ships_needed = need_more_shipyards(board, info)
    if not ships_needed:
        return
    
    spawn_shipyards = []

    # closest distance between my shipyard and opponent
    min_distance = 100
    for my_sy in me.shipyards:
        for opp_sy in opp.shipyards:
            distance = my_sy.point.distance(opp_sy.point)
            if distance < min_distance:
                min_distance = distance

    # convert score
    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue
        
        if shipyard.available_ship_count < convert_cost:
            continue

        best_score = {"score": -10**9, "point": None}
        for cell in board.field.surrounding_cells(shipyard.point, 6, 2, -1):
            
            num_shipyards = sum(
                1 for sy in opp.shipyards if sy.point.distance(cell.point) <= 10
            )
            if num_shipyards >= 2:
                continue

            score = spawn_score(shipyard.point, cell.point, board, info)
            if score > best_score["score"]:
                best_score["point"] = cell.point
                best_score["score"] = score

        if best_score["point"] is not None:
            spawn_shipyards.append((shipyard, best_score["score"], best_score["point"]))

    spawn_shipyards.sort(key=lambda x: x[1], reverse=True)
    
    shipyard_count = 0
    for shipyard, score, point in spawn_shipyards:
        if shipyard_count >= ships_needed:
            break

        num_ships = shipyard.available_ship_count
        plan = FlightPlan.find_best_s_shaped_plan(shipyard.point, point, num_ships, board, info, True, True)

        # overwrite
        shipyard.next_action = Action.launch(num_ships=shipyard.available_ship_count, flight_plan=plan.command)
        
        shipyard_count += 1
    
    # overwrite
    me.need_shipyard = max(ships_needed - shipyard_count, 0)

def need_more_shipyards(board: Board, info: Info) -> int:
    me = board.current_player
    opp = board.opponent_player

    if me.total_ship_count < 100:
        return 0
    
    # the number of shipyards in the future
    expected_shipyard_count = len(me.shipyards)
    opponent_shipyard_count = len(opp.shipyards)

    for fleet in board.fleets.values():
        if fleet.route.is_convert and fleet.player_id == me.player_id:
            expected_shipyard_count += 1
        elif fleet.route.is_convert and fleet.player_id == opp.player_id:
            opponent_shipyard_count += 1

    shipyard_production_capacity = sum(sy.max_spawn for sy in me.shipyards)

    if expected_shipyard_count < opponent_shipyard_count and me.total_ship_count < opp.total_ship_count:
        me.counter = True
        return 0

    if board.steps_left > 100:
        scale = 3
    elif board.steps_left > 50:
        scale = 4
    elif board.steps_left > 10:
        scale = 100
    else:
        scale = 1000
    
    needed = me.available_kore() > scale * shipyard_production_capacity
    if not needed:
        return 0
    
    if (expected_shipyard_count == opponent_shipyard_count 
        and me.total_ship_count < opp.total_ship_count 
        and board.steps_left > 100
    ):
        return 0
    
    if expected_shipyard_count > opponent_shipyard_count:
        return 0
    
    if len(me.shipyards) < 10:
        if expected_shipyard_count > len(me.shipyards):
            return 0
        else:
            return 1
    
    return max(0, 5 - (expected_shipyard_count - len(me.shipyards)))

def spawn_score(start: Point, end: Point, board: Board, info: Info) -> float:
    me = board.current_player
    opp = board.opponent_player
    size = board.configuration.size
    turn = start.distance(end)
    score = {"num_ships": 0, "kore": 0}

    max_distance = 6

    for i in range(turn, info.total_turn):
        future_cell = info.future_field(turn=i)[end.to_tuple()]
        if future_cell.fleet is not None and future_cell.fleet.player_id == opp.player_id:
            return -10**9
    
    if board.field[end.to_tuple()].shipyard is not None:
        return -10**9
    
    for fleet in board.fleets.values():
        if fleet.route.is_convert and fleet.route.end == end:
            return -10**9
    
    closest_opp = board.field.closest_distance(start, opp.player_id)
    if (closest_opp is not None 
        and closest_opp >= 10 
        and start.distance(end) < 5
    ):
        return -10**9
    
    closest = board.field.closest_shipyard(end, opp.player_id)
    if closest is not None:
        future_cell = info.future_field(turn=info.total_turn)[closest.point.to_tuple()]
        score["num_ships"] = future_cell.shipyard.ship_count * (size - closest_opp)

    future_field = info.future_field(turn=turn)
    for cell in future_field.surrounding_cells(end, 1, max_distance + 1): 
        if cell.shipyard is not None:
            
            if cell.point.distance(end) <= 3:
                return -10**9
            
            if cell.shipyard.player_id == opp.player_id:
                return -10**9
            else:
                score["num_ships"] += 1
        
        if cell.shipyard is None:
            score["kore"] += cell.kore

    distance_me = sum(sy.point.distance(end)**2 for sy in me.shipyards)
    distance_opp = sum(sy.point.distance(end) for sy in opp.shipyards)
    
    return score["kore"] + 30 * distance_me

def defence2(board: Board, info: Info) -> None:
    """shipyard defense"""
    me = board.current_player
    opp = board.opponent_player
    spawn_cost = board.configuration.spawn_cost
    need_help_shipyards = []
    need_help_id = []

    # closest shipyard
    closest_sy = {}
    for shipyard in opp.shipyards:
        closest = board.field.closest_shipyard(shipyard.point, me.player_id)
        if closest is not None:
            closest_sy[closest.id] = shipyard

    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue

        incoming_hostile_fleets = shipyard.incoming_hostile_fleets
        incoming_allied_fleets = shipyard.incoming_allied_fleets

        incoming_hostile_power = sum(fleet.ship_count for fleet in incoming_hostile_fleets)
        if incoming_hostile_fleets:
            incoming_hostile_time = min(fleet.route.time for fleet in incoming_hostile_fleets)
        else:
            incoming_hostile_time = 0

        # defense in advance
        if shipyard.id in closest_sy:
            closest_opp = closest_sy[shipyard.id]
            distance = shipyard.point.distance(closest_opp.point)
            incoming_allied_power = sum(
                fleet.ship_count
                for fleet in incoming_allied_fleets 
                if fleet.route.time <= incoming_hostile_time + distance
            )
            attack_power = max(closest_opp.ship_count + incoming_hostile_power - incoming_allied_power, 0)
            # overwrite
            shipyard.expected_guard = min(shipyard.ship_count, attack_power)
            shipyard.guard_turn = shipyard.point.distance(closest_opp.point)

        if not incoming_hostile_fleets:
            continue
        
        incoming_allied_power = sum(
            fleet.ship_count 
            for fleet in incoming_allied_fleets 
            if fleet.route.time < incoming_hostile_time
        )

        ships_needed = incoming_hostile_power - incoming_allied_power
        if ships_needed <= 0:
            continue
        if shipyard.available_ship_count > ships_needed:
            # overwrite
            shipyard.guard_ship_count = min(shipyard.available_ship_count, int(ships_needed * 1.1))
            shipyard.guard_turn = incoming_hostile_time
            continue

        num_ships = shipyard.spawn_as_many_ships(me.available_kore())
        
        if num_ships > 0:
            # overwrite
            shipyard.next_action = Action.spawn(num_ships=num_ships, turns_controlled=shipyard.turns_controlled)

        shipyard.guard_ship_count = shipyard.ship_count
        shipyard.guard_turn = incoming_hostile_time

        expected_spawn = spawn_max_ships_to_defense(shipyard, board, info)

        if ships_needed - expected_spawn > 0:
            need_help_shipyards.append((shipyard, ships_needed - expected_spawn))
            need_help_id.append(shipyard.id)
    
    # help allied shipyards
    for shipyard, needed in need_help_shipyards:
        incoming_hostile_fleets = shipyard.incoming_hostile_fleets
        incoming_hostile_time = min(fleet.route.time for fleet in incoming_hostile_fleets)

        board._players[me.player_id]._shipyards = sorted(
            [sy for sy in me.shipyards], key=lambda x: shipyard.point.distance(x.point)
        )

        closest = board.field.closest_shipyard(shipyard.point, me.player_id)

        help_power = needed
        for other_sy in me.shipyards:
            if (other_sy.id == shipyard.id) or (other_sy.next_action is not None):
                continue

            if not help_power:
                break

            distance = other_sy.point.distance(shipyard.point)
            if (other_sy.id in need_help_id 
                and other_sy.guard_turn <= distance 
                and other_sy.ship_count - other_sy.guard_ship_count <= 0
            ):
                continue

            if distance == incoming_hostile_time:
                plan = FlightPlan.shortest_plan(other_sy.point, shipyard.point, board.field, True)
                if other_sy.id in need_help_id:
                    max_ships = other_sy.ship_count
                    num_ships = max(plan.min_ship_count, help_power)
                else:
                    max_ships = other_sy.ship_count - other_sy.guard_ship_count
                    num_ships = max(plan.min_ship_count, min(help_power, max_ships))
                
                if max_ships >= num_ships:
                    # overwrite
                    other_sy.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)
                    help_power = max(help_power - num_ships, 0)
            
            elif distance < incoming_hostile_time:
                # overwrite
                num_ships = min(needed, other_sy.ship_count)
                other_sy.guard_ship_count = num_ships
                shipyard.guard_turn = incoming_hostile_time - distance

            elif distance > incoming_hostile_time and closest is not None and closest.id == other_sy.id:
                # be occupied in the future
                future_shipyard = info.future_field(turn=info.total_turn)[shipyard.point.to_tuple()].shipyard
                if future_shipyard.player_id != me.player_id:
                    plan = FlightPlan.shortest_plan(other_sy.point, shipyard.point, board.field, True)
                    num_ships = max(plan.min_ship_count, future_shipyard.ship_count)

                    # overwrite
                    if other_sy.available_ship_count > num_ships:
                        other_sy.next_action = Action.launch(num_ships=other_sy.available_ship_count, flight_plan=plan.command)

def defence3(board: Board, info: Info) -> None:
    """fleet attack"""
    me = board.current_player

    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue

        opponent_shipyard = board.field.closest_shipyard(shipyard.point, board.opponent_player.player_id)
        if opponent_shipyard is None:
            return
        
        here = board.field[shipyard.point.to_tuple()].point
        opponent = board.field[opponent_shipyard.point.to_tuple()].point
        max_turn = min(here.distance(opponent) // 2, info.total_turn)

        for i in range(1, max_turn + 1):
            future_field = info.future_field(turn=i)
            
            fleet = future_field.closest_fleet(shipyard.point, board.opponent_player.player_id)
            if fleet is None or shipyard.ship_count <= fleet.ship_count:
                continue

            target = board.field[fleet.point.to_tuple()].point
            
            if here.distance(fleet.point) == i:
                
                if here.distance(fleet.point) >= opponent.distance(fleet.point):
                    continue

                cell = board.field[fleet.point.to_tuple()]
                if any([fl.player_id != me.player_id for fl in cell.adjacent_fleets]):
                    continue

                is_longitude = True if fleet.direction in {"N", "S"} else False
                plan = FlightPlan.l_shaped_plan(here, target, board.field, is_longitude=is_longitude)
                num_ships = max(fleet.ship_count + 2, plan.min_ship_count)

                if shipyard.available_ship_count >= num_ships:
                    # overwrite
                    shipyard.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)
                    return
            
            if here.distance(fleet.point) == i+1:
                if here.distance(fleet.point) > opponent.distance(fleet.point):
                    continue

                for diag in target.adjacent_point:
                    if here.distance(diag) == i:
                        is_longitude = True if fleet.direction in {"N", "S"} else False
                        plan = FlightPlan.l_shaped_plan(here, diag, board.field, is_longitude=is_longitude)
                        num_ships = max(fleet.ship_count + 2, plan.min_ship_count)

                        if shipyard.available_ship_count >= num_ships:
                            # overwrite
                            shipyard.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)
                            return

def defence4(board: Board, info: Info) -> None:
    """help shipyard to be converted"""
    me = board.current_player

    targets = []
    for my_fleet in me.fleets:
        if not my_fleet.route.is_convert:
            continue

        end = my_fleet.route.end

        attacked_turn = 0
        opp_power = 0
        for turn in range(1, info.total_turn):
            future_shipyard = info.future_field(turn=turn)[end.to_tuple()].shipyard

            if future_shipyard is None:
                continue
            
            if future_shipyard.player_id != me.player_id and attacked_turn == 0:
                attacked_turn = turn
                break
            
        if future_shipyard is not None and future_shipyard.player_id != me.player_id:
            opp_power = future_shipyard.ship_count
        
        if attacked_turn != 0:
            targets.append({"point": end, "power": opp_power, "attacked": attacked_turn})
    
    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue

        targets.sort(key=lambda x: x["attacked"])
        for t in targets:
            distance = shipyard.point.distance(t["point"])
            if distance > t["attacked"]:
                continue

            if distance == t["attacked"]:
                plan = FlightPlan.shortest_plan(shipyard.point, t["point"], board.field, True)
                num_ships = max(plan.min_ship_count, t["power"] + 1)
                
                if shipyard.ship_count >= num_ships:
                    # overwrite
                    shipyard.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)
                    break
            else:
                # overwrite
                shipyard.guard_ship_count = max(shipyard.guard_ship_count, t["power"])
                break

def spawn_max_ships_to_defense(shipyard: Shipyard, board: Board, info: Info) -> int:
    me = board.current_player
    spawn_cost = board.configuration.spawn_cost

    spawn_kore = 0
    total = 0
    for i in range(shipyard.guard_turn):
        spawn_ships = sum(max_ships_to_spawn(sy.turns_controlled + i) for sy in me.shipyards)
        spawn_kore += spawn_ships * spawn_cost

        if me.kore < spawn_kore:
            return total

        total += max_ships_to_spawn(shipyard.turns_controlled + i)
    return total

def defence1(board: Board, info: Info) -> None:
    """calculate opponent power in advance"""
    me = board.current_player
    opp = board.opponent_player
    convert_cost = board.configuration.convert_cost

    convert_fleet = [fleet for fleet in opp.fleets if fleet.route.is_convert]

    for shipyard in me.shipyards:

        # distance from opponent
        attack_power = defaultdict(list)
        for opp_sy in opp.shipyards:
            distance = shipyard.point.distance(opp_sy.point)
            attack_power[distance].append(opp_sy)
        
        fleet_power = defaultdict(list)
        for fleet in convert_fleet:
            distance = shipyard.point.distance(fleet.route.end)
            fleet_power[distance].append(fleet)

        attack_sy = []
        for turn in range(30):
            if turn == 0:
                # overwrite
                shipyard.capacity.append(shipyard.ship_count)
                continue

            # spawn
            for opp_dict in attack_sy:
                additional_turn = opp_dict["turns_controlled"] + turn - opp_dict["turn"]
                opp_dict["ships"] += max_ships_to_spawn(additional_turn)
            
            if turn in attack_power:
                for sy in attack_power[turn]:
                    attack_sy.append({"turns_controlled": sy.turns_controlled, "ships": sy.ship_count, "turn": turn})
            
            for turn in fleet_power:
                for fleet in fleet_power[turn]:
                    ship_count = fleet.ship_count - convert_cost
                    if turn == fleet.route.time and ship_count >= 0:
                        attack_sy.append({"turns_controlled": 1, "ships": ship_count, "turn": turn})
            
            if turn <= info.total_turn:
                cell_sy = info.future_field(turn=turn)[shipyard.point.to_tuple()].shipyard
            else:
                cell_sy = info.future_field(turn=info.total_turn)[shipyard.point.to_tuple()].shipyard

            incoming_hostile_power = sum(
                fleet.ship_count for fleet in shipyard.incoming_hostile_fleets 
                if fleet.route.time <= turn
            )

            attack = sum(opp_dict["ships"] for opp_dict in attack_sy) + incoming_hostile_power

            if cell_sy.player_id == me.player_id:
                # overwrite
                shipyard.capacity.append(cell_sy.ship_count - attack)
            else:
                # overwrite
                shipyard.capacity.append(-cell_sy.ship_count - attack)

def defence5(board: Board, info: Info) -> None:
    """need help in advance"""
    me = board.current_player

    if len(me.shipyards) == 1:
        return

    need_help = []
    for shipyard in me.shipyards:
        need_ships = shipyard.ship_count - shipyard.guard_ship_count - shipyard.expected_guard
        if need_ships < 0:
            need_help.append({"shipyard": shipyard, "ships": -need_ships})
    
    for need in need_help:
        shipyard = need["shipyard"]
        closest = board.field.closest_shipyard(shipyard.point, me.player_id)

        if closest is None:
            continue

        if closest.next_action is not None or closest.id == shipyard.id:
            continue
            
        if shipyard.incoming_hostile_fleets:
            incoming_hostile_time = min(fleet.route.time for fleet in shipyard.incoming_hostile_fleets)
            if shipyard.point.distance(closest.point) > incoming_hostile_time:
                continue

        if closest.available_ship_count < min_ship_count_for_flight_plan_len(7):
            continue

        if closest.available_ship_count >= need["ships"]:
            num_ships = closest.available_ship_count
            plan = FlightPlan.find_best_s_shaped_plan(closest.point, shipyard.point, num_ships, board, info)

            # overwrite
            closest.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)
            continue

def mine1(board: Board, info: Info) -> None:
    """mining with best route"""
    is_longitude = True
    me = board.current_player
    opp = board.opponent_player

    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue

        if shipyard.ship_count <= 2:
            continue
        
        if len(me.shipyards) < 5:
            max_distance = 13
        else:
            max_distance = 8
        max_distance = min(board.steps_left // 2, max_distance)
        
        score = {"plan": None, "kore": 0, "ships": 0}

        min_ships, min_distance = find_best_ship_count(shipyard, board, info)
        if min_distance >= max_distance:
            min_distance = max(max_distance - 1, 1)

        for cell in board.field.surrounding_cells(shipyard.point, start=min_distance, stop=max_distance):
            distance = shipyard.point.distance(cell.point)

            if min_ships < 10:
                available_ship_count = shipyard.ship_count
            else:
                available_ship_count = min(shipyard.capacity[distance * 2], shipyard.ship_count)
                
            # find best plan
            for plan_type in ("circle1", "circle2", "l_shaped1", "l_shaped2"):
                if plan_type == "circle1":
                    plan = FlightPlan.circle_plan(shipyard.point, cell.point, board.field, is_longitude)
                if plan_type == "circle2":
                    plan = FlightPlan.circle_plan(shipyard.point, cell.point, board.field, not is_longitude)
                if plan_type == "l_shaped1":
                    plan = FlightPlan.l_shaped_plan(shipyard.point, cell.point, board.field, is_longitude)
                if plan_type == "l_shaped2":
                    plan = FlightPlan.l_shaped_plan(shipyard.point, cell.point, board.field, not is_longitude)

                num_ships = max(min_ships, plan.min_ship_count)
                
                if available_ship_count < num_ships:
                    continue

                if 0 <= available_ship_count - num_ships <= 2:
                    num_ships = available_ship_count

                kore = plan.expected_total_assets(num_ships, board, info)

                if kore >= score["kore"]:
                    score["kore"] = kore
                    score["plan"] = plan
                    score["ships"] = num_ships
        
        if score["plan"] is None:
            continue
        else:
            # overwrite
            shipyard.next_action = Action.launch(num_ships=score["ships"], flight_plan=score["plan"].command)

def mine2(board: Board, info: Info) -> None:
    """shipyard surrounded by friendly shipyards"""
    me = board.current_player

    if len(me.shipyards) < 5:
        return
    
    front = []
    support = []
    for shipyard in me.shipyards:
        closest = {direction: None for direction in ("first", "second", "third", "fourth")}
        
        for i, cell in enumerate(board.field.surrounding_cells(shipyard.point, 1, 10)):
            if cell.shipyard is None:
                continue

            if (i + 1) % 4 == 1:
                quadrant = "fourth"
            elif (i + 1) % 4 == 2:
                quadrant = "third"
            elif (i + 1) % 4 == 3:
                quadrant = "second"
            else:
                quadrant = "first"
            
            if closest[quadrant] is None and cell.shipyard.player_id != me.player_id:
                front.append(shipyard)
                break
            
            if closest[quadrant] is None:
                closest[quadrant] = shipyard

        # safety shipyard
        if all([value is not None for value in closest.values()]):
            support.append(shipyard)
    
    # send ships
    for shipyard in support:
        if shipyard.next_action is not None:
            continue

        target = None
        min_ship_count = 10**9
        for sy in front:
            distance = shipyard.point.distance(sy.point)
            cell = info.future_field(turn=distance)[sy.point.to_tuple()]

            if cell.shipyard.player_id != me.player_id:
                continue

            if cell.shipyard.ship_count < min_ship_count:
                min_ship_count = cell.shipyard.ship_count
                target = sy
        
        if target is None:
            continue

        num_ships = max(shipyard.available_ship_count, min_ship_count_for_flight_plan_len(7))
        plan = FlightPlan.find_best_s_shaped_plan(shipyard.point, target.point, num_ships, board, info, True)
        
        # overwrite
        if shipyard.available_ship_count >= num_ships:
            shipyard.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)

def mine3(board: Board, info: Info) -> None:
    """collect ships at one shipyard if my shipyards are stronger"""
    me = board.current_player
    opp = board.opponent_player

    expected_shipyard_count = len(me.shipyards)
    opponent_shipyard_count = len(opp.shipyards)

    for fleet in board.fleets.values():
        if fleet.route.is_convert and fleet.player_id == me.player_id:
            expected_shipyard_count += 1
        elif fleet.route.is_convert and fleet.player_id == opp.player_id:
            opponent_shipyard_count += 1
    
    if not me.counter and me.total_ship_count < opp.total_ship_count + 50:
        return
    
    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue

        num_ships = shipyard.available_ship_count
        if num_ships < 50:
            continue

        closest = board.field.closest_shipyard(shipyard.point, me.player_id)
        if closest is None:
            continue

        opp1 = board.field.closest_distance(shipyard.point, opp.player_id)
        opp2 = board.field.closest_distance(closest.point, opp.player_id)
        if opp1 is None or opp2 is None or opp1 <= opp2:
            continue

        plan = FlightPlan.find_best_s_shaped_plan(shipyard.point, closest.point, num_ships, board, info)
        # overwrite
        shipyard.next_action = Action.launch(num_ships=num_ships, flight_plan=plan.command)     

def find_best_ship_count(shipyard: Shipyard, board: Board, info: Info) -> Tuple[int, int]:
    me = board.current_player
    spawn_cost = board.configuration.spawn_cost

    if me.available_kore() / len(me.shipyards) < spawn_cost:
        return 3, 1

    return min_ship_count_for_flight_plan_len(6), 1

def spawn1(board: Board, info: Info) -> None:
    me = board.current_player

    ship_count = sum(x.ship_count for x in me.shipyards)
    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue

        if ship_count > max_ships_to_control(board):
            return

        if not need_more_ships(board, shipyard.ship_count):
            return
        
        spawn_cost = board.configuration.spawn_cost
        num_ships = min(int(me.available_kore() // spawn_cost), shipyard.spawn_as_many_ships(me.available_kore()))

        if num_ships > 0:
            # overwrite
            shipyard.next_action = Action.spawn(num_ships=num_ships, turns_controlled=shipyard.turns_controlled)
            ship_count += num_ships

def spawn2(board: Board, info: Info) -> None:
    """spawn for attack"""
    me = board.current_player
    opp = board.opponent_player
    spawn_cost = board.configuration.spawn_cost

    if board.steps_left <= 50 and me.total_ship_count > opp.total_ship_count + 50:
        return

    max_ships_spawn = sum(sy.max_spawn for sy in me.shipyards)
    if me.available_kore() < max_ships_spawn * spawn_cost:
        return
    
    if me.available_kore() < opp.kore + 50 or me.total_ship_count > opp.total_ship_count:
        return

    board._players[me.player_id]._shipyards = sorted([sy for sy in me.shipyards], key=lambda x: -x.turns_controlled)

    ship_count = sum(x.ship_count for x in me.shipyards)
    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue

        if ship_count > max_ships_to_control(board):
            return

        if not need_more_ships(board, shipyard.ship_count):
            return
        
        num_ships = shipyard.max_spawn
        if me.available_kore() // spawn_cost > num_ships:
            # overwrite
            shipyard.next_action = Action.spawn(num_ships=num_ships, turns_controlled=shipyard.turns_controlled)
            ship_count += num_ships

def spawn3(board: Board, info: Info) -> None:
    me = board.current_player
    opp = board.opponent_player
    spawn_cost = board.configuration.spawn_cost

    board._players[me.player_id]._shipyards = sorted([sy for sy in me.shipyards], key=lambda x: -x.turns_controlled)

    superior = me.total_ship_count > opp.total_ship_count + 50
    inferior = (len(me.shipyards) < len(opp.shipyards)) and (me.total_ship_count < opp.total_ship_count)

    ship_count = sum(x.ship_count for x in me.shipyards)
    ready_to_convert = 0
    for shipyard in me.shipyards:
        if shipyard.next_action is not None:
            continue

        if ship_count > max_ships_to_control(board):
            return
        
        if not need_more_ships(board, shipyard.ship_count):
            return
        
        need_shipyard = max(me.need_shipyard - ready_to_convert, 0)
        expected_ships = spawn_to_allied_ship_count(shipyard, board, info)

        if need_shipyard == 0 and not (superior or inferior):
            if expected_ships == -1 and shipyard.ship_count > min_ship_count_for_flight_plan_len(7):
                continue

            if expected_ships != -1 and shipyard.ship_count >= min_ship_count_for_flight_plan_len(6):
                continue
        
        num_ships = shipyard.max_spawn
        if me.available_kore() // spawn_cost > num_ships:
            # overwrite
            shipyard.next_action = Action.spawn(num_ships=num_ships, turns_controlled=shipyard.turns_controlled)
            ship_count += num_ships
            ready_to_convert += 1
    
def need_more_ships(board: Board, ship_count: int) -> bool:
    me = board.current_player
    opp = board.opponent_player

    if board.steps_left < 10:
        return False
    if board.steps_left < 100 and len(me.fleets) < max(5, len(opp.fleets) - 5):
        return False
    if ship_count > max_ships_to_control(board):
        return False
    return True

def max_ships_to_control(board: Board) -> int:
    return max(100, 3 * sum(x.ship_count for x in board.opponent_player.shipyards))

def spawn_to_allied_ship_count(shipyard: Shipyard, board: Board, info: Info) -> int:
    """the number of ships to spawn by the time allied fleet coming"""
    me = board.current_player
    spawn_cost = board.configuration.spawn_cost

    closest_allied = {"ships": 0, "turn": 20}
    for fleet in shipyard.incoming_allied_fleets:
        if fleet.route.time < closest_allied["turn"]:
            closest_allied["ships"] = fleet.ship_count
            closest_allied["turn"] = fleet.route.time
        
        elif fleet.route.time == closest_allied["turn"]:
            closest_allied["ships"] += fleet.ship_count

    spawn_kore = 0
    for i in range(closest_allied["turn"]):
        max_spawn = max_ships_to_spawn(shipyard.turns_controlled + i)

        available_kore = me.available_kore() / len(me.shipyards)
        if available_kore - spawn_kore > max_spawn * spawn_cost:
            spawn_kore += max_spawn * spawn_cost
        else:
            return -1
    return spawn_kore + closest_allied["ships"]

@future_board
def rule_agent(board, info):
    board.sort_player_shipyards()
    defence1(board, info)
    defence2(board, info)
    defence4(board, info)
    defence5(board, info)
    defence3(board, info)
    attack2(board, info)
    spawn2(board, info)
    mine3(board, info)
    build3(board, info)
    spawn3(board, info)
    mine2(board, info)
    mine1(board, info)
    spawn1(board, info)