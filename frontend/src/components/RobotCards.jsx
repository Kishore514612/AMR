import React from 'react';
import { Battery, Zap, Activity, Navigation, Radio, ShieldCheck } from 'lucide-react';

const STATUS_BADGES = {
  IDLE: { bg: 'bg-slate-700/50 text-slate-300 border-slate-600', dot: 'bg-slate-400' },
  MOVING: { bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30', dot: 'bg-cyan-400 animate-pulse' },
  NEGOTIATING: { bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30', dot: 'bg-amber-400 animate-ping' },
  YIELDING: { bg: 'bg-purple-500/10 text-purple-400 border-purple-500/30', dot: 'bg-purple-400' },
  REROUTING: { bg: 'bg-orange-500/10 text-orange-400 border-orange-500/30', dot: 'bg-orange-400 animate-bounce' },
  DEADLOCKED: { bg: 'bg-red-500/10 text-red-400 border-red-500/30', dot: 'bg-red-400' },
  CHARGING: { bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30', dot: 'bg-emerald-400 animate-pulse' },
};

export function RobotCards({ robots }) {
  if (!robots || Object.keys(robots).length === 0) {
    return (
      <div className="text-sm text-slate-500 font-mono-code italic text-center py-6">
        No active AMRs detected on mesh.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {Object.values(robots).map((robot) => {
        const badge = STATUS_BADGES[robot.status] || STATUS_BADGES.IDLE;
        const batteryPct = Math.round(robot.battery || 100);
        const isLowBattery = batteryPct < 25;

        return (
          <div
            key={robot.robot_id}
            className="glass-card rounded-2xl p-4 border border-slate-800 hover:border-cyan-500/40 transition-all duration-300 shadow-lg relative overflow-hidden group"
          >
            {/* Top Row: Robot ID & Status */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-sm text-cyan-400 font-mono-code">
                  {robot.robot_id}
                </div>
                <div>
                  <span className="text-xs text-slate-400 font-mono-code block">Port :{robot.port}</span>
                </div>
              </div>

              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${badge.bg}`}
              >
                <span className={`w-2 h-2 rounded-full ${badge.dot}`}></span>
                {robot.status}
              </span>
            </div>

            {/* Battery & Kinematics */}
            <div className="space-y-3 my-3">
              {/* Battery Bar */}
              <div>
                <div className="flex justify-between text-xs mb-1 font-mono-code text-slate-400">
                  <span className="flex items-center gap-1">
                    <Battery className={`w-3.5 h-3.5 ${isLowBattery ? 'text-red-400' : 'text-emerald-400'}`} />
                    Battery Level
                  </span>
                  <span className={isLowBattery ? 'text-red-400 font-bold' : 'text-slate-200'}>
                    {batteryPct}%
                  </span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700/50">
                  <div
                    className={`h-full transition-all duration-500 ${
                      isLowBattery ? 'bg-red-500' : 'bg-gradient-to-r from-emerald-500 to-cyan-400'
                    }`}
                    style={{ width: `${batteryPct}%` }}
                  ></div>
                </div>
              </div>

              {/* Grid Location & Speed */}
              <div className="grid grid-cols-2 gap-2 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80 text-xs font-mono-code">
                <div>
                  <span className="text-slate-500 block text-[10px]">CURRENT POSE</span>
                  <span className="text-slate-200 font-semibold">
                    ({robot.pose?.x.toFixed(1)}, {robot.pose?.y.toFixed(1)})
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">SPEED / ETA</span>
                  <span className="text-cyan-400 font-semibold">
                    {robot.velocity > 0 ? `${robot.velocity.toFixed(1)} m/s` : '0 m/s'} • {robot.eta?.toFixed(1)}s
                  </span>
                </div>
              </div>
            </div>

            {/* Task & Active Reservation */}
            <div className="pt-2 border-t border-slate-800/80 text-xs space-y-1.5 font-mono-code">
              <div className="flex justify-between items-center text-slate-400">
                <span className="flex items-center gap-1">
                  <Navigation className="w-3.5 h-3.5 text-cyan-400" />
                  Task:
                </span>
                <span className="text-slate-200 truncate max-w-[140px]">
                  {robot.current_task_id || 'IDLE (Awaiting Dispatch)'}
                </span>
              </div>

              <div className="flex justify-between items-center text-slate-400">
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  P2P Peers:
                </span>
                <span className="text-emerald-400">
                  {robot.peers ? Object.keys(robot.peers).length : 0} Connected
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
