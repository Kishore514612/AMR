# EdgeFleet — Decentralized P2P AMR Fleet Coordination Simulator

> **Smart India Hackathon (SIH) Solution**: Autonomous Mobile Robot (AMR) Fleet Coordination and Collision Avoidance Framework for Dynamic Smart Warehouses.

---

## 1. Core Architectural Principle

```
                 CENTRAL SYSTEM (FastAPI / WebSockets)
                               │
                          "OBSERVE" (Telemetry Only)
                               │
                               ▼
        ┌─────────────────────────────────────────────────────────┐
        │  RELEVANCE-BASED P2P COORDINATION MESH (Independent)    │
        │                                                         │
        │              R1 ◄──────────► R2                         │
        │               ▲               ▲                         │
        │               │   "COORDINATE"│                         │
        │               └────── R3 ─────┘                         │
        └─────────────────────────────────────────────────────────┘
```

* **Zero Central Point of Failure**: Safety-critical collision avoidance, conflict negotiation, space-time reservations, and deadlock resolution happen directly between robot agents over P2P TCP connections.
* **Server-Down Resilience**: If the central backend is terminated (Scenario F), the AMRs continue navigating, negotiating, and completing jobs safely with **0 collisions**.
* **Scalability ($O(K)$ Local Traffic)**: Uses relevance-based neighborhood filtering and spatial trajectory bounding boxes to prevent $O(N^2)$ network chatter.

---

## 2. Key Features

1. **Space-Time A\* Path Planning**: Full $(x, y, t)$ search space supporting static obstacles, dynamic reservations, wait actions, and dynamic rerouting.
2. **Deterministic Conflict Resolution**: Multi-factor priority evaluation (task urgency, wait time, ETA, battery) with stable Robot ID tie-breaking, ensuring identical decisions on both sides without centralized mediation.
3. **Critical-Zone & Intersection Reservations**: Space-time window locking with automatic timeouts and release broadcasts.
4. **Distributed Deadlock Cycle Detection**: Cycle detection in distributed wait-for graphs with deterministic evasion maneuvers.
5. **Local Safety Envelope**: Continuous proximity checks enforcing a strict $0.8$-cell safety bubble.
6. **Real Stop-and-Wait Baseline & Benchmarks**: Automated Monte Carlo comparison demonstrating $> 20\%$ efficiency improvements under overlapping traffic with **0 collisions**.
7. **Interactive React + Vite Dashboard**: High-DPI 2D warehouse canvas, live P2P packet sniffer log, robot telemetry cards, dynamic obstacle injector, and benchmark analysis.

---

## 3. Quick Start Guide

### Prerequisites
* Python 3.11+
* Node.js 18+ and npm

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### 2. Run Automated Test Suite (28 Tests)
```powershell
python -m pytest tests/ -v
```

### 3. Run Benchmark Suite
```powershell
python run_demo.py --benchmark
```

### 4. Launch Full Stack Dashboard
**Terminal 1 (Backend):**
```powershell
python run_demo.py
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm run dev
```
Open your browser at `http://localhost:3000`.

---

## 4. Test Report & Verification

```text
==========================================================================
                   EDGEFLEET BENCHMARK & EVALUATION REPORT                
==========================================================================
Scenario     | Base (s)  | Edge (s)  | Imp %    | Collisions | Status  
--------------------------------------------------------------------------
A - Normal   | 28.0      | 28.0      | +0.0%    | 0          | PASS    
B - Overlap  | 300.1     | 28.9      | +90.4%   | 0          | PASS    
C - EqualPri | 300.1     | 20.9      | +93.0%   | 0          | PASS    
D - Blocked  | 35.0      | 29.0      | +17.1%   | 0          | PASS    
E - Deadlock | 300.1     | 4.4       | +98.5%   | 0          | PASS    
==========================================================================
Target (>= 20% under overlapping traffic): PASS
Central Server Required for Coordination: NO
Zero Collisions: PASS (0 collisions across all runs)
==========================================================================
```
