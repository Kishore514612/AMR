"""
Integration tests for Dynamic Obstacle Injection & Real-Time Rerouting
"""
import pytest
import asyncio
from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.amr.robot import AMRRobot
from edgefleet.simulation.tasks import Task

@pytest.mark.asyncio
async def test_dynamic_obstacle_reroute():
    wh = WarehouseMap.create_default()
    r1 = AMRRobot("R1", initial_pos=(2, 2), warehouse=wh, port=9310)
    await r1.start()

    task = Task(id="TASK_REROUTE", pickup_location=(2, 2), drop_location=(28, 2))
    success = await r1.assign_task(task)
    assert success is True
    assert len(r1.state.planned_path) > 0

    # Step robot forward
    await r1.step(0.5)

    # Now inject dynamic obstacle directly on robot's next planned path
    next_cell = r1.state.planned_path[r1.target_waypoint_idx]
    wh.add_dynamic_obstacle(next_cell)

    initial_reroute_count = r1.state.reroute_count
    # Next step should detect blocked cell and trigger reroute
    await r1.step(0.1)

    assert r1.state.reroute_count >= initial_reroute_count
    assert next_cell not in r1.state.planned_path[r1.target_waypoint_idx:]

    await r1.stop()
