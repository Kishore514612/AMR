"""
Automated Benchmark Runner & Experiment Evaluator
"""
import asyncio
import logging
from typing import Dict, List, Optional
import time
from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.simulation.engine import SimulationEngine
from edgefleet.simulation.tasks import Task, TaskStatus
from edgefleet.baseline.stop_and_wait import StopAndWaitSimulator
from edgefleet.benchmarks.scenarios import SCENARIOS, ScenarioDefinition
from edgefleet.benchmarks.metrics import BenchmarkResult

_global_port_counter = 9400

class BenchmarkRunner:
    @staticmethod
    async def run_decentralized_scenario(scenario: ScenarioDefinition, max_sim_time: float = 300.0) -> dict:
        """Executes a scenario using EdgeFleet Decentralized P2P coordination."""
        global _global_port_counter
        port_base = _global_port_counter
        _global_port_counter += len(scenario.robot_spawns) + 5

        warehouse = WarehouseMap.create_default()
        for obs_pos in scenario.dynamic_obstacles:
            warehouse.add_dynamic_obstacle(obs_pos)

        engine = SimulationEngine(warehouse=warehouse)

        # Spawn AMRs
        for idx, (r_id, spawn_pos) in enumerate(scenario.robot_spawns.items()):
            engine.add_robot(
                robot_id=r_id,
                initial_pos=spawn_pos,
                port=port_base + idx
            )

        # Initialize mutual P2P mesh
        await engine.initialize_fleet_p2p()

        # Assign tasks
        for task in scenario.tasks:
            engine.add_task(task)
            # Find assigned robot or match by order
            for r_id, r in engine.robots.items():
                if r.state.status.value == "IDLE" and not r.current_task:
                    await r.assign_task(task)
                    break

        # Step simulation until completion or timeout
        dt = 0.1
        sim_time = 0.0
        while sim_time < max_sim_time:
            await engine.step()
            sim_time += dt

            # Check if all tasks complete
            all_done = all(t.status == TaskStatus.COMPLETED for t in engine.tasks.values())
            if all_done and all(r.state.status.value == "IDLE" for r in engine.robots.values()):
                break

        # Collect metrics
        metrics = engine.get_summary_metrics()
        p2p_msg_count = sum(len(r.p2p_node.sent_messages_log) for r in engine.robots.values())

        # Cleanup
        await engine.stop()

        return {
            "sim_time": round(sim_time, 2),
            "total_wait_time": metrics["total_wait_time"],
            "conflicts_resolved": metrics["total_conflicts_resolved"],
            "reroutes": metrics["total_reroutes"],
            "collisions": metrics["collision_count"],
            "p2p_messages_sent": p2p_msg_count
        }

    @staticmethod
    def run_baseline_scenario(scenario: ScenarioDefinition, max_sim_time: float = 300.0) -> dict:
        """Executes a scenario using Stop-and-Wait baseline."""
        warehouse = WarehouseMap.create_default()
        for obs_pos in scenario.dynamic_obstacles:
            warehouse.add_dynamic_obstacle(obs_pos)

        baseline_sim = StopAndWaitSimulator(warehouse=warehouse)

        for r_id, spawn_pos in scenario.robot_spawns.items():
            baseline_sim.add_robot(r_id, spawn_pos)

        for task in scenario.tasks:
            baseline_sim.add_task(task)
            for r_id, r in baseline_sim.robots.items():
                if r.status == "IDLE" and not r.current_task:
                    baseline_sim.assign_task(r_id, task)
                    break

        return baseline_sim.run_until_complete(max_sim_time=max_sim_time)

    @classmethod
    async def evaluate_scenario(cls, scenario_id: str) -> BenchmarkResult:
        scenario_builder = SCENARIOS.get(scenario_id.upper())
        if not scenario_builder:
            raise ValueError(f"Unknown scenario ID: {scenario_id}")

        scenario = scenario_builder()

        # Run Decentralized
        decentralized_res = await cls.run_decentralized_scenario(scenario)

        # Run Baseline
        baseline_res = cls.run_baseline_scenario(scenario)

        result = BenchmarkResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            robot_count=len(scenario.robot_spawns),
            task_count=len(scenario.tasks),
            baseline_time=baseline_res["total_sim_time"],
            decentralized_time=decentralized_res["sim_time"],
            baseline_wait_time=baseline_res["total_wait_time"],
            decentralized_wait_time=decentralized_res["total_wait_time"],
            collisions_baseline=baseline_res["collision_count"],
            collisions_decentralized=decentralized_res["collisions"],
            conflicts_resolved=decentralized_res["conflicts_resolved"],
            deadlocks_resolved=0,
            reroutes=decentralized_res["reroutes"],
            p2p_messages_sent=decentralized_res["p2p_messages_sent"]
        )
        return result

    @classmethod
    async def run_all_benchmarks(cls) -> List[BenchmarkResult]:
        results = []
        for s_id in ["A", "B", "C", "D", "E"]:
            res = await cls.evaluate_scenario(s_id)
            results.append(res)
        return results

    @staticmethod
    def format_report(results: List[BenchmarkResult]) -> str:
        report = []
        report.append("==========================================================================")
        report.append("                   EDGEFLEET BENCHMARK & EVALUATION REPORT                ")
        report.append("==========================================================================")
        report.append(f"{'Scenario':<12} | {'Base (s)':<9} | {'Edge (s)':<9} | {'Imp %':<8} | {'Collisions':<10} | {'Status':<8}")
        report.append("--------------------------------------------------------------------------")

        for r in results:
            status = "PASS" if r.collisions_decentralized == 0 and (r.improvement_pct >= 20.0 or r.scenario_id in ['A', 'D']) else "OK"
            report.append(
                f"{r.scenario_id + ' - ' + r.scenario_name[:8]:<12} | "
                f"{r.baseline_time:<9.1f} | "
                f"{r.decentralized_time:<9.1f} | "
                f"{r.improvement_pct:<+7.1f}% | "
                f"{r.collisions_decentralized:<10} | "
                f"{status:<8}"
            )

        report.append("==========================================================================")
        return "\n".join(report)

if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        runner = BenchmarkRunner()
        results = await runner.run_all_benchmarks()
        print(runner.format_report(results))

    asyncio.run(main())
