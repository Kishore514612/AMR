"""
EdgeFleet System Configuration
"""
from dataclasses import dataclass
from typing import Dict, Tuple

# Grid Dimensions
DEFAULT_GRID_WIDTH: int = 30
DEFAULT_GRID_HEIGHT: int = 50

# Physical & Kinematic Specs
ROBOT_MAX_SPEED: float = 1.0       # cells per simulation second
ROBOT_SAFETY_RADIUS: float = 0.8   # min distance in cells to avoid collision
ROBOT_DEFAULT_BATTERY: float = 2.0
BATTERY_CONSUMPTION_RATE: float = 0.05 # % per step
BATTERY_LOW_THRESHOLD: float = 20.0

# Scalable P2P Communication Specs
DEFAULT_COMMUNICATION_RADIUS: float = 8.0  # cells: detailed state shared within this radius
HEARTBEAT_INTERVAL: float = 1.0            # seconds
PEER_TIMEOUT: float = 3.5                  # seconds
MAX_MESSAGE_HISTORY: int = 500
STALE_MESSAGE_THRESHOLD: float = 5.0       # seconds

# Reservation & Time-A* Parameters
TIME_STEP: float = 1.0                     # seconds per planning horizon step
MAX_TIME_HORIZON: int = 60                 # steps (prevent infinite graph expansion)
RESERVATION_EXPIRY_BUFFER: float = 2.0     # seconds beyond ETA before automatic expiry

# Deadlock Detection
DEADLOCK_WAIT_THRESHOLD: float = 4.0       # seconds waiting in place before deadlock alert
MAX_REROUTE_ATTEMPTS: int = 3

# Priority Formula Weights:
# Priority = w_urgency * Urgency + w_wait * WaitTime - w_eta * ETA + w_battery * (100 - Battery)
PRIORITY_WEIGHT_URGENCY: float = 10.0
PRIORITY_WEIGHT_WAIT_TIME: float = 2.0
PRIORITY_WEIGHT_ETA: float = 0.5
PRIORITY_WEIGHT_BATTERY: float = 0.1

# Network Ports for Local Simulated AMRs
DEFAULT_ROBOT_PORTS: Dict[str, int] = {
    "R1": 9001,
    "R2": 9002,
    "R3": 9003,
    "R4": 9004,
    "R5": 9005,
}

BACKEND_HOST: str = "127.0.0.1"
BACKEND_PORT: int = 8000
