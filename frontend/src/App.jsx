import React, { useState, useEffect } from 'react';
import { useTelemetryWS } from './hooks/useTelemetryWS';
import { WarehouseCanvas } from './components/WarehouseCanvas';
import { RobotCards } from './components/RobotCards';
import { P2PLogViewer } from './components/P2PLogViewer';
import { ControlPanel } from './components/ControlPanel';
import { MetricsOverview } from './components/MetricsOverview';
import { BenchmarkModal } from './components/BenchmarkModal';
import { Layers, ShieldCheck, Activity, Cpu, Sparkles, Terminal } from 'lucide-react';

export default function App() {
  const { data, isConnected, lastMessageTime } = useTelemetryWS();
  const [speed, setSpeed] = useState(1.0);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);

  const warehouse = data?.warehouse;
  const robots = data?.robots || {};
  const dynamicObstacles = data?.dynamic_obstacles || {};
  const metrics = data?.metrics || {};
  const p2pLogs = data?.p2p_logs || [];
  const isRunning = data?.is_running || false;
  const simTime = data?.sim_time || 0.0;

  // Control Handlers
  const handlePlay = async () => {
    try {
      await fetch('/api/simulation/start', { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const handlePause = async () => {
    try {
      await fetch('/api/simulation/pause', { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const handleReset = async () => {
    try {
      await fetch('/api/simulation/reset', { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const handleSpeedChange = async (newSpeed) => {
    setSpeed(newSpeed);
    try {
      await fetch('/api/simulation/speed', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed_multiplier: newSpeed }),
      });
    } catch (e) {
      console.error(e);
    }
  };

  const handleLoadScenario = async (scenarioId) => {
    try {
      await fetch(`/api/simulation/scenario/${scenarioId}`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleBlockCell = async (x, y) => {
    try {
      await fetch('/api/simulation/block-cell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x, y }),
      });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col selection:bg-cyan-500 selection:text-black">
      {/* Top Navigation Header */}
      <header className="border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-xl sticky top-0 z-40 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-black text-slate-950 shadow-lg shadow-cyan-500/20">
              <Cpu className="w-5 h-5 text-slate-950" />
            </div>
            <div>
              <h1 className="text-base font-extrabold tracking-tight text-white flex items-center gap-2">
                EDGEFLEET
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono-code font-bold">
                  P2P AMR COORDINATOR
                </span>
              </h1>
              <p className="text-[11px] text-slate-400 font-mono-code">
                Decentralized Multi-Agent Coordination • Zero Cloud Collision Dependency
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono-code">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800">
              <span
                className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
                }`}
              ></span>
              <span className="text-slate-400">
                Server Telemetry: <strong className={isConnected ? 'text-emerald-400' : 'text-red-400'}>{isConnected ? 'OBSERVING' : 'OFFLINE (P2P ACTIVE)'}</strong>
              </span>
            </div>

            <button
              onClick={() => setIsBenchmarkOpen(true)}
              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold transition-all shadow-md hover:shadow-cyan-500/20 flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 fill-slate-950" />
              Benchmarks
            </button>
          </div>
        </div>
      </header>

      {/* Main Dashboard Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Top Metric Cards */}
        <MetricsOverview metrics={metrics} isConnected={isConnected} simTime={simTime} />

        {/* Central Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: 2D Warehouse Spatial Canvas */}
          <div className="lg:col-span-8 space-y-6">
            <WarehouseCanvas
              warehouse={warehouse}
              robots={robots}
              dynamicObstacles={dynamicObstacles}
              onToggleBlockCell={handleToggleBlockCell}
            />

            {/* Individual Robot Live Cards */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono-code flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  Independent AMR Agent Telemetry
                </h3>
                <span className="text-xs text-slate-500 font-mono-code">
                  Individual Space-Time Planners
                </span>
              </div>
              <RobotCards robots={robots} />
            </div>
          </div>

          {/* Right Column: Simulation Controls & Live P2P Wiretap */}
          <div className="lg:col-span-4 space-y-6">
            {/* Control Panel */}
            <ControlPanel
              isRunning={isRunning}
              speed={speed}
              onPlay={handlePlay}
              onPause={handlePause}
              onReset={handleReset}
              onSpeedChange={handleSpeedChange}
              onLoadScenario={handleLoadScenario}
              onOpenBenchmark={() => setIsBenchmarkOpen(true)}
            />

            {/* P2P Log Packet Sniffer */}
            <P2PLogViewer logs={p2pLogs} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 px-6 py-3 text-center text-xs text-slate-500 font-mono-code">
        EdgeFleet Decentralized Architecture • Smart India Hackathon Autonomous Fleet Solution
      </footer>

      {/* Benchmark Modal */}
      <BenchmarkModal isOpen={isBenchmarkOpen} onClose={() => setIsBenchmarkOpen(false)} />
    </div>
  );
}
