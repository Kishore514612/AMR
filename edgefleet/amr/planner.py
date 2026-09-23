"""
Space-Time A* Path Planner with Wait Actions and Reservation Constraints
"""
import heapq
import math
from typing import Dict, List, Optional, Set, Tuple
from edgefleet.amr.reservation import ReservationTable
from edgefleet.simulation.warehouse import WarehouseMap

def manhattan_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def euclidean_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

class PathPlanner:
    """
    Decentralized Path Planner supporting both Space-Time A* and Static A*.
    """
    def __init__(self, warehouse: WarehouseMap, robot_id: str):
        self.warehouse = warehouse
        self.robot_id = robot_id

    def plan_static_astar(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        temporary_blocked: Optional[Set[Tuple[int, int]]] = None
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Standard 2D A* on warehouse grid map.
        """
        if not self.warehouse.is_walkable(start) or not self.warehouse.is_walkable(goal):
            return None
        if temporary_blocked and (start in temporary_blocked or goal in temporary_blocked):
            return None
        if start == goal:
            return [start]

        open_set = []
        # (f_score, h_score, (x, y))
        heapq.heappush(open_set, (manhattan_distance(start, goal), manhattan_distance(start, goal), start))
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {start: 0.0}

        moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        while open_set:
            _, _, current = heapq.heappop(open_set)

            if current == goal:
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            for dx, dy in moves:
                neighbor = (current[0] + dx, current[1] + dy)

                if not self.warehouse.is_walkable(neighbor):
                    continue
                if temporary_blocked and neighbor in temporary_blocked:
                    continue

                tentative_g = g_score[current] + 1.0
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h = manhattan_distance(neighbor, goal)
                    f = tentative_g + h
                    heapq.heappush(open_set, (f, h, neighbor))

        return None

    def plan_space_time_astar(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        start_time: float,
        reservation_table: ReservationTable,
        time_step: float = 1.0,
        max_horizon_steps: int = 60,
        temporary_blocked: Optional[Set[Tuple[int, int]]] = None
    ) -> Optional[List[Tuple[Tuple[int, int], float]]]:
        """
        Space-Time A* Search.
        State: (x, y, t_step)
        Returns: List of ((x, y), t) where t is simulated timestamp.
        """
        if not self.warehouse.is_walkable(start) or not self.warehouse.is_walkable(goal):
            return None
        if temporary_blocked and (start in temporary_blocked or goal in temporary_blocked):
            return None

        # Node representation in heap: (f, h, t_step, (x, y))
        start_t_step = 0
        h_start = manhattan_distance(start, goal)
        open_set = []
        heapq.heappush(open_set, (h_start, h_start, start_t_step, start))

        # came_from: (x, y, t_step) -> (prev_x, prev_y, prev_t_step)
        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
        # g_score: (x, y, t_step) -> g
        g_score: Dict[Tuple[int, int, int], float] = {(start[0], start[1], start_t_step): 0.0}
        closed_set: Set[Tuple[int, int, int]] = set()

        # Available moves: 4 directions + WAIT (0, 0)
        moves = [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]
        max_expansions = 5000
        expansions = 0

        while open_set and expansions < max_expansions:
            expansions += 1
            f, h, current_t_step, current_pos = heapq.heappop(open_set)
            current_state = (current_pos[0], current_pos[1], current_t_step)

            if current_state in closed_set:
                continue
            closed_set.add(current_state)

            # Check if reached goal
            if current_pos == goal:
                # Reconstruct space-time trajectory
                path: List[Tuple[Tuple[int, int], float]] = []
                curr = current_state
                while curr in came_from:
                    pos = (curr[0], curr[1])
                    t = start_time + curr[2] * time_step
                    path.append((pos, t))
                    curr = came_from[curr]
                # Add start
                path.append((start, start_time))
                path.reverse()
                return path

            if current_t_step >= max_horizon_steps:
                continue

            next_t_step = current_t_step + 1
            t_from = start_time + current_t_step * time_step
            t_to = start_time + next_t_step * time_step

            for dx, dy in moves:
                next_pos = (current_pos[0] + dx, current_pos[1] + dy)
                next_state = (next_pos[0], next_pos[1], next_t_step)

                if next_state in closed_set:
                    continue

                # 1. Warehouse walkability & temporary blocks
                if not self.warehouse.is_walkable(next_pos):
                    continue
                if temporary_blocked and next_pos in temporary_blocked:
                    continue

                # 2. Vertex Conflict: Check if next_pos is reserved by another robot at [t_from, t_to]
                if reservation_table.is_cell_reserved(
                    next_pos, t_from, t_to, exclude_robot_id=self.robot_id
                ):
                    continue

                # 3. Edge Conflict: Swap conflict (head-on collision check)
                if dx != 0 or dy != 0:
                    if reservation_table.is_edge_conflict(
                        current_pos, next_pos, t_from, t_to, exclude_robot_id=self.robot_id
                    ):
                        continue

                # Transition cost: Moving = 1.0, Waiting = 1.05 (slight bias against unnecessary waiting)
                step_cost = 1.05 if (dx == 0 and dy == 0) else 1.0
                tentative_g = g_score[current_state] + step_cost

                if tentative_g < g_score.get(next_state, float('inf')):
                    came_from[next_state] = current_state
                    g_score[next_state] = tentative_g
                    h_next = manhattan_distance(next_pos, goal)
                    f_next = tentative_g + h_next
                    heapq.heappush(open_set, (f_next, h_next, next_t_step, next_pos))

        # Fallback to static A* if Space-Time search exceeds capacity
        static_path = self.plan_static_astar(start, goal, temporary_blocked)
        if static_path:
            return [(pos, start_time + idx * time_step) for idx, pos in enumerate(static_path)]
        return None
