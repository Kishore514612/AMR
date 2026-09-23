"""
Distributed Conflict Detection and Deterministic Priority Tie-Breaking
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import hashlib
from edgefleet.amr.state import AMRState, TrajectoryPoint
from edgefleet.config import (
    PRIORITY_WEIGHT_URGENCY,
    PRIORITY_WEIGHT_WAIT_TIME,
    PRIORITY_WEIGHT_ETA,
    PRIORITY_WEIGHT_BATTERY
)

class ConflictType(str, Enum):
    VERTEX = "VERTEX"           # Simultaneous occupation of same cell
    SWAP = "SWAP"               # Head-on exchange of adjacent cells
    CRITICAL_ZONE = "CRITICAL_ZONE" # Both entering same intersection / bottleneck
    DEADLOCK = "DEADLOCK"       # Circular mutual blocking

@dataclass
class PathConflict:
    conflict_type: ConflictType
    cell: Tuple[int, int]
    t_conflict: float
    robot1_id: str
    robot2_id: str
    critical_zone_id: Optional[str] = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "conflict_type": self.conflict_type.value,
            "cell": list(self.cell),
            "t_conflict": round(self.t_conflict, 2),
            "robot1_id": self.robot1_id,
            "robot2_id": self.robot2_id,
            "critical_zone_id": self.critical_zone_id,
            "description": self.description
        }

class ConflictDetector:
    @staticmethod
    def calculate_priority(
        task_urgency: int = 1,
        wait_time: float = 0.0,
        eta: float = 10.0,
        battery: float = 100.0,
        w_urgency: float = PRIORITY_WEIGHT_URGENCY,
        w_wait: float = PRIORITY_WEIGHT_WAIT_TIME,
        w_eta: float = PRIORITY_WEIGHT_ETA,
        w_battery: float = PRIORITY_WEIGHT_BATTERY
    ) -> float:
        """
        Calculates scalar priority value.
        Higher score = higher priority.
        """
        priority = (
            w_urgency * float(task_urgency)
            + w_wait * float(wait_time)
            - w_eta * float(eta)
            + w_battery * float(100.0 - battery)
        )
        return round(priority, 4)

    @staticmethod
    def resolve_conflict_deterministic(
        robot1_id: str,
        priority1: float,
        wait_time1: float,
        eta1: float,
        robot2_id: str,
        priority2: float,
        wait_time2: float,
        eta2: float
    ) -> Tuple[str, str, str]:
        """
        Deterministic tie-breaking resolution.
        Returns: (winner_id, loser_id, reason)
        Both robots running this independently ALWAYS return identical results.
        """
        epsilon = 0.001

        # 1. Primary: Priority Score
        if abs(priority1 - priority2) >= epsilon:
            if priority1 > priority2:
                return robot1_id, robot2_id, f"Priority score: {priority1:.2f} > {priority2:.2f}"
            else:
                return robot2_id, robot1_id, f"Priority score: {priority2:.2f} > {priority1:.2f}"

        # 2. Secondary: Wait Time (robot waiting longer gets priority)
        if abs(wait_time1 - wait_time2) >= 0.2:
            if wait_time1 > wait_time2:
                return robot1_id, robot2_id, f"Wait time: {wait_time1:.1f}s > {wait_time2:.1f}s"
            else:
                return robot2_id, robot1_id, f"Wait time: {wait_time2:.1f}s > {wait_time1:.1f}s"

        # 3. Tertiary: ETA (robot closer to completing goal gets priority)
        if abs(eta1 - eta2) >= 0.2:
            if eta1 < eta2:
                return robot1_id, robot2_id, f"Closer ETA: {eta1:.1f}s < {eta2:.1f}s"
            else:
                return robot2_id, robot1_id, f"Closer ETA: {eta2:.1f}s < {eta1:.1f}s"

        # 4. Quaternary: Deterministic Stable Robot ID Ordering (lexicographical or hash)
        if robot1_id < robot2_id:
            return robot1_id, robot2_id, f"Deterministic ID tie-breaker ({robot1_id} < {robot2_id})"
        else:
            return robot2_id, robot1_id, f"Deterministic ID tie-breaker ({robot2_id} < {robot1_id})"

    @staticmethod
    def detect_trajectory_conflict(
        robot1_id: str,
        traj1: List[TrajectoryPoint],
        robot2_id: str,
        traj2: List[TrajectoryPoint],
        time_tolerance: float = 0.8
    ) -> Optional[PathConflict]:
        """
        Finds first spatial-temporal conflict between two trajectories.
        """
        if not traj1 or not traj2:
            return None

        # Check vertex collisions
        for p1 in traj1:
            for p2 in traj2:
                if (p1.x, p1.y) == (p2.x, p2.y) and abs(p1.t - p2.t) <= time_tolerance:
                    return PathConflict(
                        conflict_type=ConflictType.VERTEX,
                        cell=(p1.x, p1.y),
                        t_conflict=(p1.t + p2.t) / 2.0,
                        robot1_id=robot1_id,
                        robot2_id=robot2_id,
                        description=f"Vertex collision predicted at cell ({p1.x}, {p1.y}) at t={p1.t:.1f}"
                    )

        # Check swap / head-on collisions
        for i in range(len(traj1) - 1):
            p1_curr, p1_next = traj1[i], traj1[i + 1]
            for j in range(len(traj2) - 1):
                p2_curr, p2_next = traj2[j], traj2[j + 1]

                if (p1_curr.x, p1_curr.y) == (p2_next.x, p2_next.y) and \
                   (p1_next.x, p1_next.y) == (p2_curr.x, p2_curr.y):
                    # Check temporal overlap
                    if max(p1_curr.t, p2_curr.t) < min(p1_next.t, p2_next.t) + time_tolerance:
                        return PathConflict(
                            conflict_type=ConflictType.SWAP,
                            cell=(p1_next.x, p1_next.y),
                            t_conflict=(p1_next.t + p2_next.t) / 2.0,
                            robot1_id=robot1_id,
                            robot2_id=robot2_id,
                            description=f"Head-on swap conflict between ({p1_curr.x},{p1_curr.y}) and ({p1_next.x},{p1_next.y})"
                        )

        return None
