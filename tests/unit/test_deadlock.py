"""
Unit tests for Deadlock Detection & Resolution
"""
import pytest
from edgefleet.amr.deadlock import DeadlockDetector

def test_deadlock_cycle_detection():
    # Circular wait: R1 -> R2 -> R3 -> R1
    wait_graph = {
        "R1": "R2",
        "R2": "R3",
        "R3": "R1"
    }

    cycle = DeadlockDetector.find_cycle(wait_graph, "R1")
    assert cycle is not None
    assert "R1" in cycle
    assert "R2" in cycle
    assert "R3" in cycle

def test_deadlock_no_cycle():
    # Linear wait: R1 -> R2 -> None
    wait_graph = {
        "R1": "R2",
        "R2": None
    }
    assert DeadlockDetector.find_cycle(wait_graph, "R1") is None

def test_deadlock_victim_selection():
    cycle = ["R1", "R2", "R3"]
    priorities = {
        "R1": 25.0,
        "R2": 10.0, # Lowest priority
        "R3": 40.0
    }

    victim = DeadlockDetector.select_resolution_victim(cycle, priorities)
    assert victim == "R2"
