"""
Dynamic Obstacles and Aisle Blockages
"""
from dataclasses import dataclass
from typing import Tuple
import time

@dataclass
class DynamicObstacle:
    id: str
    position: Tuple[int, int]
    created_at: float = 0.0
    active: bool = True
    reason: str = "Spill / Temporary Obstacle"

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "position": list(self.position),
            "created_at": self.created_at,
            "active": self.active,
            "reason": self.reason
        }
