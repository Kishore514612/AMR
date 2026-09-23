"""
Warehouse Grid Map & Environment Layout
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import json

class CellType(str, Enum):
    EMPTY = "EMPTY"
    SHELF = "SHELF"
    WALL = "WALL"
    INTERSECTION = "INTERSECTION"
    CORRIDOR = "CORRIDOR"
    PICKUP = "PICKUP"
    DROP = "DROP"
    CHARGING = "CHARGING"
    BLOCKED = "BLOCKED"

@dataclass
class CriticalZone:
    id: str
    cells: List[Tuple[int, int]]
    zone_type: str  # "INTERSECTION" or "NARROW_CORRIDOR"
    description: str = ""

@dataclass
class WarehouseMap:
    width: int = 30
    height: int = 20
    shelves: Set[Tuple[int, int]] = field(default_factory=set)
    walls: Set[Tuple[int, int]] = field(default_factory=set)
    pickups: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    drops: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    charging_stations: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    critical_zones: Dict[str, CriticalZone] = field(default_factory=dict)
    dynamic_obstacles: Set[Tuple[int, int]] = field(default_factory=set)

    @classmethod
    def create_default(cls, width: int = 30, height: int = 20) -> "WarehouseMap":
        """
        Creates a realistic smart warehouse layout:
        - Outer walls
        - 4 shelf blocks with cross aisles
        - Central high-traffic 4-way intersection (Critical Zone X1)
        - East bottleneck corridor (Critical Zone C1)
        - Dedicated Pickup A/B/C/D stations
        - Dedicated Drop A/B/C/D stations
        - Charging bays
        """
        wh = cls(width=width, height=height)

        # Outer walls
        for x in range(width):
            wh.walls.add((x, 0))
            wh.walls.add((x, height - 1))
        for y in range(height):
            wh.walls.add((0, y))
            wh.walls.add((width - 1, y))

        # Shelves (Block 1: Top-Left, Block 2: Top-Right, Block 3: Bottom-Left, Block 4: Bottom-Right)
        # Block 1: x from 4 to 10, y from 3 to 7
        for x in range(4, 11):
            for y in range(3, 8):
                wh.shelves.add((x, y))

        # Block 2: x from 19 to 25, y from 3 to 7
        for x in range(19, 26):
            for y in range(3, 8):
                wh.shelves.add((x, y))

        # Block 3: x from 4 to 10, y from 12 to 16
        for x in range(4, 11):
            for y in range(12, 17):
                wh.shelves.add((x, y))

        # Block 4: x from 19 to 25, y from 12 to 16
        for x in range(19, 26):
            for y in range(12, 17):
                wh.shelves.add((x, y))

        # Critical Zones (Intersections & Bottlenecks)
        # Central Main Intersection (X1) around (14, 15) x (9, 10)
        central_cells = [(14, 9), (15, 9), (14, 10), (15, 10)]
        wh.critical_zones["X1"] = CriticalZone(
            id="X1",
            cells=central_cells,
            zone_type="INTERSECTION",
            description="Central Main 4-Way Intersection"
        )

        # North-Central Junction (X2)
        wh.critical_zones["X2"] = CriticalZone(
            id="X2",
            cells=[(14, 2), (15, 2)],
            zone_type="INTERSECTION",
            description="North Main Highway Junction"
        )

        # South-Central Junction (X3)
        wh.critical_zones["X3"] = CriticalZone(
            id="X3",
            cells=[(14, 18), (15, 18)],
            zone_type="INTERSECTION",
            description="South Main Highway Junction"
        )

        # East Narrow Corridor (C1)
        wh.critical_zones["C1"] = CriticalZone(
            id="C1",
            cells=[(27, 9), (28, 9), (27, 10), (28, 10)],
            zone_type="NARROW_CORRIDOR",
            description="East Single-Lane Bottleneck"
        )

        # Pickups
        wh.pickups["PICKUP_A"] = (2, 2)
        wh.pickups["PICKUP_B"] = (2, 9)
        wh.pickups["PICKUP_C"] = (2, 17)
        wh.pickups["PICKUP_D"] = (15, 1)

        # Drops
        wh.drops["DROP_A"] = (28, 2)
        wh.drops["DROP_B"] = (28, 17)
        wh.drops["DROP_C"] = (15, 18)
        wh.drops["DROP_D"] = (28, 9)

        # Charging Stations
        wh.charging_stations["CHARGE_1"] = (1, 5)
        wh.charging_stations["CHARGE_2"] = (1, 14)
        wh.charging_stations["CHARGE_3"] = (28, 5)

        return wh

    def is_walkable(self, pos: Tuple[int, int]) -> bool:
        x, y = pos
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        if pos in self.walls or pos in self.shelves or pos in self.dynamic_obstacles:
            return False
        return True

    def get_cell_type(self, pos: Tuple[int, int]) -> CellType:
        if pos in self.dynamic_obstacles:
            return CellType.BLOCKED
        if pos in self.walls:
            return CellType.WALL
        if pos in self.shelves:
            return CellType.SHELF
        for zone in self.critical_zones.values():
            if pos in zone.cells:
                return CellType.INTERSECTION if zone.zone_type == "INTERSECTION" else CellType.CORRIDOR
        for loc in self.pickups.values():
            if pos == loc:
                return CellType.PICKUP
        for loc in self.drops.values():
            if pos == loc:
                return CellType.DROP
        for loc in self.charging_stations.values():
            if pos == loc:
                return CellType.CHARGING
        return CellType.EMPTY

    def add_dynamic_obstacle(self, pos: Tuple[int, int]) -> bool:
        if 0 <= pos[0] < self.width and 0 <= pos[1] < self.height and pos not in self.walls and pos not in self.shelves:
            self.dynamic_obstacles.add(pos)
            return True
        return False

    def remove_dynamic_obstacle(self, pos: Tuple[int, int]) -> bool:
        if pos in self.dynamic_obstacles:
            self.dynamic_obstacles.remove(pos)
            return True
        return False

    def clear_dynamic_obstacles(self):
        self.dynamic_obstacles.clear()

    def get_critical_zone_for_cell(self, pos: Tuple[int, int]) -> Optional[CriticalZone]:
        for zone in self.critical_zones.values():
            if pos in zone.cells:
                return zone
        return None

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "shelves": list(self.shelves),
            "walls": list(self.walls),
            "pickups": self.pickups,
            "drops": self.drops,
            "charging_stations": self.charging_stations,
            "critical_zones": {
                k: {"id": v.id, "cells": v.cells, "zone_type": v.zone_type, "description": v.description}
                for k, v in self.critical_zones.items()
            },
            "dynamic_obstacles": list(self.dynamic_obstacles)
        }
