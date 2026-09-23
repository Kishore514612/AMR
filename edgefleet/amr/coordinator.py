"""
AMR P2P Coordinator & State Machine Handler
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
import time
from edgefleet.network.protocol import P2PMessage, MessageType
from edgefleet.amr.state import AMRState, AMRStatus, TrajectoryPoint
from edgefleet.amr.reservation import ReservationTable, Reservation
from edgefleet.amr.conflict import ConflictDetector, PathConflict, ConflictType
from edgefleet.amr.deadlock import DeadlockDetector, DeadlockEvent

logger = logging.getLogger(__name__)

class AMRCoordinator:
    """
    Decentralized Coordinator handling P2P negotiations on each AMR.
    """
    def __init__(self, robot):
        self.robot = robot  # Back-reference to parent AMRRobot instance

    async def handle_message(self, msg: P2PMessage) -> None:
        """Route incoming P2P message based on message type."""
        m_type = msg.message_type

        if m_type == MessageType.DISCOVERY:
            await self._handle_discovery(msg)
        elif m_type == MessageType.DISCOVERY_ACK:
            self._handle_discovery_ack(msg)
        elif m_type == MessageType.STATE_UPDATE:
            self._handle_state_update(msg)
        elif m_type == MessageType.INTENT_UPDATE or m_type == MessageType.PATH_UPDATE:
            await self._handle_intent_update(msg)
        elif m_type == MessageType.CONFLICT_REQUEST:
            await self._handle_conflict_request(msg)
        elif m_type == MessageType.RESERVATION_REQUEST:
            await self._handle_reservation_request(msg)
        elif m_type == MessageType.RESERVATION_GRANTED:
            self._handle_reservation_granted(msg)
        elif m_type == MessageType.YIELD:
            self._handle_yield(msg)
        elif m_type == MessageType.PROCEED:
            self._handle_proceed(msg)
        elif m_type == MessageType.RESERVATION_RELEASE:
            self._handle_reservation_release(msg)
        elif m_type == MessageType.DEADLOCK_ALERT:
            await self._handle_deadlock_alert(msg)

    async def _handle_discovery(self, msg: P2PMessage) -> None:
        # Peer introduced itself; acknowledge and send own address
        sender_id = msg.sender_id
        host = msg.payload.get("host", "127.0.0.1")
        port = msg.payload.get("port", 0)
        self.robot.discovery_table.register_peer(sender_id, host, port)

        ack = P2PMessage(
            message_type=MessageType.DISCOVERY_ACK,
            sender_id=self.robot.robot_id,
            recipient_id=sender_id,
            payload={
                "host": self.robot.host,
                "port": self.robot.port,
                "status": self.robot.state.status.value,
                "position": [self.robot.state.pose.x, self.robot.state.pose.y]
            }
        )
        await self.robot.p2p_node.send_direct(sender_id, ack)

    def _handle_discovery_ack(self, msg: P2PMessage) -> None:
        sender_id = msg.sender_id
        host = msg.payload.get("host", "127.0.0.1")
        port = msg.payload.get("port", 0)
        self.robot.discovery_table.register_peer(sender_id, host, port)

    def _handle_state_update(self, msg: P2PMessage) -> None:
        sender_id = msg.sender_id
        payload = msg.payload
        pos = payload.get("position")
        if pos:
            self.robot.peer_poses[sender_id] = tuple(pos)
        self.robot.peer_statuses[sender_id] = payload.get("status", "IDLE")
        self.robot.peer_batteries[sender_id] = payload.get("battery", 100.0)

    async def _handle_intent_update(self, msg: P2PMessage) -> None:
        sender_id = msg.sender_id
        payload = msg.payload
        raw_traj = payload.get("trajectory", [])
        peer_traj = [TrajectoryPoint(x=p["x"], y=p["y"], t=p["t"]) for p in raw_traj]
        self.robot.peer_trajectories[sender_id] = peer_traj

        # Update local space-time reservation table with peer's claimed trajectory
        self.robot.reservation_table.release_robot_reservations(sender_id)
        for p in peer_traj:
            self.robot.reservation_table.add_reservation(
                Reservation(
                    id=f"{sender_id}_{p.x}_{p.y}_{p.t}",
                    robot_id=sender_id,
                    cell=(p.x, p.y),
                    start_time=p.t - 0.7,
                    end_time=p.t + 0.7
                )
            )

        # Check for space-time conflicts with own planned trajectory
        if self.robot.state.trajectory:
            conflict = ConflictDetector.detect_trajectory_conflict(
                robot1_id=self.robot.robot_id,
                traj1=self.robot.state.trajectory,
                robot2_id=sender_id,
                traj2=peer_traj
            )

            if conflict:
                logger.info(f"[{self.robot.robot_id}] Detected conflict with {sender_id}: {conflict.description}")
                await self.initiate_conflict_negotiation(sender_id, conflict)

    async def initiate_conflict_negotiation(self, peer_id: str, conflict: PathConflict) -> None:
        """Calculates own priority and sends conflict resolution request to peer."""
        self.robot.state.status = AMRStatus.NEGOTIATING
        my_priority = self.robot.get_current_priority()

        req = P2PMessage(
            message_type=MessageType.CONFLICT_REQUEST,
            sender_id=self.robot.robot_id,
            recipient_id=peer_id,
            payload={
                "conflict": conflict.to_dict(),
                "priority": my_priority,
                "wait_time": self.robot.state.wait_time_accumulated,
                "eta": self.robot.state.eta,
                "task_urgency": self.robot.current_task.priority if self.robot.current_task else 1
            }
        )
        await self.robot.p2p_node.send_direct(peer_id, req)

    async def _handle_conflict_request(self, msg: P2PMessage) -> None:
        sender_id = msg.sender_id
        payload = msg.payload
        peer_priority = payload.get("priority", 0.0)
        peer_wait = payload.get("wait_time", 0.0)
        peer_eta = payload.get("eta", 10.0)

        my_priority = self.robot.get_current_priority()
        my_wait = self.robot.state.wait_time_accumulated
        my_eta = self.robot.state.eta

        # Deterministic conflict resolution on both ends
        winner_id, loser_id, reason = ConflictDetector.resolve_conflict_deterministic(
            robot1_id=self.robot.robot_id,
            priority1=my_priority,
            wait_time1=my_wait,
            eta1=my_eta,
            robot2_id=sender_id,
            priority2=peer_priority,
            wait_time2=peer_wait,
            eta2=peer_eta
        )

        logger.info(f"[{self.robot.robot_id}] Conflict with {sender_id} resolved: Winner={winner_id} Reason: {reason}")
        self.robot.state.conflicts_resolved_count += 1

        if winner_id == self.robot.robot_id:
            # We won: inform peer that we proceed and reserve the cell/zone
            self.robot.state.status = AMRStatus.MOVING
            self.robot.state.waiting_for_robot_id = None
            resp = P2PMessage(
                message_type=MessageType.PROCEED,
                sender_id=self.robot.robot_id,
                recipient_id=sender_id,
                payload={"winner": winner_id, "reason": reason}
            )
            await self.robot.p2p_node.send_direct(sender_id, resp)
        else:
            # We lost: yield and replan around winner's space-time trajectory
            self.robot.state.status = AMRStatus.YIELDING
            self.robot.state.waiting_for_robot_id = sender_id
            self.robot.state.stalled_since = time.time()
            resp = P2PMessage(
                message_type=MessageType.YIELD,
                sender_id=self.robot.robot_id,
                recipient_id=sender_id,
                payload={"winner": winner_id, "loser": loser_id, "reason": reason}
            )
            await self.robot.p2p_node.send_direct(sender_id, resp)
            # Replan around winner's trajectory
            await self.robot.replan_around_peer(sender_id)

    async def _handle_reservation_request(self, msg: P2PMessage) -> None:
        sender_id = msg.sender_id
        payload = msg.payload
        cell = tuple(payload["cell"])
        t_start = payload["start_time"]
        t_end = payload["end_time"]
        zone_id = payload.get("zone_id")

        # Record peer's reservation locally
        res = Reservation(
            id=f"{sender_id}_{cell}_{t_start}",
            robot_id=sender_id,
            cell=cell,
            start_time=t_start,
            end_time=t_end,
            zone_id=zone_id
        )
        self.robot.reservation_table.add_reservation(res)

        grant = P2PMessage(
            message_type=MessageType.RESERVATION_GRANTED,
            sender_id=self.robot.robot_id,
            recipient_id=sender_id,
            payload={"cell": list(cell), "granted": True}
        )
        await self.robot.p2p_node.send_direct(sender_id, grant)

    def _handle_reservation_granted(self, msg: P2PMessage) -> None:
        if self.robot.state.status == AMRStatus.NEGOTIATING:
            self.robot.state.status = AMRStatus.MOVING

    def _handle_yield(self, msg: P2PMessage) -> None:
        # Peer yielded to us; we are clear to proceed
        logger.info(f"[{self.robot.robot_id}] Peer {msg.sender_id} yielded. Proceeding.")
        self.robot.state.status = AMRStatus.MOVING
        self.robot.state.waiting_for_robot_id = None

    def _handle_proceed(self, msg: P2PMessage) -> None:
        payload = msg.payload
        winner = payload.get("winner")
        if winner == self.robot.robot_id:
            self.robot.state.status = AMRStatus.MOVING
            self.robot.state.waiting_for_robot_id = None

    def _handle_reservation_release(self, msg: P2PMessage) -> None:
        sender_id = msg.sender_id
        zone_id = msg.payload.get("zone_id")
        self.robot.reservation_table.release_robot_reservations(sender_id, zone_id)
        if self.robot.state.waiting_for_robot_id == sender_id:
            logger.info(f"[{self.robot.robot_id}] {sender_id} released reservation. Resuming movement.")
            self.robot.state.waiting_for_robot_id = None
            self.robot.state.status = AMRStatus.MOVING
            self.robot.state.stalled_since = None

    async def _handle_deadlock_alert(self, msg: P2PMessage) -> None:
        victim = msg.payload.get("victim_robot_id")
        if victim == self.robot.robot_id:
            logger.warning(f"[{self.robot.robot_id}] Selected as deadlock resolution victim. Performing evasion.")
            await self.robot.execute_deadlock_evasion()
