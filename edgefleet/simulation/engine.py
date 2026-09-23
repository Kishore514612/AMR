"""
Multi-AMR Simulation Engine & Physics Stepping Loop
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
import time
from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.simulation.tasks import Task, TaskStatus
from edgefleet.simulation.obstacles import DynamicObstacle
from edgefleet.amr.robot import AMRRobot
from edgefleet.amr.state import AMRStatus, Pose
from edgefleet.config import ROBOT_SAFETY_RADIUS

logger = logging.getLogger(__name__)

class SimulationEngine:
    """
    Simulation environment orchestrator.
    Manages warehouse layout, time stepping, and AMR agent life-cycles.
    NOTE: Does NOT make movement or conflict decisions for the robots!
    """
    def __init__(self, warehouse: Optional[WarehouseMap] = None):
        self.warehouse = warehouse or WarehouseMap.create_default()
        self.robots: Dict[str, AMRRobot] = {}
        self.tasks: Dict[str, Task] = {}
        self.dynamic_obstacles: Dict[str, DynamicObstacle] = {}

        self.sim_time: float = 0.0
        self.dt: float = 0.1
        self.is_running: bool = False
        self.speed_multiplier: float = 1.0

        # Global collision monitor for safety verification
        self.collision_events: List[dict] = []
        self._step_task: Optional[asyncio.Task] = None

    def add_robot(
        self,
        robot_id: str,
        initial_pos: Tuple[int, int],
        host: str = "127.0.0.1",
        port: int = 9000,
        battery: float = 100.0
    ) -> AMRRobot:
        robot = AMRRobot(
            robot_id=robot_id,
            initial_pos=initial_pos,
            warehouse=self.warehouse,
            host=host,
            port=port,
            battery=battery
        )
        self.robots[robot_id] = robot
        return robot

    def add_task(self, task: Task) -> None:
        self.tasks[task.id] = task

    def add_dynamic_obstacle(self, pos: Tuple[int, int], reason: str = "Obstacle") -> Optional[DynamicObstacle]:
        if self.warehouse.add_dynamic_obstacle(pos):
            obs_id = f"OBS_{pos[0]}_{pos[1]}"
            obs = DynamicObstacle(id=obs_id, position=pos, reason=reason)
            self.dynamic_obstacles[obs_id] = obs
            return obs
        return None

    def remove_dynamic_obstacle(self, pos: Tuple[int, int]) -> bool:
        if self.warehouse.remove_dynamic_obstacle(pos):
            obs_id = f"OBS_{pos[0]}_{pos[1]}"
            if obs_id in self.dynamic_obstacles:
                del self.dynamic_obstacles[obs_id]
            return True
        return False

    async def initialize_fleet_p2p(self) -> None:
        """Starts all AMR TCP servers and registers mutual discovery entries."""
        for robot in self.robots.values():
            await robot.start()

        # Connect mutual discovery tables
        for r1_id, r1 in self.robots.items():
            for r2_id, r2 in self.robots.items():
                if r1_id != r2_id:
                    r1.discovery_table.register_peer(
                        robot_id=r2_id,
                        host=r2.host,
                        port=r2.port,
                        pos=(r2.state.pose.x, r2.state.pose.y)
                    )

    async def step(self) -> None:
        """Single simulation step for all AMRs."""
        self.sim_time += self.dt

        # Ensure each AMR has current neighbor poses
        for r1_id, r1 in self.robots.items():
            for r2_id, r2 in self.robots.items():
                if r1_id != r2_id:
                    r1.peer_poses[r2_id] = (r2.state.pose.x, r2.state.pose.y)
                    r1.peer_statuses[r2_id] = r2.state.status.value

        # Advance each AMR independently
        for robot in self.robots.values():
            await robot.step(self.dt)

        # Global Safety Check (Ground truth verification)
        self._verify_zero_collisions()

    def _verify_zero_collisions(self) -> None:
        """Independent ground-truth collision check."""
        robot_list = list(self.robots.values())
        for i in range(len(robot_list)):
            for j in range(i + 1, len(robot_list)):
                r1, r2 = robot_list[i], robot_list[j]
                dist = r1.state.pose.distance_to(r2.state.pose)
                # Physical collision is when bounding circles overlap (dist < 0.6)
                if dist < 0.6:
                    event = {
                        "sim_time": round(self.sim_time, 2),
                        "robot1": r1.robot_id,
                        "robot2": r2.robot_id,
                        "distance": round(dist, 3),
                        "pos1": (round(r1.state.pose.x, 2), round(r1.state.pose.y, 2)),
                        "pos2": (round(r2.state.pose.x, 2), round(r2.state.pose.y, 2))
                    }
                    self.collision_events.append(event)
                    logger.critical(f"PHYSICAL COLLISION DETECTED at t={self.sim_time:.1f}: {event}")

    async def run_loop(self) -> None:
        """Continuous simulation runner loop."""
        self.is_running = True
        while self.is_running:
            start_t = time.time()
            await self.step()
            elapsed = time.time() - start_t
            target_delay = (self.dt / max(0.1, self.speed_multiplier))
            sleep_time = max(0.001, target_delay - elapsed)
            await asyncio.sleep(sleep_time)

    def start_loop(self) -> None:
        if not self._step_task or self._step_task.done():
            self._step_task = asyncio.create_task(self.run_loop())

    async def stop(self) -> None:
        self.is_running = False
        if self._step_task:
            self._step_task.cancel()
        for robot in self.robots.values():
            await robot.stop()

    def get_summary_metrics(self) -> dict:
        total_wait_time = sum(r.state.wait_time_accumulated for r in self.robots.values())
        total_conflicts = sum(r.state.conflicts_resolved_count for r in self.robots.values())
        total_reroutes = sum(r.state.reroute_count for r in self.robots.values())
        total_completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        completed_durations = [t.duration for t in self.tasks.values() if t.duration is not None]
        avg_task_duration = (sum(completed_durations) / len(completed_durations)) if completed_durations else 0.0

        return {
            "sim_time": round(self.sim_time, 2),
            "active_robots": len(self.robots),
            "total_tasks": len(self.tasks),
            "completed_tasks": total_completed,
            "avg_task_duration": round(avg_task_duration, 2),
            "total_wait_time": round(total_wait_time, 2),
            "total_conflicts_resolved": total_conflicts,
            "total_reroutes": total_reroutes,
            "collision_count": len(self.collision_events),
            "collisions": self.collision_events
        }

    def to_dict(self) -> dict:
        return {
            "sim_time": round(self.sim_time, 2),
            "is_running": self.is_running,
            "speed_multiplier": self.speed_multiplier,
            "warehouse": self.warehouse.to_dict(),
            "robots": {r_id: r.to_dict() for r_id, r in self.robots.items()},
            "tasks": {t_id: t.to_dict() for t_id, t in self.tasks.items()},
            "dynamic_obstacles": {k: v.to_dict() for k, v in self.dynamic_obstacles.items()},
            "metrics": self.get_summary_metrics()
        }
