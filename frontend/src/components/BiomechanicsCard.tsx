/**
 * BiomechanicsCard — Displays joint angles with visual bars and color-coded status.
 */
import type { PlayerData } from '../utils/types';
import { ANGLE_CONFIG } from '../utils/constants';

interface BiomechanicsCardProps {
  player: PlayerData | null;
}

function getAngleStatus(angle: number): { class: string; label: string } {
  if (angle >= 120) return { class: 'optimal', label: 'Optimal' };
  if (angle >= 90) return { class: 'caution', label: 'Caution' };
  return { class: 'risk', label: 'Risk' };
}

export function BiomechanicsCard({ player }: BiomechanicsCardProps) {
  const angles = player?.joint_angles ?? {};
  const trunkLean = player?.trunk_lean;

  return (
    <div className="bio-card animate-fade-in" id="biomechanics-panel">
      <h3>🦴 Biomechanics</h3>

      {Object.entries(ANGLE_CONFIG).map(([key, config]) => {
        const value = angles[key];
        if (value === undefined) return null;

        const status = getAngleStatus(value);
        const barWidth = Math.min((value / 180) * 100, 100);

        return (
          <div className="angle-row" key={key}>
            <span className="angle-name">
              {config.icon} {config.label}
            </span>
            <div className="angle-bar-container">
              <div
                className={`angle-bar ${status.class}`}
                style={{ width: `${barWidth}%` }}
              />
            </div>
            <span className="angle-value">{value.toFixed(1)}°</span>
          </div>
        );
      })}

      {trunkLean !== null && trunkLean !== undefined && (
        <div className="angle-row" style={{ marginTop: '8px' }}>
          <span className="angle-name">🏃 Trunk Lean</span>
          <div className="angle-bar-container">
            <div
              className={`angle-bar ${trunkLean < 15 ? 'optimal' : trunkLean < 30 ? 'caution' : 'risk'}`}
              style={{ width: `${Math.min((trunkLean / 45) * 100, 100)}%` }}
            />
          </div>
          <span className="angle-value">{trunkLean}°</span>
        </div>
      )}

      {/* Symmetry score */}
      {player?.symmetry?.overall !== undefined && (
        <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="angle-name">⚖️ Body Symmetry</span>
            <span
              className="angle-value"
              style={{
                color:
                  player.symmetry.overall < 10
                    ? 'var(--color-success)'
                    : player.symmetry.overall < 20
                      ? 'var(--color-warning)'
                      : 'var(--color-danger)',
              }}
            >
              {player.symmetry.overall}° diff
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
