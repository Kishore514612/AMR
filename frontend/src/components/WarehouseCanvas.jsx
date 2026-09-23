import React, { useRef, useEffect, useState } from 'react';

const ROBOT_COLORS = {
  R1: '#06B6D4', // Cyan
  R2: '#10B981', // Emerald
  R3: '#8B5CF6', // Violet
  R4: '#F59E0B', // Amber
  R5: '#EC4899', // Pink
};

export function WarehouseCanvas({ warehouse, robots, dynamicObstacles, onToggleBlockCell }) {
  const canvasRef = useRef(null);
  const [hoverCoord, setHoverCoord] = useState(null);

  const width = warehouse?.width || 30;
  const height = warehouse?.height || 20;

  // Grid cell sizing
  const cellSize = 32;
  const canvasWidth = width * cellSize;
  const canvasHeight = height * cellSize;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear background
    ctx.fillStyle = '#0B0F19';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // 1. Draw Grid Lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x++) {
      ctx.beginPath();
      ctx.moveTo(x * cellSize, 0);
      ctx.lineTo(x * cellSize, canvasHeight);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * cellSize);
      ctx.lineTo(canvasWidth, y * cellSize);
      ctx.stroke();
    }

    // 2. Draw Critical Zones (Intersections & Bottlenecks)
    if (warehouse?.critical_zones) {
      Object.values(warehouse.critical_zones).forEach((zone) => {
        zone.cells.forEach(([cx, cy]) => {
          ctx.fillStyle = zone.zone_type === 'INTERSECTION' ? 'rgba(6, 182, 212, 0.12)' : 'rgba(245, 158, 11, 0.12)';
          ctx.fillRect(cx * cellSize, cy * cellSize, cellSize, cellSize);

          ctx.strokeStyle = zone.zone_type === 'INTERSECTION' ? 'rgba(6, 182, 212, 0.4)' : 'rgba(245, 158, 11, 0.4)';
          ctx.lineWidth = 1.5;
          ctx.strokeRect(cx * cellSize + 1, cy * cellSize + 1, cellSize - 2, cellSize - 2);
        });
      });
    }

    // 3. Draw Shelves
    if (warehouse?.shelves) {
      warehouse.shelves.forEach(([sx, sy]) => {
        ctx.fillStyle = '#1E293B';
        ctx.fillRect(sx * cellSize + 2, sy * cellSize + 2, cellSize - 4, cellSize - 4);
        ctx.strokeStyle = '#334155';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(sx * cellSize + 2, sy * cellSize + 2, cellSize - 4, cellSize - 4);

        // Rack inner lines
        ctx.strokeStyle = '#475569';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(sx * cellSize + 6, sy * cellSize + cellSize / 2);
        ctx.lineTo(sx * cellSize + cellSize - 6, sy * cellSize + cellSize / 2);
        ctx.stroke();
      });
    }

    // 4. Draw Walls
    if (warehouse?.walls) {
      warehouse.walls.forEach(([wx, wy]) => {
        ctx.fillStyle = '#0F172A';
        ctx.fillRect(wx * cellSize, wy * cellSize, cellSize, cellSize);
        ctx.strokeStyle = '#1E293B';
        ctx.strokeRect(wx * cellSize, wy * cellSize, cellSize, cellSize);
      });
    }

    // 5. Draw Charging Stations
    if (warehouse?.charging_stations) {
      Object.entries(warehouse.charging_stations).forEach(([name, [cx, cy]]) => {
        ctx.fillStyle = 'rgba(245, 158, 11, 0.2)';
        ctx.fillRect(cx * cellSize + 2, cy * cellSize + 2, cellSize - 4, cellSize - 4);
        ctx.fillStyle = '#F59E0B';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('⚡', cx * cellSize + cellSize / 2, cy * cellSize + cellSize / 2);
      });
    }

    // 6. Draw Pickup and Drop Points
    if (warehouse?.pickups) {
      Object.entries(warehouse.pickups).forEach(([name, [px, py]]) => {
        ctx.fillStyle = 'rgba(16, 185, 129, 0.25)';
        ctx.beginPath();
        ctx.arc(px * cellSize + cellSize / 2, py * cellSize + cellSize / 2, cellSize / 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#10B981';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.fillStyle = '#10B981';
        ctx.font = '9px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('P', px * cellSize + cellSize / 2, py * cellSize + cellSize / 2 + 3);
      });
    }

    if (warehouse?.drops) {
      Object.entries(warehouse.drops).forEach(([name, [dx, dy]]) => {
        ctx.fillStyle = 'rgba(59, 130, 246, 0.25)';
        ctx.beginPath();
        ctx.arc(dx * cellSize + cellSize / 2, dy * cellSize + cellSize / 2, cellSize / 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#3B82F6';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.fillStyle = '#3B82F6';
        ctx.font = '9px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('D', dx * cellSize + cellSize / 2, dy * cellSize + cellSize / 2 + 3);
      });
    }

    // 7. Draw Dynamic Obstacles
    if (dynamicObstacles) {
      Object.values(dynamicObstacles).forEach((obs) => {
        const [ox, oy] = obs.position;
        ctx.fillStyle = 'rgba(239, 68, 68, 0.35)';
        ctx.fillRect(ox * cellSize + 2, oy * cellSize + 2, cellSize - 4, cellSize - 4);
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 2;
        ctx.strokeRect(ox * cellSize + 2, oy * cellSize + 2, cellSize - 4, cellSize - 4);

        // Hazard X
        ctx.beginPath();
        ctx.moveTo(ox * cellSize + 6, oy * cellSize + 6);
        ctx.lineTo(ox * cellSize + cellSize - 6, oy * cellSize + cellSize - 6);
        ctx.moveTo(ox * cellSize + cellSize - 6, oy * cellSize + 6);
        ctx.lineTo(ox * cellSize + 6, oy * cellSize + cellSize - 6);
        ctx.stroke();
      });
    }

    // 8. Draw Planned Paths & Reservations
    if (robots) {
      Object.values(robots).forEach((robot) => {
        const color = ROBOT_COLORS[robot.robot_id] || '#06B6D4';

        // Draw trail / planned path
        if (robot.planned_path && robot.planned_path.length > 0) {
          ctx.strokeStyle = color;
          ctx.lineWidth = 2;
          ctx.setLineDash([4, 4]);
          ctx.beginPath();
          ctx.moveTo(robot.pose.x * cellSize + cellSize / 2, robot.pose.y * cellSize + cellSize / 2);
          robot.planned_path.forEach(([px, py]) => {
            ctx.lineTo(px * cellSize + cellSize / 2, py * cellSize + cellSize / 2);
          });
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // Draw reservations
        if (robot.reservations) {
          robot.reservations.forEach((res) => {
            const [rx, ry] = res.cell;
            ctx.fillStyle = `${color}22`;
            ctx.fillRect(rx * cellSize + 4, ry * cellSize + 4, cellSize - 8, cellSize - 8);
          });
        }
      });
    }

    // 9. Draw AMRs
    if (robots) {
      Object.values(robots).forEach((robot) => {
        const color = ROBOT_COLORS[robot.robot_id] || '#06B6D4';
        const cx = robot.pose.x * cellSize + cellSize / 2;
        const cy = robot.pose.y * cellSize + cellSize / 2;
        const radius = cellSize * 0.42;

        // Status Glow Ring
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, radius + 3, 0, Math.PI * 2);
        ctx.fillStyle = `${color}20`;
        ctx.fill();

        // AMR Body
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fillStyle = '#1E293B';
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.stroke();

        // Heading Arrow Indicator
        const headingLen = radius * 0.85;
        const hx = cx + Math.cos(robot.pose.theta) * headingLen;
        const hy = cy + Math.sin(robot.pose.theta) * headingLen;
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(hx, hy);
        ctx.stroke();

        // Label
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(robot.robot_id, cx, cy - 1);

        ctx.restore();
      });
    }
  }, [warehouse, robots, dynamicObstacles, canvasWidth, canvasHeight]);

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas || !onToggleBlockCell) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const cellX = Math.floor(clickX / cellSize);
    const cellY = Math.floor(clickY / cellSize);

    if (cellX >= 0 && cellX < width && cellY >= 0 && cellY < height) {
      onToggleBlockCell(cellX, cellY);
    }
  };

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const cellX = Math.floor((e.clientX - rect.left) / cellSize);
    const cellY = Math.floor((e.clientY - rect.top) / cellSize);
    if (cellX >= 0 && cellX < width && cellY >= 0 && cellY < height) {
      setHoverCoord({ x: cellX, y: cellY });
    } else {
      setHoverCoord(null);
    }
  };

  return (
    <div className="relative flex flex-col items-center glass-card p-4 rounded-2xl shadow-2xl border border-slate-800">
      <div className="flex justify-between items-center w-full mb-3 px-2">
        <div className="flex items-center gap-3">
          <span className="inline-block w-3 h-3 rounded-full bg-cyan-400 animate-pulse"></span>
          <h2 className="text-sm font-semibold tracking-wider uppercase text-slate-300 font-mono-code">
            Warehouse 2D Spatial Map (30 × 20)
          </h2>
        </div>
        <div className="text-xs text-slate-400 font-mono-code">
          {hoverCoord ? (
            <span className="text-cyan-400">Cell [{hoverCoord.x}, {hoverCoord.y}] • Click to toggle obstacle</span>
          ) : (
            <span>Click any aisle to inject/remove dynamic spill</span>
          )}
        </div>
      </div>

      <div className="relative overflow-auto max-w-full rounded-xl border border-slate-800/80 shadow-inner bg-[#0B0F19]">
        <canvas
          ref={canvasRef}
          width={canvasWidth}
          height={canvasHeight}
          onClick={handleCanvasClick}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoverCoord(null)}
          className="cursor-crosshair block"
        />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-center gap-5 mt-4 text-xs text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded bg-slate-800 border border-slate-700"></span>
          <span>Shelf Storage</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded bg-cyan-500/20 border border-cyan-400"></span>
          <span>Critical Intersection (X1)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded-full bg-emerald-500/20 border border-emerald-400"></span>
          <span>Pickup Bay</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded-full bg-blue-500/20 border border-blue-400"></span>
          <span>Drop Bay</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded bg-red-500/30 border border-red-500"></span>
          <span>Dynamic Obstacle</span>
        </div>
      </div>
    </div>
  );
}
