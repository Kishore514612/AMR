"""
Unit tests for Conflict Detection & Deterministic Priority Tie-Breaking
"""
import pytest
from edgefleet.amr.conflict import ConflictDetector, ConflictType
from edgefleet.amr.state import TrajectoryPoint

def test_priority_calculation():
    # Higher task urgency gives higher score
    p_urgent = ConflictDetector.calculate_priority(task_urgency=5, wait_time=0.0, eta=5.0, battery=90.0)
    p_normal = ConflictDetector.calculate_priority(task_urgency=1, wait_time=0.0, eta=5.0, battery=90.0)
    assert p_urgent > p_normal

    # Longer wait time gives higher score
    p_waited = ConflictDetector.calculate_priority(task_urgency=1, wait_time=5.0, eta=5.0, battery=90.0)
    assert p_waited > p_normal

def test_deterministic_tie_breaking_equal_priority():
    # Force exact identical priorities, wait times, and ETAs
    r1_id = "R1"
    r2_id = "R2"

    winner_1, loser_1, reason_1 = ConflictDetector.resolve_conflict_deterministic(
        robot1_id=r1_id, priority1=15.0, wait_time1=2.0, eta1=5.0,
        robot2_id=r2_id, priority2=15.0, wait_time2=2.0, eta2=5.0
    )

    # From R2 perspective:
    winner_2, loser_2, reason_2 = ConflictDetector.resolve_conflict_deterministic(
        robot1_id=r2_id, priority1=15.0, wait_time1=2.0, eta1=5.0,
        robot2_id=r1_id, priority2=15.0, wait_time2=2.0, eta2=5.0
    )

    # BOTH MUST AGREE ON THE SAME WINNER
    assert winner_1 == "R1"
    assert winner_2 == "R1"
    assert loser_1 == "R2"
    assert loser_2 == "R2"

def test_trajectory_conflict_detection():
    # Trajectory 1: R1 moves (10, 5) -> (11, 5) -> (12, 5) at t=0, 1, 2
    traj1 = [
        TrajectoryPoint(x=10, y=5, t=0.0),
        TrajectoryPoint(x=11, y=5, t=1.0),
        TrajectoryPoint(x=12, y=5, t=2.0),
    ]

    # Trajectory 2: R2 moves (12, 5) -> (11, 5) -> (10, 5) at t=0, 1, 2 (Head-on swap!)
    traj2 = [
        TrajectoryPoint(x=12, y=5, t=0.0),
        TrajectoryPoint(x=11, y=5, t=1.0),
        TrajectoryPoint(x=10, y=5, t=2.0),
    ]

    conflict = ConflictDetector.detect_trajectory_conflict("R1", traj1, "R2", traj2)
    assert conflict is not None
    assert conflict.conflict_type in [ConflictType.VERTEX, ConflictType.SWAP]
