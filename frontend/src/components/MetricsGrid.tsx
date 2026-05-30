/**
 * MetricsGrid — Grid of KPI cards showing session statistics.
 */
import type { SessionMetrics } from '../utils/types';

interface MetricsGridProps {
  metrics: SessionMetrics | null;
}

interface MetricItem {
  label: string;
  value: string;
  icon: string;
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  const items: MetricItem[] = [
    {
      label: 'Total Shots',
      value: metrics?.total_shots?.toString() ?? '0',
      icon: '🎾',
    },
    {
      label: 'Avg Ball Speed',
      value: `${metrics?.avg_ball_speed_kmh?.toFixed(0) ?? '0'} km/h`,
      icon: '⚡',
    },
    {
      label: 'Max Ball Speed',
      value: `${metrics?.max_ball_speed_kmh?.toFixed(0) ?? '0'} km/h`,
      icon: '🔥',
    },
    {
      label: 'Distance Covered',
      value: formatDistance(metrics),
      icon: '🏃',
    },
    {
      label: 'Avg Rally',
      value: `${metrics?.avg_rally_length?.toFixed(1) ?? '0'} shots`,
      icon: '🔄',
    },
    {
      label: 'Longest Rally',
      value: `${metrics?.longest_rally ?? 0} shots`,
      icon: '🏆',
    },
    {
      label: 'Shots / Hour',
      value: metrics?.shots_per_hour?.toString() ?? '0',
      icon: '⏱️',
    },
    {
      label: 'Duration',
      value: formatDuration(metrics?.duration_sec ?? 0),
      icon: '🕐',
    },
  ];

  return (
    <div className="metrics-grid animate-slide-up" id="metrics-grid">
      {items.map((item) => (
        <div className="metric-card" key={item.label}>
          <span className="metric-label">
            {item.icon} {item.label}
          </span>
          <span className="metric-value">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

function formatDistance(metrics: SessionMetrics | null): string {
  if (!metrics?.player_distances_m) return '0 m';
  const distances = Object.values(metrics.player_distances_m);
  if (distances.length === 0) return '0 m';
  const max = Math.max(...distances);
  if (max >= 1000) return `${(max / 1000).toFixed(1)} km`;
  return `${max.toFixed(0)} m`;
}

function formatDuration(sec: number): string {
  if (sec <= 0) return '0:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
