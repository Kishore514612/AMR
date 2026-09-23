"""
Benchmark Metrics & Performance Analysis
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import json

@dataclass
class BenchmarkResult:
    scenario_id: str
    scenario_name: str
    robot_count: int
    task_count: int
    baseline_time: float
    decentralized_time: float
    baseline_wait_time: float
    decentralized_wait_time: float
    collisions_baseline: int
    collisions_decentralized: int
    conflicts_resolved: int
    deadlocks_resolved: int
    reroutes: int
    p2p_messages_sent: int = 0

    @property
    def improvement_pct(self) -> float:
        if self.baseline_time <= 0:
            return 0.0
        return ((self.baseline_time - self.decentralized_time) / self.baseline_time) * 100.0

    @property
    def wait_time_reduction_pct(self) -> float:
        if self.baseline_wait_time <= 0:
            return 0.0
        return ((self.baseline_wait_time - self.decentralized_wait_time) / self.baseline_wait_time) * 100.0

    @property
    def target_20_met(self) -> bool:
        return self.improvement_pct >= 20.0 and self.collisions_decentralized == 0

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "robot_count": self.robot_count,
            "task_count": self.task_count,
            "baseline_time": round(self.baseline_time, 2),
            "decentralized_time": round(self.decentralized_time, 2),
            "baseline_wait_time": round(self.baseline_wait_time, 2),
            "decentralized_wait_time": round(self.decentralized_wait_time, 2),
            "improvement_pct": round(self.improvement_pct, 2),
            "wait_time_reduction_pct": round(self.wait_time_reduction_pct, 2),
            "collisions_baseline": self.collisions_baseline,
            "collisions_decentralized": self.collisions_decentralized,
            "conflicts_resolved": self.conflicts_resolved,
            "deadlocks_resolved": self.deadlocks_resolved,
            "reroutes": self.reroutes,
            "p2p_messages_sent": self.p2p_messages_sent,
            "target_20_met": self.target_20_met
        }
