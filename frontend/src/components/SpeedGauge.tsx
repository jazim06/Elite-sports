/**
 * SpeedGauge — Radial gauge displaying ball and player speed.
 */
interface SpeedGaugeProps {
  ballSpeed: number;
  maxBallSpeed: number;
  playerSpeed: number;
}

export function SpeedGauge({ ballSpeed, maxBallSpeed, playerSpeed }: SpeedGaugeProps) {
  // SVG arc calculation for the gauge
  const maxSpeed = 200; // max gauge value (km/h)
  const radius = 60;
  const strokeWidth = 8;
  const centerX = 80;
  const centerY = 75;
  const startAngle = -210;
  const endAngle = 30;
  const totalAngle = endAngle - startAngle;

  const ballPct = Math.min(ballSpeed / maxSpeed, 1);
  const sweepAngle = ballPct * totalAngle;

  const polarToCart = (angle: number, r: number) => ({
    x: centerX + r * Math.cos((angle * Math.PI) / 180),
    y: centerY + r * Math.sin((angle * Math.PI) / 180),
  });

  const bgStart = polarToCart(startAngle, radius);
  const bgEnd = polarToCart(endAngle, radius);
  const fillEnd = polarToCart(startAngle + sweepAngle, radius);

  const describeArc = (sx: number, sy: number, ex: number, ey: number, large: number) =>
    `M ${sx} ${sy} A ${radius} ${radius} 0 ${large} 1 ${ex} ${ey}`;

  const bgArc = describeArc(bgStart.x, bgStart.y, bgEnd.x, bgEnd.y, 1);
  const fillArc = describeArc(
    bgStart.x,
    bgStart.y,
    fillEnd.x,
    fillEnd.y,
    sweepAngle > 180 ? 1 : 0,
  );

  return (
    <div className="speed-gauge-card" id="speed-gauge">
      <h3>⚡ Ball Speed</h3>

      <div className="gauge-display">
        <svg width="160" height="100" viewBox="0 0 160 100">
          {/* Background arc */}
          <path
            d={bgArc}
            fill="none"
            stroke="hsla(220, 20%, 20%, 0.5)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Fill arc */}
          {ballSpeed > 0 && (
            <path
              d={fillArc}
              fill="none"
              stroke="url(#gaugeGradient)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              style={{ transition: 'all 0.3s ease' }}
            />
          )}
          {/* Gradient definition */}
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(145, 70%, 50%)" />
              <stop offset="50%" stopColor="hsl(65, 95%, 55%)" />
              <stop offset="100%" stopColor="hsl(0, 75%, 55%)" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div className="gauge-value">{ballSpeed.toFixed(0)}</div>
      <div className="gauge-unit">km/h</div>
      <div className="gauge-max">Max: {maxBallSpeed.toFixed(0)} km/h</div>

      {/* Player speed below */}
      <div
        style={{
          marginTop: '16px',
          paddingTop: '12px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span className="angle-name">🏃 Player Speed</span>
        <span className="text-mono" style={{ fontSize: '1rem', fontWeight: 700 }}>
          {playerSpeed.toFixed(1)} <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>km/h</span>
        </span>
      </div>
    </div>
  );
}
