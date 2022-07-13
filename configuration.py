from typing import Dict

class Configuration(Dict[str, any]):
    @property
    def agent_timeout(self) -> float:
        """Maximum runtime (seconds) to initialize an agent."""
        return self["agentTimeout"]

    @property
    def starting_kore(self) -> int:
        """The starting amount of kore available on the board. default=2750"""
        return self["startingKore"]

    @property
    def size(self) -> int:
        """The number of cells vertically and horizontally on the board. default=21"""
        return self["size"]

    @property
    def spawn_cost(self) -> int:
        """The amount of kore to spawn a new ship. default=10"""
        return self["spawnCost"]

    @property
    def convert_cost(self) -> int:
        """The amount of ships needed from a fleet to create a shipyard. default=50"""
        return self["convertCost"]

    @property
    def regen_rate(self) -> float:
        """The rate kore regenerates on the board. default=0.02"""
        return self["regenRate"]

    @property
    def max_cell_kore(self) -> int:
        """The maximum kore that can be in any cell. default=500"""
        return self["maxRegenCellKore"]

    @property
    def random_seed(self) -> int:
        """The seed to the random number generator (0 means no seed)."""
        return self["randomSeed"]