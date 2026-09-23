"""
Peer Discovery Table and Relevance-Based Neighborhood Filtering
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import math
import time
from edgefleet.config import DEFAULT_COMMUNICATION_RADIUS, PEER_TIMEOUT

@dataclass
class PeerEntry:
    robot_id: str
    host: str
    port: int
    last_seen: float = field(default_factory=time.time)
    status: str = "ACTIVE"
    last_known_pos: Optional[Tuple[float, float]] = None
    last_seq_no: int = 0
    trajectory_bounding_box: Optional[Tuple[float, float, float, float]] = None  # (xmin, ymin, xmax, ymax)

    def is_alive(self, timeout_sec: float = PEER_TIMEOUT, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return (now - self.last_seen) <= timeout_sec

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "host": self.host,
            "port": self.port,
            "last_seen": round(self.last_seen, 2),
            "status": self.status,
            "last_known_pos": list(self.last_known_pos) if self.last_known_pos else None,
            "last_seq_no": self.last_seq_no
        }

class DiscoveryTable:
    """
    Local Peer Discovery and Address Book maintained by each AMR.
    """
    def __init__(self, my_robot_id: str, comm_radius: float = DEFAULT_COMMUNICATION_RADIUS):
        self.my_robot_id = my_robot_id
        self.comm_radius = comm_radius
        self._peers: Dict[str, PeerEntry] = {}

    def register_peer(
        self,
        robot_id: str,
        host: str,
        port: int,
        status: str = "ACTIVE",
        pos: Optional[Tuple[float, float]] = None
    ) -> PeerEntry:
        if robot_id not in self._peers:
            entry = PeerEntry(robot_id=robot_id, host=host, port=port, status=status, last_known_pos=pos)
            self._peers[robot_id] = entry
            return entry
        else:
            entry = self._peers[robot_id]
            entry.host = host
            entry.port = port
            entry.status = status
            entry.last_seen = time.time()
            if pos:
                entry.last_known_pos = pos
            return entry

    def update_address(self, robot_id: str, host: str, port: int) -> None:
        if robot_id in self._peers:
            self._peers[robot_id].host = host
            self._peers[robot_id].port = port
            self._peers[robot_id].last_seen = time.time()
        else:
            self.register_peer(robot_id, host, port)

    def update_heartbeat(self, robot_id: str, pos: Optional[Tuple[float, float]] = None, seq_no: int = 0) -> None:
        if robot_id in self._peers:
            entry = self._peers[robot_id]
            entry.last_seen = time.time()
            entry.status = "ACTIVE"
            if pos:
                entry.last_known_pos = pos
            if seq_no > entry.last_seq_no:
                entry.last_seq_no = seq_no

    def get_peer(self, robot_id: str) -> Optional[PeerEntry]:
        return self._peers.get(robot_id)

    def get_all_peers(self) -> List[PeerEntry]:
        return list(self._peers.values())

    def get_active_peers(self, timeout_sec: float = PEER_TIMEOUT) -> List[PeerEntry]:
        now = time.time()
        return [p for p in self._peers.values() if p.is_alive(timeout_sec, now)]

    def is_relevant_neighbor(
        self,
        peer_id: str,
        my_pos: Tuple[float, float],
        my_bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> bool:
        """
        Scalability Filter: Evaluates whether peer is within communication radius
        or if planned trajectory intersects with peer or peer's area.
        """
        peer = self._peers.get(peer_id)
        if not peer:
            return False

        # 1. Direct Spatial Proximity Check
        if peer.last_known_pos is not None:
            dist = math.hypot(my_pos[0] - peer.last_known_pos[0], my_pos[1] - peer.last_known_pos[1])
            if dist <= self.comm_radius:
                return True

            # 2. Planned Trajectory vs Peer Position Envelope Check
            if my_bbox:
                my_xmin, my_ymin, my_xmax, my_ymax = my_bbox
                px, py = peer.last_known_pos
                # If peer is within comm radius of our planned path envelope
                if (my_xmin - self.comm_radius <= px <= my_xmax + self.comm_radius and
                    my_ymin - self.comm_radius <= py <= my_ymax + self.comm_radius):
                    return True

        # 3. Trajectory Bounding Box Overlap
        if my_bbox and peer.trajectory_bounding_box:
            my_xmin, my_ymin, my_xmax, my_ymax = my_bbox
            p_xmin, p_ymin, p_xmax, p_ymax = peer.trajectory_bounding_box
            if not (my_xmax < p_xmin or my_xmin > p_xmax or my_ymax < p_ymin or my_ymin > p_ymax):
                return True

        # If peer position is unknown, default to true for discovery
        if peer.last_known_pos is None:
            return True

        return False

    def to_dict(self) -> dict:
        return {r_id: entry.to_dict() for r_id, entry in self._peers.items()}
