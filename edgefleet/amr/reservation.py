"""
Space-Time Reservation Table for Multi-Agent Planning
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import time

@dataclass
class Reservation:
    id: str
    robot_id: str
    cell: Tuple[int, int]
    start_time: float   # simulation or relative time
    end_time: float     # simulation or relative time
    zone_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    active: bool = True

    def overlaps_with(self, cell: Tuple[int, int], t_start: float, t_end: float) -> bool:
        if not self.active:
            return False
        if self.cell != cell:
            return False
        # Overlap condition: max(start1, start2) < min(end1, end2)
        return max(self.start_time, t_start) < min(self.end_time, t_end)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "robot_id": self.robot_id,
            "cell": list(self.cell),
            "zone_id": self.zone_id,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "active": self.active
        }

class ReservationTable:
    """
    Local Space-Time Reservation Table maintained independently on each AMR.
    """
    def __init__(self, owner_robot_id: str):
        self.owner_robot_id = owner_robot_id
        # Key: (x, y) -> List[Reservation]
        self._cell_reservations: Dict[Tuple[int, int], List[Reservation]] = {}
        # Key: zone_id -> List[Reservation]
        self._zone_reservations: Dict[str, List[Reservation]] = {}

    def add_reservation(self, res: Reservation) -> None:
        if res.cell not in self._cell_reservations:
            self._cell_reservations[res.cell] = []
        self._cell_reservations[res.cell].append(res)

        if res.zone_id:
            if res.zone_id not in self._zone_reservations:
                self._zone_reservations[res.zone_id] = []
            self._zone_reservations[res.zone_id].append(res)

    def is_cell_reserved(
        self,
        cell: Tuple[int, int],
        t_start: float,
        t_end: float,
        exclude_robot_id: Optional[str] = None
    ) -> Optional[Reservation]:
        """
        Returns conflicting Reservation if cell is occupied during [t_start, t_end]
        by a robot other than exclude_robot_id.
        """
        if cell in self._cell_reservations:
            for res in self._cell_reservations[cell]:
                if not res.active:
                    continue
                if exclude_robot_id and res.robot_id == exclude_robot_id:
                    continue
                if res.overlaps_with(cell, t_start, t_end):
                    return res
        return None

    def is_zone_reserved(
        self,
        zone_id: str,
        t_start: float,
        t_end: float,
        exclude_robot_id: Optional[str] = None
    ) -> Optional[Reservation]:
        """
        Returns conflicting Reservation if entire critical zone is occupied.
        """
        if zone_id in self._zone_reservations:
            for res in self._zone_reservations[zone_id]:
                if not res.active:
                    continue
                if exclude_robot_id and res.robot_id == exclude_robot_id:
                    continue
                if max(res.start_time, t_start) < min(res.end_time, t_end):
                    return res
        return None

    def is_edge_conflict(
        self,
        from_cell: Tuple[int, int],
        to_cell: Tuple[int, int],
        t_from: float,
        t_to: float,
        exclude_robot_id: Optional[str] = None
    ) -> bool:
        """
        Detects head-on swap conflict: Another robot moving to_cell -> from_cell
        at the same time interval.
        """
        # If another robot reserves to_cell at t_from and from_cell at t_to
        res_to = self.is_cell_reserved(to_cell, t_from - 0.1, t_from + 0.9, exclude_robot_id=exclude_robot_id)
        res_from = self.is_cell_reserved(from_cell, t_to - 0.1, t_to + 0.9, exclude_robot_id=exclude_robot_id)
        if res_to and res_from and res_to.robot_id == res_from.robot_id:
            return True
        return False

    def release_robot_reservations(self, robot_id: str, zone_id: Optional[str] = None) -> List[Reservation]:
        """
        Releases reservations belonging to robot_id (optionally specific zone).
        """
        released = []
        for cell, res_list in self._cell_reservations.items():
            for res in res_list:
                if res.robot_id == robot_id and (zone_id is None or res.zone_id == zone_id):
                    res.active = False
                    released.append(res)
        return released

    def clean_expired(self, current_sim_time: float) -> None:
        """
        Prunes old expired reservations.
        """
        for cell in list(self._cell_reservations.keys()):
            self._cell_reservations[cell] = [
                r for r in self._cell_reservations[cell]
                if r.active and r.end_time >= current_sim_time
            ]
            if not self._cell_reservations[cell]:
                del self._cell_reservations[cell]

        for zone in list(self._zone_reservations.keys()):
            self._zone_reservations[zone] = [
                r for r in self._zone_reservations[zone]
                if r.active and r.end_time >= current_sim_time
            ]
            if not self._zone_reservations[zone]:
                del self._zone_reservations[zone]

    def clear(self) -> None:
        self._cell_reservations.clear()
        self._zone_reservations.clear()

    def get_all_active(self) -> List[Reservation]:
        results = []
        for res_list in self._cell_reservations.values():
            for r in res_list:
                if r.active and r not in results:
                    results.append(r)
        return results

    def to_list(self) -> List[dict]:
        return [r.to_dict() for r in self.get_all_active()]
