"""
Unit tests for Space-Time Reservation Table
"""
import pytest
from edgefleet.amr.reservation import ReservationTable, Reservation

def test_reservation_overlap():
    r1 = Reservation(
        id="R1_RES",
        robot_id="R1",
        cell=(10, 5),
        start_time=2.0,
        end_time=5.0
    )

    # Overlapping interval [3.0, 4.0]
    assert r1.overlaps_with((10, 5), 3.0, 4.0) is True
    # Non-overlapping interval [6.0, 8.0]
    assert r1.overlaps_with((10, 5), 6.0, 8.0) is False
    # Different cell
    assert r1.overlaps_with((10, 6), 3.0, 4.0) is False

def test_reservation_table_query_and_release():
    table = ReservationTable("R1")

    res = Reservation(
        id="R2_RES",
        robot_id="R2",
        cell=(14, 9),
        start_time=1.0,
        end_time=4.0,
        zone_id="X1"
    )
    table.add_reservation(res)

    # Conflict check from R1 perspective
    conflict = table.is_cell_reserved((14, 9), 2.0, 3.0, exclude_robot_id="R1")
    assert conflict is not None
    assert conflict.robot_id == "R2"

    # Exclude R2 perspective
    assert table.is_cell_reserved((14, 9), 2.0, 3.0, exclude_robot_id="R2") is None

    # Release by R2
    table.release_robot_reservations("R2")
    assert table.is_cell_reserved((14, 9), 2.0, 3.0, exclude_robot_id="R1") is None

def test_clean_expired_reservations():
    table = ReservationTable("R1")
    res = Reservation(
        id="R2_OLD",
        robot_id="R2",
        cell=(14, 9),
        start_time=1.0,
        end_time=3.0
    )
    table.add_reservation(res)

    table.clean_expired(current_sim_time=5.0)
    assert len(table.get_all_active()) == 0
