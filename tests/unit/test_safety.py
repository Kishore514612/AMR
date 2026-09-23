"""
Unit tests for Safety Controller & Collision Bubble
"""
import pytest
from edgefleet.amr.safety import SafetyController
from edgefleet.amr.state import Pose

def test_safety_proximity_violation():
    safety = SafetyController("R1", safety_radius=0.8)
    my_pose = Pose(x=10.0, y=5.0)

    # Peer at distance 0.4 (< 0.8)
    peer_poses = {"R2": Pose(x=10.4, y=5.0)}
    violation = safety.check_proximity(my_pose, peer_poses)
    assert violation is not None
    assert violation[0] == "R2"
    assert violation[1] == pytest.approx(0.4)

def test_safety_proximity_safe():
    safety = SafetyController("R1", safety_radius=0.8)
    my_pose = Pose(x=10.0, y=5.0)

    # Peer at distance 1.5 (> 0.8)
    peer_poses = {"R2": Pose(x=11.5, y=5.0)}
    assert safety.check_proximity(my_pose, peer_poses) is None

def test_will_collide_next_step():
    safety = SafetyController("R1", safety_radius=0.8)
    peer_poses = {"R2": Pose(x=10.0, y=5.0)}

    # Moving into (10.2, 5.0) which is 0.2 from R2
    assert safety.will_collide_next_step((10.2, 5.0), peer_poses) is True
    # Moving into (12.0, 5.0) which is 2.0 from R2
    assert safety.will_collide_next_step((12.0, 5.0), peer_poses) is False
