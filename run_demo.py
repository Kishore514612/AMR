"""
EdgeFleet: Single-Command Launch and Demo Script
"""
import argparse
import asyncio
import subprocess
import sys
import os
import uvicorn

def run_benchmark():
    from edgefleet.benchmarks.runner import BenchmarkRunner
    async def _main():
        print("\n==========================================================================")
        print("                  RUNNING EDGEFLEET BENCHMARK SUITE                       ")
        print("==========================================================================")
        results = await BenchmarkRunner.run_all_benchmarks()
        print(BenchmarkRunner.format_report(results))
    asyncio.run(_main())

def run_server():
    print("Starting EdgeFleet FastAPI & WebSocket Monitoring Server on http://127.0.0.1:8000 ...")
    uvicorn.run("edgefleet.backend.main:app", host="127.0.0.1", port=8000, reload=False)

def main():
    parser = argparse.ArgumentParser(description="EdgeFleet Demo Runner")
    parser.add_argument("--benchmark", action="store_true", help="Run automated benchmarks & report")
    parser.add_argument("--server", action="store_true", help="Run FastAPI backend only")
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark()
    else:
        run_server()

if __name__ == "__main__":
    main()
