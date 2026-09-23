"""
Unit tests for Static A* and Space-Time A* Path Planner
"""
import pytest
from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.amr.planner import PathPlanner
from edgefleet.amr.reservation import ReservationTable, Reservation

def test_static_astar_pathfinding():
    wh = WarehouseMap.create_default()
    planner = PathPlanner(wh, "R1")

    # Path from (2, 2) to (28, 2)
    path = planner.plan_static_astar((2, 2), (28, 2))
    assert path is not None
    assert path[0] == (2, 2)
    assert path[-1] == (28, 2)

    # Path should not traverse shelves or walls
    for cell in path:
        assert wh.is_walkable(cell)

def test_static_astar_unreachable():
    wh = WarehouseMap.create_default()
    planner = PathPlanner(wh, "R1")

    # (0, 0) is a wall
    path = planner.plan_static_astar((0, 0), (28, 2))
    assert path is None

def test_space_time_astar_with_reservation_avoidance():
    wh = WarehouseMap.create_default()
    planner = PathPlanner(wh, "R1")
    res_table = ReservationTable("R1")

    start = (12, 9)
    goal = (16, 9)

    # Without reservation, direct horizontal path passes through (14, 9) at t=2.0
    # Let's reserve (14, 9) at t=2.0 by R2
    res_table.add_reservation(
        Reservation(
            id="RES_R2_X1",
            robot_id="R2",
            cell=(14, 9),
            start_time=1.5,
            end_time=2.5,
            zone_id="X1"
        )
    )

    st_path = planner.plan_space_time_astar(
        start=start,
        goal=goal,
        start_time=0.0,
        reservation_table=res_table
    )

    assert st_path is not None
    assert st_path[0][0] == start
    assert st_path[-1][0] == goal

    # Verify that at t in [1.5, 2.5], R1 is NOT at (14, 9)
    for pos, t in st_path:
        if 1.5 <= t <= 2.5:
            assert pos != (14, 9)
