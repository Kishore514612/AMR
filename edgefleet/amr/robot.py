"""
Autonomous Mobile Robot (AMR) Agent Core
"""
import asyncio
import logging
import math
from typing import Dict, List, Optional, Set, Tuple
import time
from edgefleet.amr.state import Pose, AMRState, AMRStatus, TrajectoryPoint
from edgefleet.amr.planner import PathPlanner
from edgefleet.amr.reservation import ReservationTable, Reservation
from edgefleet.amr.safety import SafetyController
from edgefleet.amr.coordinator import AMRCoordinator
from edgefleet.amr.conflict import ConflictDetector
from edgefleet.amr.deadlock import DeadlockDetector
from edgefleet.network.discovery import DiscoveryTable
from edgefleet.network.peer import P2PNode
from edgefleet.network.heartbeat import HeartbeatManager
from edgefleet.network.protocol import P2PMessage, MessageType
from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.simulation.tasks import Task, TaskStatus
from edgefleet.config import (
    DEFAULT_COMMUNICATION_RADIUS,
    ROBOT_MAX_SPEED,
    ROBOT_SAFETY_RADIUS,
    BATTERY_CONSUMPTION_RATE,
    DEADLOCK_WAIT_THRESHOLD,
    MAX_REROUTE_ATTEMPTS
)

logger = logging.getLogger(__name__)

class AMRRobot:
    """
    Independent Decentralized AMR Agent.
    Runs its own path planner, P2P network server, safety checks, and state machine.
    """
    def __init__(
        self,
        robot_id: str,
        initial_pos: Tuple[int, int],
        warehouse: WarehouseMap,
        host: str = "127.0.0.1",
        port: int = 9000,
        comm_radius: float = DEFAULT_COMMUNICATION_RADIUS,
        battery: float = 100.0
    ):
        self.robot_id = robot_id
        self.host = host
        self.port = port
        self.warehouse = warehouse
        self.comm_radius = comm_radius

        # Subsystems
        self.state = AMRState(
            robot_id=robot_id,
            pose=Pose(x=float(initial_pos[0]), y=float(initial_pos[1])),
            battery=battery,
            status=AMRStatus.IDLE
        )
        self.discovery_table = DiscoveryTable(robot_id, comm_radius=comm_radius)
        self.reservation_table = ReservationTable(robot_id)
        self.planner = PathPlanner(warehouse, robot_id)
        self.safety = SafetyController(robot_id)
        self.coordinator = AMRCoordinator(self)

        self.p2p_node = P2PNode(
            robot_id=robot_id,
            host=host,
            port=port,
            discovery_table=self.discovery_table,
            message_handler=self.coordinator.handle_message
        )
        self.heartbeat_manager = HeartbeatManager(
            p2p_node=self.p2p_node,
            get_current_pos_callback=lambda: (self.state.pose.x, self.state.pose.y),
            get_status_callback=lambda: self.state.status.value
        )

        # Peer information maintained locally
        self.peer_poses: Dict[str, Tuple[float, float]] = {}
        self.peer_statuses: Dict[str, str] = {}
        self.peer_batteries: Dict[str, float] = {}
        self.peer_trajectories: Dict[str, List[TrajectoryPoint]] = {}

        # Execution state
        self.current_task: Optional[Task] = None
        self.target_waypoint_idx = 0
        self.current_sim_time = 0.0
        self._running = False
        self._control_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Starts P2P networking and background loops."""
        self._running = True
        await self.p2p_node.start()
        self.heartbeat_manager.start()

        # Announce presence to known or local subnet peers
        discovery_msg = P2PMessage(
            message_type=MessageType.DISCOVERY,
            sender_id=self.robot_id,
            payload={
                "host": self.host,
                "port": self.port,
                "status": self.state.status.value,
                "position": [self.state.pose.x, self.state.pose.y]
            }
        )
        await self.p2p_node.broadcast_to_all(discovery_msg)

    async def stop(self) -> None:
        """Gracefully halts robot."""
        self._running = False
        if self._control_task:
            self._control_task.cancel()
        self.heartbeat_manager.stop()
        await self.p2p_node.stop()

    def get_current_priority(self) -> float:
        task_urgency = self.current_task.priority if self.current_task else 1
        return ConflictDetector.calculate_priority(
            task_urgency=task_urgency,
            wait_time=self.state.wait_time_accumulated,
            eta=self.state.eta,
            battery=self.state.battery
        )

    def get_trajectory_bounding_box(self) -> Optional[Tuple[float, float, float, float]]:
        if not self.state.planned_path:
            return None
        xs = [p[0] for p in self.state.planned_path]
        ys = [p[1] for p in self.state.planned_path]
        return (min(xs), min(ys), max(xs), max(ys))

    async def assign_task(self, task: Task) -> bool:
        """Assigns a new task and plans the space-time route to the destination."""
        self.current_task = task
        self.state.current_task_id = task.id
        task.assigned_robot_id = self.robot_id
        task.status = TaskStatus.ASSIGNED
        task.started_at = time.time()

        # Plan to pickup first if not already there, else to drop
        current_cell = self.state.pose.grid_cell
        target_destination = task.pickup_location if current_cell != task.pickup_location else task.drop_location
        self.state.destination = target_destination

        return await self.plan_and_broadcast_route(target_destination)

    async def plan_and_broadcast_route(self, destination: Tuple[int, int]) -> bool:
        """Computes Space-Time A* path and announces intent to relevant local neighbors."""
        start_cell = self.state.pose.grid_cell
        self.reservation_table.clean_expired(self.current_sim_time)

        space_time_path = self.planner.plan_space_time_astar(
            start=start_cell,
            goal=destination,
            start_time=self.current_sim_time,
            reservation_table=self.reservation_table
        )

        if not space_time_path or len(space_time_path) <= 1:
            # If already at destination
            if start_cell == destination:
                self.state.planned_path = [destination]
                self.state.trajectory = [TrajectoryPoint(x=destination[0], y=destination[1], t=self.current_sim_time)]
                self.state.status = AMRStatus.IDLE
                self.state.eta = 0.0
                return True
            logger.warning(f"[{self.robot_id}] No path found to {destination}")
            self.state.status = AMRStatus.IDLE
            return False

        self.state.planned_path = [pt[0] for pt in space_time_path]
        self.state.trajectory = [TrajectoryPoint(x=pt[0][0], y=pt[0][1], t=pt[1]) for pt in space_time_path]
        self.state.eta = max(0.0, space_time_path[-1][1] - self.current_sim_time)
        self.state.status = AMRStatus.MOVING
        self.target_waypoint_idx = 1 if len(self.state.planned_path) > 1 else 0

        # Broadcast INTENT_UPDATE only to relevant neighbors (Scalability O(K) filter)
        my_bbox = self.get_trajectory_bounding_box()
        intent_msg = P2PMessage(
            message_type=MessageType.INTENT_UPDATE,
            sender_id=self.robot_id,
            payload={
                "position": [self.state.pose.x, self.state.pose.y],
                "destination": list(destination),
                "planned_path": [list(p) for p in self.state.planned_path],
                "trajectory": [tp.to_dict() for tp in self.state.trajectory],
                "eta": self.state.eta,
                "priority": self.get_current_priority(),
                "battery": self.state.battery
            }
        )
        await self.p2p_node.broadcast_to_relevant(
            intent_msg,
            my_pos=(self.state.pose.x, self.state.pose.y),
            my_bbox=my_bbox
        )

        # Reserve critical zones on route
        for cell, t in space_time_path:
            zone = self.warehouse.get_critical_zone_for_cell(cell)
            if zone:
                res = Reservation(
                    id=f"{self.robot_id}_{zone.id}_{t}",
                    robot_id=self.robot_id,
                    cell=cell,
                    start_time=t - 0.5,
                    end_time=t + 1.5,
                    zone_id=zone.id
                )
                self.reservation_table.add_reservation(res)
                # Request reservation broadcast to relevant peers
                res_msg = P2PMessage(
                    message_type=MessageType.RESERVATION_REQUEST,
                    sender_id=self.robot_id,
                    payload={
                        "cell": list(cell),
                        "start_time": t - 0.5,
                        "end_time": t + 1.5,
                        "zone_id": zone.id
                    }
                )
                await self.p2p_node.broadcast_to_relevant(
                    res_msg,
                    my_pos=(self.state.pose.x, self.state.pose.y),
                    my_bbox=my_bbox
                )

        return True

    async def replan_around_peer(self, peer_id: str) -> bool:
        """Replans path avoiding peer's trajectory or dynamic obstacles."""
        if not self.state.destination:
            return False
        logger.info(f"[{self.robot_id}] Replanning route around {peer_id}...")
        self.state.reroute_count += 1

        start_cell = self.state.pose.grid_cell
        self.reservation_table.clean_expired(self.current_sim_time)

        space_time_path = self.planner.plan_space_time_astar(
            start=start_cell,
            goal=self.state.destination,
            start_time=self.current_sim_time,
            reservation_table=self.reservation_table
        )

        if not space_time_path or len(space_time_path) <= 1:
            if start_cell == self.state.destination:
                self.state.status = AMRStatus.IDLE
                return True
            # No alternative path: maintain YIELDING status until peer passes
            self.state.status = AMRStatus.YIELDING
            return False

        self.state.planned_path = [pt[0] for pt in space_time_path]
        self.state.trajectory = [TrajectoryPoint(x=pt[0][0], y=pt[0][1], t=pt[1]) for pt in space_time_path]
        self.state.eta = max(0.0, space_time_path[-1][1] - self.current_sim_time)
        self.target_waypoint_idx = 1 if len(self.state.planned_path) > 1 else 0
        self.state.status = AMRStatus.MOVING

        # Broadcast updated intent
        my_bbox = self.get_trajectory_bounding_box()
        intent_msg = P2PMessage(
            message_type=MessageType.INTENT_UPDATE,
            sender_id=self.robot_id,
            payload={
                "position": [self.state.pose.x, self.state.pose.y],
                "destination": list(self.state.destination),
                "planned_path": [list(p) for p in self.state.planned_path],
                "trajectory": [tp.to_dict() for tp in self.state.trajectory],
                "eta": self.state.eta,
                "priority": self.get_current_priority(),
                "battery": self.state.battery
            }
        )
        await self.p2p_node.broadcast_to_relevant(
            intent_msg,
            my_pos=(self.state.pose.x, self.state.pose.y),
            my_bbox=my_bbox
        )
        return True

    async def execute_deadlock_evasion(self) -> None:
        """Yields right-of-way by stepping aside or recalculating with a detour."""
        current_cell = self.state.pose.grid_cell
        occupied = set(self.peer_poses.values())
        evasion_cell = DeadlockDetector.find_evasion_cell(
            current_cell, occupied, self.warehouse.is_walkable
        )
        if evasion_cell:
            logger.info(f"[{self.robot_id}] Stepping aside to evasion cell {evasion_cell} to break deadlock.")
            self.state.planned_path = [current_cell, evasion_cell]
            self.state.trajectory = [
                TrajectoryPoint(x=current_cell[0], y=current_cell[1], t=self.current_sim_time),
                TrajectoryPoint(x=evasion_cell[0], y=evasion_cell[1], t=self.current_sim_time + 1.5)
            ]
            self.target_waypoint_idx = 1
            self.state.status = AMRStatus.MOVING
            self.state.waiting_for_robot_id = None
            self.state.stalled_since = None

    async def step(self, dt: float = 0.1) -> None:
        """
        Single simulation time step: kinematics, safety bubble, dynamic obstacle check,
        deadlock check, and task progression.
        """
        self.current_sim_time += dt
        self.state.last_updated = time.time()
        self.reservation_table.clean_expired(self.current_sim_time)

        # 1. Check for dynamic obstacles directly ahead on planned path
        if self.state.planned_path and self.target_waypoint_idx < len(self.state.planned_path):
            next_target = self.state.planned_path[self.target_waypoint_idx]
            if not self.warehouse.is_walkable(next_target):
                logger.warning(f"[{self.robot_id}] Dynamic obstacle detected at {next_target}! Initiating dynamic reroute.")
                self.state.status = AMRStatus.REROUTING
                if self.state.destination:
                    await self.plan_and_broadcast_route(self.state.destination)
                return

        # 2. Deadlock & Stall Check
        if self.state.status in [AMRStatus.YIELDING, AMRStatus.NEGOTIATING]:
            self.state.wait_time_accumulated += dt
            if self.state.stalled_since:
                stall_duration = time.time() - self.state.stalled_since
                if stall_duration > DEADLOCK_WAIT_THRESHOLD:
                    logger.warning(f"[{self.robot_id}] Stall threshold exceeded ({stall_duration:.1f}s). Triggering deadlock detection.")
                    # Build local wait graph
                    wait_graph = {self.robot_id: self.state.waiting_for_robot_id}
                    cycle = DeadlockDetector.find_cycle(wait_graph, self.robot_id)
                    victim = self.robot_id
                    if cycle:
                        priorities = {self.robot_id: self.get_current_priority()}
                        victim = DeadlockDetector.select_resolution_victim(cycle, priorities)

                    alert = P2PMessage(
                        message_type=MessageType.DEADLOCK_ALERT,
                        sender_id=self.robot_id,
                        payload={
                            "cycle": cycle or [self.robot_id, self.state.waiting_for_robot_id or "UNKNOWN"],
                            "victim_robot_id": victim
                        }
                    )
                    await self.p2p_node.broadcast_to_relevant(
                        alert,
                        my_pos=(self.state.pose.x, self.state.pose.y)
                    )
                    if victim == self.robot_id:
                        await self.execute_deadlock_evasion()

        # 3. Kinematics and Movement Execution
        if self.state.status == AMRStatus.MOVING and self.state.planned_path:
            if self.target_waypoint_idx < len(self.state.planned_path):
                target_cell = self.state.planned_path[self.target_waypoint_idx]
                target_x, target_y = float(target_cell[0]), float(target_cell[1])

                # Scheduled Space-Time Wait check
                if self.target_waypoint_idx < len(self.state.trajectory):
                    traj_pt = self.state.trajectory[self.target_waypoint_idx]
                    if (target_x, target_y) == self.state.pose.grid_cell and self.current_sim_time < traj_pt.t:
                        self.state.velocity = 0.0
                        self.state.wait_time_accumulated += dt
                        return

                # Local Safety Check: Stop if step reduces distance to any peer below safety bubble
                for peer_id, (px, py) in self.peer_poses.items():
                    if peer_id == self.robot_id:
                        continue
                    d_to_peer = math.hypot(target_x - px, target_y - py)
                    curr_d = math.hypot(self.state.pose.x - px, self.state.pose.y - py)
                    if d_to_peer < ROBOT_SAFETY_RADIUS and d_to_peer <= curr_d:
                        self.state.velocity = 0.0
                        self.state.collisions_avoided_count += 1
                        self.state.wait_time_accumulated += dt
                        return

                # Move towards target waypoint
                dx = target_x - self.state.pose.x
                dy = target_y - self.state.pose.y
                dist = math.hypot(dx, dy)

                step_dist = ROBOT_MAX_SPEED * dt
                if dist <= step_dist or dist < 0.05:
                    # Arrived at waypoint cell
                    self.state.pose.x = target_x
                    self.state.pose.y = target_y
                    self.state.total_travel_distance += dist
                    self.target_waypoint_idx += 1

                    # Check if reached destination
                    if self.target_waypoint_idx >= len(self.state.planned_path):
                        await self._on_reach_destination()
                else:
                    # Interpolate movement
                    self.state.pose.x += (dx / dist) * step_dist
                    self.state.pose.y += (dy / dist) * step_dist
                    self.state.pose.theta = math.atan2(dy, dx)
                    self.state.velocity = ROBOT_MAX_SPEED
                    self.state.total_travel_distance += step_dist

                self.state.total_travel_time += dt
                self.state.battery = max(0.0, self.state.battery - BATTERY_CONSUMPTION_RATE * dt)

    async def _on_reach_destination(self) -> None:
        """Called when robot reaches its planned destination."""
        self.state.velocity = 0.0
        current_cell = self.state.pose.grid_cell

        # Release any held critical zone reservations
        self.reservation_table.release_robot_reservations(self.robot_id)
        release_msg = P2PMessage(
            message_type=MessageType.RESERVATION_RELEASE,
            sender_id=self.robot_id,
            payload={"zone_id": self.state.current_reservation_zone}
        )
        await self.p2p_node.broadcast_to_relevant(
            release_msg,
            my_pos=(self.state.pose.x, self.state.pose.y)
        )
        self.state.current_reservation_zone = None

        if self.current_task:
            if current_cell == self.current_task.pickup_location:
                # Picked up item; now proceed to drop location
                logger.info(f"[{self.robot_id}] Picked up task {self.current_task.id}. En route to drop {self.current_task.drop_location}.")
                self.current_task.status = TaskStatus.EN_ROUTE_DROP
                await self.plan_and_broadcast_route(self.current_task.drop_location)
            elif current_cell == self.current_task.drop_location:
                # Task completed!
                logger.info(f"[{self.robot_id}] Completed task {self.current_task.id}!")
                self.current_task.status = TaskStatus.COMPLETED
                self.current_task.completed_at = time.time()
                self.state.tasks_completed_count += 1
                self.current_task = None
                self.state.current_task_id = None
                self.state.status = AMRStatus.IDLE
                self.state.planned_path = []
                self.state.trajectory = []
        else:
            self.state.status = AMRStatus.IDLE

    def to_dict(self) -> dict:
        return {
            **self.state.to_dict(),
            "host": self.host,
            "port": self.port,
            "peers": self.discovery_table.to_dict(),
            "reservations": self.reservation_table.to_list()
        }
