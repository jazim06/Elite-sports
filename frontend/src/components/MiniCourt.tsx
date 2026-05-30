/**
 * MiniCourt — Top-down mini court radar showing player positions.
 */
import type { PlayerData, BallData } from '../utils/types';
import { COURT } from '../utils/constants';

interface MiniCourtProps {
  players: PlayerData[];
  ball: BallData | null;
}

export function MiniCourt({ players, ball }: MiniCourtProps) {
  // SVG dimensions — scale court to SVG viewport
  const padding = 15;
  const svgWidth = 200;
  const svgHeight = (COURT.length / COURT.width) * svgWidth;
  const courtW = svgWidth - padding * 2;
  const courtH = svgHeight - padding * 2;

  // Scale court coordinates (meters) to SVG pixels
  const scaleX = (m: number) => padding + (m / COURT.width) * courtW;
  const scaleY = (m: number) => padding + (m / COURT.length) * courtH;

  const netY = scaleY(COURT.netPosition);
  const singleLeft = scaleX((COURT.width - COURT.singlesWidth) / 2);
  const singleRight = scaleX((COURT.width + COURT.singlesWidth) / 2);
  const serviceTopY = scaleY(COURT.netPosition - COURT.serviceLineDist);
  const serviceBotY = scaleY(COURT.netPosition + COURT.serviceLineDist);
  const centerX = scaleX(COURT.width / 2);

  // Player colors
  const playerColors = ['hsl(185, 85%, 55%)', 'hsl(25, 90%, 58%)'];

  return (
    <div className="mini-court-card" id="mini-court">
      <h3>📍 Court Position</h3>

      <svg
        className="mini-court-svg"
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        width="100%"
      >
        {/* Court background */}
        <rect
          x={padding}
          y={padding}
          width={courtW}
          height={courtH}
          fill="hsl(145, 50%, 22%)"
          rx="3"
        />

        {/* Court lines */}
        {/* Outer boundary */}
        <rect
          x={padding}
          y={padding}
          width={courtW}
          height={courtH}
          fill="none"
          stroke="hsla(0,0%,100%,0.6)"
          strokeWidth="1.5"
          rx="3"
        />

        {/* Singles lines */}
        <line x1={singleLeft} y1={padding} x2={singleLeft} y2={padding + courtH} stroke="hsla(0,0%,100%,0.4)" strokeWidth="0.8" />
        <line x1={singleRight} y1={padding} x2={singleRight} y2={padding + courtH} stroke="hsla(0,0%,100%,0.4)" strokeWidth="0.8" />

        {/* Net */}
        <line x1={padding} y1={netY} x2={padding + courtW} y2={netY} stroke="hsla(0,0%,100%,0.7)" strokeWidth="2" />

        {/* Service lines */}
        <line x1={singleLeft} y1={serviceTopY} x2={singleRight} y2={serviceTopY} stroke="hsla(0,0%,100%,0.4)" strokeWidth="0.8" />
        <line x1={singleLeft} y1={serviceBotY} x2={singleRight} y2={serviceBotY} stroke="hsla(0,0%,100%,0.4)" strokeWidth="0.8" />

        {/* Center service line */}
        <line x1={centerX} y1={serviceTopY} x2={centerX} y2={serviceBotY} stroke="hsla(0,0%,100%,0.4)" strokeWidth="0.8" />

        {/* Center marks */}
        <line x1={centerX} y1={padding} x2={centerX} y2={padding + 6} stroke="hsla(0,0%,100%,0.4)" strokeWidth="0.8" />
        <line x1={centerX} y1={padding + courtH - 6} x2={centerX} y2={padding + courtH} stroke="hsla(0,0%,100%,0.4)" strokeWidth="0.8" />

        {/* Player dots */}
        {players.map((player, i) => {
          const pos = player.court_position;
          if (!pos) return null;

          const px = scaleX(pos[0]);
          const py = scaleY(pos[1]);
          const color = playerColors[i % playerColors.length];

          return (
            <g key={player.id}>
              {/* Glow */}
              <circle cx={px} cy={py} r="8" fill={color} opacity="0.2" />
              {/* Dot */}
              <circle
                cx={px}
                cy={py}
                r="5"
                fill={color}
                stroke="white"
                strokeWidth="1.5"
              />
              {/* Label */}
              <text
                x={px}
                y={py - 9}
                textAnchor="middle"
                fill="white"
                fontSize="7"
                fontWeight="600"
                fontFamily="Inter, sans-serif"
              >
                P{player.id}
              </text>
            </g>
          );
        })}

        {/* Ball */}
        {ball?.position && (
          <g>
            <circle
              cx={scaleX(COURT.width / 2)} // fallback center if no court calibration
              cy={scaleY(COURT.netPosition)}
              r="3.5"
              fill="hsl(65, 95%, 55%)"
              stroke="hsl(65, 95%, 35%)"
              strokeWidth="1"
            />
          </g>
        )}
      </svg>
    </div>
  );
}
