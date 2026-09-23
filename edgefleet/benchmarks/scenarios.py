"""
Standard Demonstration Scenarios (Scenarios A through F)
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple
from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.simulation.tasks import Task
from edgefleet.simulation.engine import SimulationEngine
from edgefleet.baseline.stop_and_wait import StopAndWaitSimulator

@dataclass
class ScenarioDefinition:
    id: str
    name: str
    description: str
    robot_spawns: Dict[str, Tuple[int, int]]  # robot_id -> initial_pos
    tasks: List[Task]
    dynamic_obstacles: List[Tuple[int, int]]

def build_scenario_a() -> ScenarioDefinition:
    """Scenario A — Normal: 3 robots with independent routes."""
    return ScenarioDefinition(
        id="A",
        name="Normal Operation",
        description="3 AMRs operating on parallel independent routes without major congestion.",
        robot_spawns={
            "R1": (2, 2),
            "R2": (2, 9),
            "R3": (2, 17)
        },
        tasks=[
            Task(id="TASK_A1", pickup_location=(2, 2), drop_location=(28, 2), priority=2),
            Task(id="TASK_A2", pickup_location=(2, 9), drop_location=(28, 9), priority=1),
            Task(id="TASK_A3", pickup_location=(2, 17), drop_location=(28, 17), priority=3),
        ],
        dynamic_obstacles=[]
    )

def build_scenario_b() -> ScenarioDefinition:
    """Scenario B — Overlapping Paths: 3 robots converging on Central Intersection X1."""
    return ScenarioDefinition(
        id="B",
        name="Overlapping Paths (Intersection Negotiation)",
        description="3 AMRs approach the central 4-way intersection (14, 9)-(15, 10) simultaneously.",
        robot_spawns={
            "R1": (2, 9),    # West approaching East
            "R2": (27, 9),   # East approaching West
            "R3": (14, 18),  # South approaching North
        },
        tasks=[
            Task(id="TASK_B1", pickup_location=(2, 9), drop_location=(28, 9), priority=3),   # West to East
            Task(id="TASK_B2", pickup_location=(27, 9), drop_location=(2, 9), priority=1),   # East to West
            Task(id="TASK_B3", pickup_location=(14, 18), drop_location=(14, 2), priority=2), # South to North
        ],
        dynamic_obstacles=[]
    )

def build_scenario_c() -> ScenarioDefinition:
    """Scenario C — Equal Priority: 2 robots with identical priority converging head-on."""
    return ScenarioDefinition(
        id="C",
        name="Equal Priority Tie-Breaker",
        description="2 AMRs with identical task priority and distances force deterministic tie-breaking.",
        robot_spawns={
            "R1": (5, 9),
            "R2": (23, 9),
        },
        tasks=[
            Task(id="TASK_C1", pickup_location=(5, 9), drop_location=(23, 9), priority=2),
            Task(id="TASK_C2", pickup_location=(23, 9), drop_location=(5, 9), priority=2),
        ],
        dynamic_obstacles=[]
    )

def build_scenario_d() -> ScenarioDefinition:
    """Scenario D — Blocked Aisle: Route dynamically blocked during transit."""
    return ScenarioDefinition(
        id="D",
        name="Dynamic Obstacle & Aisle Blockage",
        description="A main aisle is suddenly blocked by a spill, forcing real-time local rerouting.",
        robot_spawns={
            "R1": (2, 2),
            "R2": (2, 9),
            "R3": (28, 9)
        },
        tasks=[
            Task(id="TASK_D1", pickup_location=(2, 2), drop_location=(28, 2), priority=2),
            Task(id="TASK_D2", pickup_location=(2, 9), drop_location=(28, 9), priority=3),
            Task(id="TASK_D3", pickup_location=(28, 9), drop_location=(2, 9), priority=1),
        ],
        dynamic_obstacles=[(14, 9), (15, 9)]  # Blocks the central corridor
    )

def build_scenario_e() -> ScenarioDefinition:
    """Scenario E — Deadlock: 3 robots in mutual circular wait in narrow junction."""
    return ScenarioDefinition(
        id="E",
        name="Multi-Robot Deadlock Resolution",
        description="3 AMRs enter a narrow junction forming a circular wait graph, triggering distributed deadlock resolution.",
        robot_spawns={
            "R1": (13, 9),
            "R2": (16, 9),
            "R3": (14, 11),
        },
        tasks=[
            Task(id="TASK_E1", pickup_location=(13, 9), drop_location=(16, 9), priority=1),
            Task(id="TASK_E2", pickup_location=(16, 9), drop_location=(14, 11), priority=2),
            Task(id="TASK_E3", pickup_location=(14, 11), drop_location=(13, 9), priority=3),
        ],
        dynamic_obstacles=[]
    )

def build_scenario_f() -> ScenarioDefinition:
    """Scenario F — Server Down: Central backend is killed; AMRs coordinate purely P2P."""
    return ScenarioDefinition(
        id="F",
        name="Central Server Offline (Pure P2P Coordination)",
        description="Validation that local P2P coordination and collision avoidance function perfectly with zero central server involvement.",
        robot_spawns={
            "R1": (2, 9),
            "R2": (27, 9),
            "R3": (14, 18),
        },
        tasks=[
            Task(id="TASK_F1", pickup_location=(2, 9), drop_location=(28, 9), priority=3),
            Task(id="TASK_F2", pickup_location=(27, 9), drop_location=(2, 9), priority=2),
            Task(id="TASK_F3", pickup_location=(14, 18), drop_location=(14, 2), priority=1),
        ],
        dynamic_obstacles=[]
    )

SCENARIOS: Dict[str, callable] = {
    "A": build_scenario_a,
    "B": build_scenario_b,
    "C": build_scenario_c,
    "D": build_scenario_d,
    "E": build_scenario_e,
    "F": build_scenario_f,
}
