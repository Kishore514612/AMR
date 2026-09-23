"""
End-to-End Tests for Scenarios A through F
"""
import pytest
import asyncio
from edgefleet.benchmarks.scenarios import SCENARIOS
from edgefleet.benchmarks.runner import BenchmarkRunner

@pytest.mark.asyncio
async def test_scenario_a_normal():
    scenario = SCENARIOS["A"]()
    res = await BenchmarkRunner.run_decentralized_scenario(scenario, max_sim_time=120.0)
    assert res["collisions"] == 0
    assert res["sim_time"] > 0

@pytest.mark.asyncio
async def test_scenario_b_overlapping_paths():
    scenario = SCENARIOS["B"]()
    res = await BenchmarkRunner.run_decentralized_scenario(scenario, max_sim_time=120.0)
    assert res["collisions"] == 0
    # Demonstrates conflict resolution occurred
    assert res["p2p_messages_sent"] > 0

@pytest.mark.asyncio
async def test_scenario_c_equal_priority():
    scenario = SCENARIOS["C"]()
    res = await BenchmarkRunner.run_decentralized_scenario(scenario, max_sim_time=120.0)
    assert res["collisions"] == 0

@pytest.mark.asyncio
async def test_scenario_d_blocked_aisle():
    scenario = SCENARIOS["D"]()
    res = await BenchmarkRunner.run_decentralized_scenario(scenario, max_sim_time=120.0)
    assert res["collisions"] == 0

@pytest.mark.asyncio
async def test_scenario_e_deadlock():
    scenario = SCENARIOS["E"]()
    res = await BenchmarkRunner.run_decentralized_scenario(scenario, max_sim_time=120.0)
    assert res["collisions"] == 0

@pytest.mark.asyncio
async def test_scenario_f_server_unavailable():
    """
    Scenario F: The FastAPI central monitoring server is NOT running.
    The 3 AMRs coordinate strictly P2P and complete their tasks safely with 0 collisions.
    """
    scenario = SCENARIOS["F"]()
    res = await BenchmarkRunner.run_decentralized_scenario(scenario, max_sim_time=120.0)
    assert res["collisions"] == 0
    assert res["p2p_messages_sent"] > 0
