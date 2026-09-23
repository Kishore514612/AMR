"""
End-to-End Quantitative Benchmark Comparison Test (EdgeFleet vs Stop-and-Wait)
"""
import pytest
import asyncio
from edgefleet.benchmarks.runner import BenchmarkRunner

@pytest.mark.asyncio
async def test_benchmark_overlapping_paths_improvement():
    """
    Evaluates Scenario B (Overlapping Paths) under both EdgeFleet and Stop-and-Wait baseline.
    Validates:
    1. Zero collisions in EdgeFleet
    2. >= 20% reduction in completion time under overlapping traffic
    """
    result = await BenchmarkRunner.evaluate_scenario("B")

    print("\n--- BENCHMARK RESULTS (SCENARIO B) ---")
    print(f"Stop-and-Wait Baseline Time: {result.baseline_time:.2f}s")
    print(f"EdgeFleet Decentralized Time: {result.decentralized_time:.2f}s")
    print(f"Improvement: {result.improvement_pct:.2f}%")
    print(f"Collisions: {result.collisions_decentralized}")

    # Core Acceptance Criteria
    assert result.collisions_decentralized == 0, "Collisions must be strictly ZERO!"
    assert result.improvement_pct >= 20.0, f"Expected >= 20% improvement, got {result.improvement_pct:.2f}%"
