/**
 * ShotPlacementChart — Top-down court view with shot landing scatter plot.
 */
import { useMemo } from 'react';
import { SHOT_COLORS, COURT } from '../utils/constants';

interface ShotPlacementChartProps {
  shots: Array<{ x: number; y: number; type: string }>;
  shotCounts: Record<string, number>;
}

export function ShotPlacementChart({ shots, shotCounts }: ShotPlacementChartProps) {
  const padding = 20;
  const svgWidth = 400;
  const svgHeight = (COURT.length / COURT.width) * svgWidth * 0.55; // show half court
  const courtW = svgWidth - padding * 2;
  const courtH = svgHeight - padding * 2;

  const scaleX = (m: number) => padding + (m / COURT.width) * courtW;
  const scaleY = (m: number) => padding + (m / (COURT.length / 2)) * courtH;

  // Generate some demo scatter if no real data yet
  const displayShots = useMemo(() => {
    if (shots.length > 0) return shots;

    // Demo data placeholder
    const types = ['forehand', 'backhand', 'serve', 'volley'];
    return Array.from({ length: 40 }, (_, i) => ({
      x: 1 + Math.random() * (COURT.width - 2),
      y: 0.5 + Math.random() * (COURT.length / 2 - 1),
      type: types[i % types.length],
    }));
  }, [shots]);

  const singleLeft = scaleX((COURT.width - COURT.singlesWidth) / 2);
  const singleRight = scaleX((COURT.width + COURT.singlesWidth) / 2);
  const serviceY = scaleY(COURT.serviceLineDist);
  const centerX = scaleX(COURT.width / 2);

  return (
    <div className="shot-placement-card" id="shot-placement">
      <h3>🎯 Shot Placement</h3>

      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} width="100%" className="mini-court-svg">
        {/* Court background (half court) */}
        <rect x={padding} y={padding} width={courtW} height={courtH} fill="hsl(220, 50%, 18%)" rx="4" />

        {/* Court lines */}
        <rect x={padding} y={padding} width={courtW} height={courtH} fill="none" stroke="hsla(0,0%,100%,0.4)" strokeWidth="1.5" rx="4" />

        {/* Singles lines */}
        <line x1={singleLeft} y1={padding} x2={singleLeft} y2={padding + courtH} stroke="hsla(0,0%,100%,0.3)" strokeWidth="0.8" />
        <line x1={singleRight} y1={padding} x2={singleRight} y2={padding + courtH} stroke="hsla(0,0%,100%,0.3)" strokeWidth="0.8" />

        {/* Service line */}
        <line x1={singleLeft} y1={serviceY} x2={singleRight} y2={serviceY} stroke="hsla(0,0%,100%,0.3)" strokeWidth="0.8" />

        {/* Center service line */}
        <line x1={centerX} y1={padding} x2={centerX} y2={serviceY} stroke="hsla(0,0%,100%,0.3)" strokeWidth="0.8" />

        {/* Baseline (net) */}
        <line x1={padding} y1={padding} x2={padding + courtW} y2={padding} stroke="hsla(0,0%,100%,0.5)" strokeWidth="2" />

        {/* Net label */}
        <text x={svgWidth / 2} y={10} textAnchor="middle" fill="hsla(0,0%,100%,0.4)" fontSize="8" fontFamily="Inter">
          NET
        </text>

        {/* Shot dots */}
        {displayShots.map((shot, i) => (
          <circle
            key={i}
            cx={scaleX(shot.x)}
            cy={scaleY(shot.y)}
            r="4"
            fill={SHOT_COLORS[shot.type] || SHOT_COLORS.unknown}
            opacity="0.8"
            stroke="hsla(0,0%,0%,0.3)"
            strokeWidth="0.5"
          />
        ))}
      </svg>

      {/* Legend */}
      <div className="shot-legend">
        {Object.entries(SHOT_COLORS)
          .filter(([k]) => k !== 'unknown')
          .map(([type, color]) => (
            <div className="shot-legend-item" key={type}>
              <div className="shot-legend-dot" style={{ background: color }} />
              <span>
                {type.charAt(0).toUpperCase() + type.slice(1)}
                {shotCounts[type] !== undefined && ` (${shotCounts[type]})`}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
