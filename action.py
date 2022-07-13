from typing import Optional
from helpers import max_ships_to_spawn, max_flight_plan_len_for_ship_count


class Action:
    def __init__(self, action_type: str, command: str, num_ships: int, flight_plan: Optional[str]):
        self._action_type = action_type
        self._command = command
        self._num_ships = num_ships
        self._flight_plan = flight_plan

    @staticmethod
    def spawn(*, num_ships: int, turns_controlled: int) -> "Action":
        assert num_ships > 0, "Number of ships must be positive"
        assert isinstance(num_ships, int), "Number of ships must be integer"

        if num_ships > max_ships_to_spawn(turns_controlled):
            num_ships = max_ships_to_spawn(turns_controlled)

        return Action("SPAWN", f"SPAWN_{num_ships}", num_ships, None)

    @staticmethod
    def launch(*, num_ships: int, flight_plan: str) -> "Action":
        assert num_ships > 0, "Number of ships must be positive"
        assert isinstance(num_ships, int), "Number of ships must be integer"
        assert flight_plan[0].isalpha() and flight_plan[0] in "NESW", "Flight plan must start with NESW"

        max_flight_plan_len = max_flight_plan_len_for_ship_count(num_ships)
        if len(flight_plan) > max_flight_plan_len:
            truncated_flight_plan = flight_plan[:max_flight_plan_len]
            print(f"Flight plan will be truncated: FROM {flight_plan} TO {truncated_flight_plan}")
            flight_plan = truncated_flight_plan

        return Action("LAUNCH", f"LAUNCH_{num_ships}_{flight_plan}", num_ships, flight_plan)

    @property
    def action_type(self) -> str:
        return self._action_type
    
    @property
    def command(self) -> str:
        return self._command
    
    @property
    def num_ships(self) -> int:
        return self._num_ships
    
    @property
    def flight_plan(self) -> Optional[str]:
        return self._flight_plan
    
    def __repr__(self):
        return f"Action(command={self.command})"