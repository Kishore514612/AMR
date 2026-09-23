import React, { useState } from 'react';
import { Play, Pause, RotateCcw, FastForward, Plus, Layers, AlertTriangle } from 'lucide-react';

export function ControlPanel({ isRunning, speed, onPlay, onPause, onReset, onSpeedChange, onLoadScenario, onOpenBenchmark }) {
  const [selectedScenario, setSelectedScenario] = useState('B');
  const [taskPickup, setTaskPickup] = useState('2,2');
  const [taskDrop, setTaskDrop] = useState('28,17');
  const [taskPriority, setTaskPriority] = useState(1);

  const scenarios = [
    { id: 'A', name: 'Scenario A: Normal (3 Independent AMRs)' },
    { id: 'B', name: 'Scenario B: Overlapping (4-Way Intersection)' },
    { id: 'C', name: 'Scenario C: Equal Priority (Tie-Breaker)' },
    { id: 'D', name: 'Scenario D: Blocked Aisle (Dynamic Reroute)' },
    { id: 'E', name: 'Scenario E: Multi-Robot Deadlock Resolution' },
    { id: 'F', name: 'Scenario F: Backend Server Down (Pure P2P)' },
  ];

  const handleScenarioChange = (e) => {
    const sId = e.target.value;
    setSelectedScenario(sId);
    if (onLoadScenario) {
      onLoadScenario(sId);
    }
  };

  const handleCreateCustomTask = async (e) => {
    e.preventDefault();
    const [px, py] = taskPickup.split(',').map((v) => parseInt(v.trim()));
    const [dx, dy] = taskDrop.split(',').map((v) => parseInt(v.trim()));

    if (isNaN(px) || isNaN(py) || isNaN(dx) || isNaN(dy)) {
      alert('Invalid coordinate format. Use x,y (e.g. 2,9)');
      return;
    }

    try {
      await fetch('/api/tasks/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: `TASK_CUSTOM_${Date.now().toString().slice(-4)}`,
          pickup_x: px,
          pickup_y: py,
          drop_x: dx,
          drop_y: dy,
          priority: parseInt(taskPriority),
        }),
      });
    } catch (err) {
      console.error('Failed creating task:', err);
    }
  };

  return (
    <div className="glass-card rounded-2xl p-4 border border-slate-800 shadow-xl space-y-4">
      {/* Scenario Selector & Benchmark Button */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2 flex-1 min-w-[280px]">
          <Layers className="w-4 h-4 text-cyan-400" />
          <select
            value={selectedScenario}
            onChange={handleScenarioChange}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 focus:outline-none focus:border-cyan-500 font-mono-code cursor-pointer"
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={onOpenBenchmark}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs tracking-wider uppercase transition-all shadow-lg hover:shadow-cyan-500/25 flex items-center gap-1.5"
        >
          <span>Run Benchmark vs Baseline</span>
        </button>
      </div>

      {/* Main Controls: Play / Pause / Reset & Speed */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {isRunning ? (
            <button
              onClick={onPause}
              className="px-4 py-2 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30 font-semibold text-xs flex items-center gap-2 transition-all font-mono-code"
            >
              <Pause className="w-4 h-4 fill-amber-400" />
              Pause Sim
            </button>
          ) : (
            <button
              onClick={onPlay}
              className="px-4 py-2 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 font-semibold text-xs flex items-center gap-2 transition-all font-mono-code"
            >
              <Play className="w-4 h-4 fill-emerald-400" />
              Start Sim
            </button>
          )}

          <button
            onClick={onReset}
            className="px-3 py-2 rounded-xl bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 font-semibold text-xs flex items-center gap-1.5 transition-all font-mono-code"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
        </div>

        {/* Speed Slider */}
        <div className="flex items-center gap-3 bg-slate-900/60 px-3 py-1.5 rounded-xl border border-slate-800 text-xs font-mono-code">
          <FastForward className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-slate-400">Speed:</span>
          <span className="text-cyan-400 font-bold w-8">{speed}x</span>
          <input
            type="range"
            min="0.5"
            max="5.0"
            step="0.5"
            value={speed}
            onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
            className="w-24 accent-cyan-400 cursor-pointer"
          />
        </div>
      </div>

      {/* Inject Custom Task */}
      <form onSubmit={handleCreateCustomTask} className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-3 text-xs font-mono-code">
        <span className="text-slate-400 flex items-center gap-1 font-semibold">
          <Plus className="w-3.5 h-3.5 text-cyan-400" />
          Add Task:
        </span>
        <div className="flex items-center gap-1.5">
          <label className="text-slate-500">Pickup</label>
          <input
            type="text"
            value={taskPickup}
            onChange={(e) => setTaskPickup(e.target.value)}
            className="w-16 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-center"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <label className="text-slate-500">Drop</label>
          <input
            type="text"
            value={taskDrop}
            onChange={(e) => setTaskDrop(e.target.value)}
            className="w-16 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-center"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <label className="text-slate-500">Priority</label>
          <select
            value={taskPriority}
            onChange={(e) => setTaskPriority(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-slate-200"
          >
            <option value="1">1 (Normal)</option>
            <option value="3">3 (Urgent)</option>
            <option value="5">5 (Critical)</option>
          </select>
        </div>
        <button
          type="submit"
          className="px-3 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 font-semibold"
        >
          Dispatch
        </button>
      </form>
    </div>
  );
}
