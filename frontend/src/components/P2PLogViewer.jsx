import React, { useState } from 'react';
import { Terminal, Radio, Filter, Trash2 } from 'lucide-react';

const MSG_COLORS = {
  CONFLICT_REQUEST: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  CONFLICT_RESPONSE: 'text-amber-300 bg-amber-500/10 border-amber-500/30',
  RESERVATION_REQUEST: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  RESERVATION_GRANTED: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  YIELD: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  PROCEED: 'text-blue-400 bg-blue-500/10 border-blue-400/30',
  RESERVATION_RELEASE: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
  REROUTE: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  DEADLOCK_ALERT: 'text-red-400 bg-red-500/10 border-red-500/30',
  INTENT_UPDATE: 'text-slate-300 bg-slate-800 border-slate-700',
  HEARTBEAT: 'text-slate-500 bg-slate-900 border-slate-800',
};

export function P2PLogViewer({ logs = [] }) {
  const [filterType, setFilterType] = useState('ALL');

  const filteredLogs = logs.filter((log) => {
    if (filterType === 'ALL') return true;
    if (filterType === 'CONFLICTS') return ['CONFLICT_REQUEST', 'CONFLICT_RESPONSE', 'YIELD', 'PROCEED', 'DEADLOCK_ALERT'].includes(log.type);
    if (filterType === 'RESERVATIONS') return ['RESERVATION_REQUEST', 'RESERVATION_GRANTED', 'RESERVATION_RELEASE'].includes(log.type);
    return log.type === filterType;
  });

  return (
    <div className="glass-card rounded-2xl p-4 border border-slate-800 shadow-xl flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold tracking-wider uppercase text-slate-300 font-mono-code">
            P2P Coordination Wiretap (Direct TCP Stream)
          </h3>
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center gap-1.5 text-[11px] font-mono-code">
          {['ALL', 'CONFLICTS', 'RESERVATIONS'].map((f) => (
            <button
              key={f}
              onClick={() => setFilterType(f)}
              className={`px-2 py-0.5 rounded-md transition-all ${
                filterType === f
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Terminal Log Stream */}
      <div className="flex-1 overflow-y-auto mt-3 space-y-1.5 font-mono-code text-xs pr-1 max-h-72 min-h-48">
        {filteredLogs.length === 0 ? (
          <div className="text-slate-500 text-center py-8 italic">
            Waiting for P2P coordination packets...
          </div>
        ) : (
          filteredLogs.map((log, idx) => {
            const timeStr = new Date((log.timestamp || Date.now() / 1000) * 1000)
              .toISOString()
              .substring(14, 21);
            const badgeStyle = MSG_COLORS[log.type] || 'text-slate-400 bg-slate-800 border-slate-700';

            return (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-slate-800/60 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-slate-500 text-[10px]">{timeStr}</span>
                  <div className="flex items-center gap-1 font-bold">
                    <span className="text-cyan-400">{log.sender}</span>
                    <span className="text-slate-500">➔</span>
                    <span className="text-emerald-400">{log.recipient || 'PEERS'}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${badgeStyle}`}>
                    {log.type}
                  </span>
                </div>

                {log.seq && (
                  <span className="text-[10px] text-slate-600 hidden sm:inline">
                    seq#{log.seq}
                  </span>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
