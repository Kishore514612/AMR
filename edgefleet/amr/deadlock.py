"""
Distributed Deadlock Detection & Resolution
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import time

@dataclass
class DeadlockEvent:
    cycle: List[str]
    detected_by: str
    victim_robot_id: str
    evasion_waypoint: Optional[Tuple[int, int]] = None
    timestamp: float = 0.0
    resolved: bool = False

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle,
            "detected_by": self.detected_by,
            "victim_robot_id": self.victim_robot_id,
            "evasion_waypoint": list(self.evasion_waypoint) if self.evasion_waypoint else None,
            "timestamp": round(self.timestamp, 2),
            "resolved": self.resolved
        }

class DeadlockDetector:
    @staticmethod
    def find_cycle(wait_graph: Dict[str, Optional[str]], start_node: str) -> Optional[List[str]]:
        """
        Detects if start_node is part of a circular wait graph.
        wait_graph: { 'R1': 'R2', 'R2': 'R3', 'R3': 'R1' }
        """
        visited: List[str] = []
        current = start_node

        while current and current in wait_graph:
            if current in visited:
                cycle_start_idx = visited.index(current)
                return visited[cycle_start_idx:] + [current]
            visited.append(current)
            current = wait_graph.get(current)

        return None

    @staticmethod
    def select_resolution_victim(
        cycle: List[str],
        priorities: Dict[str, float]
    ) -> str:
        """
        Deterministically selects the robot in the cycle that should yield or step aside.
        The robot with lowest priority (or lowest ID tie-breaker) yields.
        """
        unique_cycle_nodes = list(set(cycle))
        # Sort by priority ascending, then by ID descending (so deterministic)
        sorted_nodes = sorted(
            unique_cycle_nodes,
            key=lambda r_id: (priorities.get(r_id, 0.0), r_id)
        )
        return sorted_nodes[0]

    @staticmethod
    def find_evasion_cell(
        current_cell: Tuple[int, int],
        occupied_cells: Set[Tuple[int, int]],
        is_walkable_func
    ) -> Optional[Tuple[int, int]]:
        """
        Finds an open adjacent cell to step aside and clear the corridor.
        """
        candidates = [
            (current_cell[0] + 1, current_cell[1]),
            (current_cell[0] - 1, current_cell[1]),
            (current_cell[0], current_cell[1] + 1),
            (current_cell[0], current_cell[1] - 1),
            (current_cell[0] + 1, current_cell[1] + 1),
            (current_cell[0] - 1, current_cell[1] - 1),
        ]
        for c in candidates:
            if is_walkable_func(c) and c not in occupied_cells:
                return c
        return None
