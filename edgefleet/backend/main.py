"""
FastAPI Central Monitoring & Telemetry Backend
NOTE: The central server is purely an OBSERVER/MONITOR.
It does NOT make path planning or conflict resolution decisions for AMRs.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from edgefleet.simulation.warehouse import WarehouseMap
from edgefleet.simulation.engine import SimulationEngine
from edgefleet.simulation.tasks import Task, TaskStatus
from edgefleet.benchmarks.scenarios import SCENARIOS, ScenarioDefinition
from edgefleet.benchmarks.runner import BenchmarkRunner
from edgefleet.backend.websocket import ws_manager
from edgefleet.backend.telemetry import telemetry_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("edgefleet.backend")

# Global Simulation Engine instance
engine: Optional[SimulationEngine] = None
telemetry_broadcast_task: Optional[asyncio.Task] = None

async def telemetry_loop():
    """Background broadcast loop pushing 20Hz telemetry packets to WebSocket subscribers."""
    while True:
        try:
            if engine:
                state_dict = engine.to_dict()

                # Extract recent P2P messages from all robots
                p2p_logs = []
                for r in engine.robots.values():
                    for sent in r.p2p_node.sent_messages_log[-10:]:
                        p2p_logs.append(sent)

                # Sort by timestamp
                p2p_logs.sort(key=lambda x: x.get("timestamp", 0.0), reverse=True)
                state_dict["p2p_logs"] = p2p_logs[:30]

                await ws_manager.broadcast(state_dict)
        except Exception as e:
            logger.debug(f"Telemetry broadcast error: {e}")
        await asyncio.sleep(0.05)  # 20 Hz

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, telemetry_broadcast_task
    # Initialize default simulation with Scenario B (Overlapping Paths) for rich immediate demo
    engine = SimulationEngine()
    scenario_b = SCENARIOS["B"]()

    port_base = 9100
    for idx, (r_id, spawn) in enumerate(scenario_b.robot_spawns.items()):
        engine.add_robot(robot_id=r_id, initial_pos=spawn, port=port_base + idx)

    await engine.initialize_fleet_p2p()

    for t in scenario_b.tasks:
        engine.add_task(t)
        for r_id, r in engine.robots.items():
            if r.state.status.value == "IDLE" and not r.current_task:
                await r.assign_task(t)
                break

    engine.start_loop()
    telemetry_broadcast_task = asyncio.create_task(telemetry_loop())
    logger.info("EdgeFleet Monitoring Backend started successfully.")

    yield

    if engine:
        await engine.stop()
    if telemetry_broadcast_task:
        telemetry_broadcast_task.cancel()

app = FastAPI(title="EdgeFleet Telemetry Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class SpeedRequest(BaseModel):
    speed_multiplier: float

class BlockCellRequest(BaseModel):
    x: int
    y: int

class CreateTaskRequest(BaseModel):
    id: str
    pickup_x: int
    pickup_y: int
    drop_x: int
    drop_y: int
    priority: int = 1

# API Endpoints
@app.get("/api/health")
async def health():
    return {"status": "ONLINE", "mode": "OBSERVER_TELEMETRY"}

@app.get("/api/warehouse")
async def get_warehouse():
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    return engine.warehouse.to_dict()

@app.get("/api/fleet")
async def get_fleet():
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    return {r_id: r.to_dict() for r_id, r in engine.robots.items()}

@app.get("/api/tasks")
async def get_tasks():
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    return {t_id: t.to_dict() for t_id, t in engine.tasks.items()}

@app.get("/api/metrics")
async def get_metrics():
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    return engine.get_summary_metrics()

@app.post("/api/simulation/start")
async def start_simulation():
    if engine:
        engine.start_loop()
        return {"status": "STARTED"}
    return {"status": "NO_ENGINE"}

@app.post("/api/simulation/pause")
async def pause_simulation():
    if engine:
        engine.is_running = False
        return {"status": "PAUSED"}
    return {"status": "NO_ENGINE"}

@app.post("/api/simulation/reset")
async def reset_simulation():
    global engine
    if engine:
        await engine.stop()
    engine = SimulationEngine()
    scenario_b = SCENARIOS["B"]()
    port_base = 9100
    for idx, (r_id, spawn) in enumerate(scenario_b.robot_spawns.items()):
        engine.add_robot(robot_id=r_id, initial_pos=spawn, port=port_base + idx)
    await engine.initialize_fleet_p2p()
    for t in scenario_b.tasks:
        engine.add_task(t)
        for r_id, r in engine.robots.items():
            if r.state.status.value == "IDLE" and not r.current_task:
                await r.assign_task(t)
                break
    engine.start_loop()
    return {"status": "RESET_TO_DEFAULT"}

@app.post("/api/simulation/speed")
async def set_speed(req: SpeedRequest):
    if engine:
        engine.speed_multiplier = max(0.1, min(10.0, req.speed_multiplier))
        return {"speed_multiplier": engine.speed_multiplier}
    return {"status": "NO_ENGINE"}

@app.post("/api/simulation/scenario/{scenario_id}")
async def load_scenario(scenario_id: str):
    global engine
    s_id = scenario_id.upper()
    if s_id not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Invalid scenario ID: {scenario_id}")

    scenario_builder = SCENARIOS[s_id]
    scenario = scenario_builder()

    if engine:
        await engine.stop()

    warehouse = WarehouseMap.create_default()
    for obs in scenario.dynamic_obstacles:
        warehouse.add_dynamic_obstacle(obs)

    engine = SimulationEngine(warehouse=warehouse)
    port_base = 9100
    for idx, (r_id, spawn) in enumerate(scenario.robot_spawns.items()):
        engine.add_robot(robot_id=r_id, initial_pos=spawn, port=port_base + idx)

    await engine.initialize_fleet_p2p()

    for t in scenario.tasks:
        engine.add_task(t)
        for r_id, r in engine.robots.items():
            if r.state.status.value == "IDLE" and not r.current_task:
                await r.assign_task(t)
                break

    engine.start_loop()
    return {"status": "LOADED", "scenario": scenario.name}

@app.post("/api/simulation/block-cell")
async def toggle_block_cell(req: BlockCellRequest):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    pos = (req.x, req.y)
    if pos in engine.warehouse.dynamic_obstacles:
        engine.remove_dynamic_obstacle(pos)
        return {"status": "UNBLOCKED", "cell": [req.x, req.y]}
    else:
        engine.add_dynamic_obstacle(pos, reason="Manual Obstacle Injection")
        return {"status": "BLOCKED", "cell": [req.x, req.y]}

@app.post("/api/tasks/create")
async def create_task(req: CreateTaskRequest):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not initialized")
    task = Task(
        id=req.id,
        pickup_location=(req.pickup_x, req.pickup_y),
        drop_location=(req.drop_x, req.drop_y),
        priority=req.priority
    )
    engine.add_task(task)

    # Assign to first free idle robot
    for r in engine.robots.values():
        if r.state.status.value == "IDLE" and not r.current_task:
            await r.assign_task(task)
            break

    return {"status": "TASK_CREATED", "task": task.to_dict()}

@app.post("/api/benchmarks/run/{scenario_id}")
async def run_benchmark(scenario_id: str):
    s_id = scenario_id.upper()
    if s_id not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Invalid scenario: {scenario_id}")
    result = await BenchmarkRunner.evaluate_scenario(s_id)
    telemetry_db.log_benchmark_result(result.to_dict())
    return result.to_dict()

@app.post("/api/benchmarks/run-all")
async def run_all_benchmarks():
    results = await BenchmarkRunner.run_all_benchmarks()
    for r in results:
        telemetry_db.log_benchmark_result(r.to_dict())
    return [r.to_dict() for r in results]

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep alive and listen for client commands if any
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
