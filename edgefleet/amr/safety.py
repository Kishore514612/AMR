"""
Local AMR Safety Controller & Collision Prevention
"""
import math
from typing import Dict, List, Optional, Tuple
from edgefleet.amr.state import Pose, AMRState
from edgefleet.config import ROBOT_SAFETY_RADIUS

class SafetyController:
    """
    Final local safety shield running on every control cycle.
    Ensures zero physical collisions even if high-level networking or negotiation is delayed.
    """
    def __init__(self, robot_id: str, safety_radius: float = ROBOT_SAFETY_RADIUS):
        self.robot_id = robot_id
        self.safety_radius = safety_radius

    def check_proximity(
        self,
        my_pose: Pose,
        peer_poses: Dict[str, Pose]
    ) -> Optional[Tuple[str, float]]:
        """
        Checks if any peer is violating the minimum safety envelope.
        Returns: (violating_robot_id, distance) if unsafe, else None.
        """
        for peer_id, pose in peer_poses.items():
            if peer_id == self.robot_id:
                continue
            dist = my_pose.distance_to(pose)
            if dist < self.safety_radius:
                return (peer_id, dist)
        return None

    def will_collide_next_step(
        self,
        next_pos: Tuple[float, float],
        peer_poses: Dict[str, Pose],
        peer_velocities: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Predicts if moving to next_pos would breach safety radius with any peer.
        """
        for peer_id, pose in peer_poses.items():
            if peer_id == self.robot_id:
                continue
            dist = math.hypot(next_pos[0] - pose.x, next_pos[1] - pose.y)
            if dist < self.safety_radius:
                return True
        return False
