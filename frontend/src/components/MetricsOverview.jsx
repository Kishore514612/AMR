import React from 'react';
import { Bot, CheckCircle2, Clock, ShieldAlert, Cpu, GitBranch, Shuffle } from 'lucide-react';

export function MetricsOverview({ metrics, isConnected, simTime }) {
  const activeRobots = metrics?.active_robots || 0;
  const completedTasks = metrics?.completed_tasks || 0;
  const totalTasks = metrics?.total_tasks || 0;
  const totalWaitTime = metrics?.total_wait_time || 0;
  const conflictsResolved = metrics?.total_conflicts_resolved || 0;
  const reroutes = metrics?.total_reroutes || 0;
  const collisions = metrics?.collision_count || 0;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {/* 1. Decentralized Mesh Status */}
      <div className="glass-card rounded-2xl p-3 border border-slate-800 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono-code mb-1">
          <span>P2P MESH</span>
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="text-sm font-bold text-slate-100 font-mono-code">DECENTRALIZED</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono-code mt-1">Observer Only Backend</span>
      </div>

      {/* 2. Active Robots */}
      <div className="glass-card rounded-2xl p-3 border border-slate-800 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono-code mb-1">
          <span>ACTIVE FLEET</span>
          <Bot className="w-3.5 h-3.5 text-cyan-400" />
        </div>
        <div className="text-xl font-bold text-cyan-400 font-mono-code">
          {activeRobots} <span className="text-xs text-slate-400 font-normal">AMRs</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono-code mt-1">Sim Time: {simTime?.toFixed(1)}s</span>
      </div>

      {/* 3. Tasks Completed */}
      <div className="glass-card rounded-2xl p-3 border border-slate-800 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono-code mb-1">
          <span>TASKS DONE</span>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div className="text-xl font-bold text-emerald-400 font-mono-code">
          {completedTasks} / {totalTasks}
        </div>
        <span className="text-[10px] text-slate-500 font-mono-code mt-1">Throughput High</span>
      </div>

      {/* 4. Total Wait Time */}
      <div className="glass-card rounded-2xl p-3 border border-slate-800 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono-code mb-1">
          <span>WAIT TIME</span>
          <Clock className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <div className="text-xl font-bold text-amber-400 font-mono-code">
          {totalWaitTime.toFixed(1)} <span className="text-xs text-slate-400 font-normal">sec</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono-code mt-1">Minimized Stalls</span>
      </div>

      {/* 5. Conflicts Resolved */}
      <div className="glass-card rounded-2xl p-3 border border-slate-800 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono-code mb-1">
          <span>NEGOTIATIONS</span>
          <Shuffle className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="text-xl font-bold text-purple-400 font-mono-code">
          {conflictsResolved} <span className="text-xs text-slate-400 font-normal">Resolved</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono-code mt-1">{reroutes} Reroutes Done</span>
      </div>

      {/* 6. Inter-Robot Collisions */}
      <div className="glass-card rounded-2xl p-3 border border-slate-800 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono-code mb-1">
          <span>COLLISIONS</span>
          <ShieldAlert className={`w-3.5 h-3.5 ${collisions === 0 ? 'text-emerald-400' : 'text-red-400'}`} />
        </div>
        <div className={`text-xl font-bold font-mono-code ${collisions === 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {collisions} <span className="text-xs text-slate-400 font-normal">Violations</span>
        </div>
        <span className="text-[10px] text-emerald-400/90 font-mono-code mt-1 font-semibold">
          100% Safety Envelope
        </span>
      </div>
    </div>
  );
}
