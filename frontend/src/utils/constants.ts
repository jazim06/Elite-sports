/**
 * Tennia — Application constants
 */

export const API_BASE_URL = 'http://localhost:8000';
export const WS_BASE_URL = 'ws://localhost:8000';

export const SHOT_COLORS: Record<string, string> = {
  forehand: 'hsl(145, 70%, 50%)',
  backhand: 'hsl(25, 90%, 58%)',
  serve: 'hsl(185, 85%, 55%)',
  volley: 'hsl(45, 95%, 55%)',
  unknown: 'hsl(220, 12%, 45%)',
};

export const PLAYBACK_SPEEDS = [0.25, 0.5, 1, 2, 4];

// Tennis court dimensions in meters (for SVG drawing ratios)
export const COURT = {
  length: 23.77,
  width: 10.97,
  singlesWidth: 8.23,
  serviceLineDist: 6.40,
  netPosition: 23.77 / 2,
};

// Joint angle display config
export const ANGLE_CONFIG: Record<string, { label: string; icon: string }> = {
  knee_left: { label: 'L Knee', icon: '🦵' },
  knee_right: { label: 'R Knee', icon: '🦵' },
  elbow_left: { label: 'L Elbow', icon: '💪' },
  elbow_right: { label: 'R Elbow', icon: '💪' },
  shoulder_left: { label: 'L Shoulder', icon: '🦴' },
  shoulder_right: { label: 'R Shoulder', icon: '🦴' },
  hip_left: { label: 'L Hip', icon: '🦴' },
  hip_right: { label: 'R Hip', icon: '🦴' },
};
