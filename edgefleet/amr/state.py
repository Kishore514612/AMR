"""
AMR Robot State Models & Kinematics
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
import math
import time

class AMRStatus(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    NEGOTIATING = "NEGOTIATING"
    YIELDING = "YIELDING"
    REROUTING = "REROUTING"
    DEADLOCKED = "DEADLOCKED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    CHARGING = "CHARGING"
    OFFLINE = "OFFLINE"

@dataclass
class Pose:
    x: float
    y: float
    theta: float = 0.0  # radians (0 = East, pi/2 = North, etc.)

    @property
    def grid_cell(self) -> Tuple[int, int]:
        return (int(round(self.x)), int(round(self.y)))

    def distance_to(self, other: "Pose") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def to_dict(self) -> dict:
        return {"x": round(self.x, 3), "y": round(self.y, 3), "theta": round(self.theta, 3)}

@dataclass
class TrajectoryPoint:
    x: int
    y: int
    t: float  # projected arrival timestamp or relative time step

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "t": round(self.t, 2)}

@dataclass
class AMRState:
    robot_id: str
    pose: Pose
    status: AMRStatus = AMRStatus.IDLE
    velocity: float = 0.0
    battery: float = 100.0
    destination: Optional[Tuple[int, int]] = None
    current_task_id: Optional[str] = None
    planned_path: List[Tuple[int, int]] = field(default_factory=list)
    trajectory: List[TrajectoryPoint] = field(default_factory=list)
    eta: float = 0.0
    current_reservation_zone: Optional[str] = None
    waiting_for_robot_id: Optional[str] = None
    wait_time_accumulated: float = 0.0
    stalled_since: Optional[float] = None
    reroute_count: int = 0
    tasks_completed_count: int = 0
    conflicts_resolved_count: int = 0
    collisions_avoided_count: int = 0
    total_travel_distance: float = 0.0
    total_travel_time: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "pose": self.pose.to_dict(),
            "grid_cell": list(self.pose.grid_cell),
            "status": self.status.value,
            "velocity": round(self.velocity, 2),
            "battery": round(self.battery, 1),
            "destination": list(self.destination) if self.destination else None,
            "current_task_id": self.current_task_id,
            "planned_path": [list(p) for p in self.planned_path],
            "trajectory": [p.to_dict() for p in self.trajectory],
            "eta": round(self.eta, 2),
            "current_reservation_zone": self.current_reservation_zone,
            "waiting_for_robot_id": self.waiting_for_robot_id,
            "wait_time_accumulated": round(self.wait_time_accumulated, 2),
            "reroute_count": self.reroute_count,
            "tasks_completed_count": self.tasks_completed_count,
            "conflicts_resolved_count": self.conflicts_resolved_count,
            "collisions_avoided_count": self.collisions_avoided_count,
            "total_travel_distance": round(self.total_travel_distance, 2),
            "total_travel_time": round(self.total_travel_time, 2),
            "last_updated": self.last_updated
        }
