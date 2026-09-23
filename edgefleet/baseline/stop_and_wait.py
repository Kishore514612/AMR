"""
Stop-and-Wait Multi-Robot Baseline
"""
from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Tuple
import time
from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.simulation.tasks import Task, TaskStatus
from edgefleet.amr.planner import PathPlanner
from edgefleet.amr.state import Pose
from edgefleet.config import ROBOT_MAX_SPEED, ROBOT_SAFETY_RADIUS

@dataclass
class BaselineRobot:
    robot_id: str
    pose: Pose
    destination: Optional[Tuple[int, int]] = None
    planned_path: List[Tuple[int, int]] = field(default_factory=list)
    target_waypoint_idx: int = 0
    current_task: Optional[Task] = None
    status: str = "IDLE"  # "IDLE", "MOVING", "STOPPED_WAITING"
    wait_time_accumulated: float = 0.0
    tasks_completed: int = 0

class StopAndWaitSimulator:
    """
    Traditional Stop-and-Wait multi-robot coordinator.
    Whenever another robot conflicts or is in proximity, the robot STOPS,
    WAITS until the obstacle/robot clears, then resumes.
    """
    def __init__(self, warehouse: Optional[WarehouseMap] = None):
        self.warehouse = warehouse or WarehouseMap.create_default()
        self.robots: Dict[str, BaselineRobot] = {}
        self.tasks: Dict[str, Task] = {}
        self.sim_time: float = 0.0
        self.dt: float = 0.1
        self.planner = PathPlanner(self.warehouse, "BASELINE")
        self.collision_events: List[dict] = []

    def add_robot(self, robot_id: str, initial_pos: Tuple[int, int]) -> BaselineRobot:
        robot = BaselineRobot(
            robot_id=robot_id,
            pose=Pose(x=float(initial_pos[0]), y=float(initial_pos[1]))
        )
        self.robots[robot_id] = robot
        return robot

    def add_task(self, task: Task) -> None:
        self.tasks[task.id] = task

    def assign_task(self, robot_id: str, task: Task) -> bool:
        robot = self.robots.get(robot_id)
        if not robot:
            return False

        robot.current_task = task
        task.assigned_robot_id = robot_id
        task.status = TaskStatus.ASSIGNED
        task.started_at = self.sim_time

        start_cell = robot.pose.grid_cell
        destination = task.pickup_location if start_cell != task.pickup_location else task.drop_location
        robot.destination = destination

        # Plan standard static A* path
        path = self.planner.plan_static_astar(start_cell, destination)
        if path:
            robot.planned_path = path
            robot.target_waypoint_idx = 1 if len(path) > 1 else 0
            robot.status = "MOVING"
            return True
        return False

    def step(self) -> None:
        """Simulates one time step with Stop-and-Wait behavior."""
        self.sim_time += self.dt

        for robot in self.robots.values():
            if robot.status in ["MOVING", "STOPPED_WAITING"] and robot.planned_path:
                if robot.target_waypoint_idx < len(robot.planned_path):
                    target_cell = robot.planned_path[robot.target_waypoint_idx]
                    target_x, target_y = float(target_cell[0]), float(target_cell[1])

                    # Check if target_cell or proximity is blocked by another robot
                    is_blocked = False
                    for peer_id, peer in self.robots.items():
                        if peer_id == robot.robot_id:
                            continue
                        dist = math.hypot(target_x - peer.pose.x, target_y - peer.pose.y)
                        if dist < ROBOT_SAFETY_RADIUS:
                            is_blocked = True
                            break

                    if is_blocked:
                        # STOP AND WAIT
                        robot.status = "STOPPED_WAITING"
                        robot.wait_time_accumulated += self.dt
                        continue

                    # Otherwise, proceed
                    robot.status = "MOVING"
                    dx = target_x - robot.pose.x
                    dy = target_y - robot.pose.y
                    dist = math.hypot(dx, dy)
                    step_dist = ROBOT_MAX_SPEED * self.dt

                    if dist <= step_dist or dist < 0.05:
                        robot.pose.x = target_x
                        robot.pose.y = target_y
                        robot.target_waypoint_idx += 1

                        if robot.target_waypoint_idx >= len(robot.planned_path):
                            self._on_reach_destination(robot)
                    else:
                        robot.pose.x += (dx / dist) * step_dist
                        robot.pose.y += (dy / dist) * step_dist

        # Collision verification
        self._verify_zero_collisions()

    def _on_reach_destination(self, robot: BaselineRobot) -> None:
        current_cell = robot.pose.grid_cell
        if robot.current_task:
            if current_cell == robot.current_task.pickup_location:
                robot.current_task.status = TaskStatus.EN_ROUTE_DROP
                robot.destination = robot.current_task.drop_location
                path = self.planner.plan_static_astar(current_cell, robot.destination)
                if path:
                    robot.planned_path = path
                    robot.target_waypoint_idx = 1 if len(path) > 1 else 0
                    robot.status = "MOVING"
            elif current_cell == robot.current_task.drop_location:
                robot.current_task.status = TaskStatus.COMPLETED
                robot.current_task.completed_at = self.sim_time
                robot.tasks_completed += 1
                robot.current_task = None
                robot.status = "IDLE"
                robot.planned_path = []
        else:
            robot.status = "IDLE"

    def _verify_zero_collisions(self) -> None:
        robot_list = list(self.robots.values())
        for i in range(len(robot_list)):
            for j in range(i + 1, len(robot_list)):
                r1, r2 = robot_list[i], robot_list[j]
                dist = r1.pose.distance_to(r2.pose)
                if dist < 0.6:
                    self.collision_events.append({
                        "sim_time": self.sim_time,
                        "robot1": r1.robot_id,
                        "robot2": r2.robot_id,
                        "distance": dist
                    })

    def run_until_complete(self, max_sim_time: float = 300.0) -> dict:
        """Runs the baseline simulation until all tasks are completed."""
        while self.sim_time < max_sim_time:
            all_done = all(t.status == TaskStatus.COMPLETED for t in self.tasks.values()) if self.tasks else False
            if all_done:
                break
            self.step()

        total_wait_time = sum(r.wait_time_accumulated for r in self.robots.values())
        completed_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)

        return {
            "total_sim_time": round(self.sim_time, 2),
            "completed_tasks": completed_tasks,
            "total_tasks": len(self.tasks),
            "total_wait_time": round(total_wait_time, 2),
            "collision_count": len(self.collision_events)
        }
