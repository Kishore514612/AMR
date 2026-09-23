"""
Warehouse Tasks & Item Moving Requests
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import time

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    EN_ROUTE_PICKUP = "EN_ROUTE_PICKUP"
    PICKED_UP = "PICKED_UP"
    EN_ROUTE_DROP = "EN_ROUTE_DROP"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass
class Task:
    id: str
    pickup_location: Tuple[int, int]
    drop_location: Tuple[int, int]
    priority: int = 1               # 1 (normal) to 5 (highest urgency)
    assigned_robot_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    description: str = ""

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return max(0.0, self.completed_at - self.started_at)
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pickup_location": list(self.pickup_location),
            "drop_location": list(self.drop_location),
            "priority": self.priority,
            "assigned_robot_id": self.assigned_robot_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "description": self.description
        }
