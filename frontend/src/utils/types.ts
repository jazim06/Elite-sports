/**
 * Tennia — TypeScript interfaces for the analytics pipeline
 */

// ── Player Data ─────────────────────────────────────────────
export interface PlayerData {
  id: number;
  bbox: [number, number, number, number]; // x1, y1, x2, y2
  confidence?: number;
  keypoints: number[][] | null; // (17, 3) — [x, y, conf]
  joint_angles: Record<string, number>;
  angular_velocity?: Record<string, number>;
  trunk_lean?: number | null;
  symmetry?: Record<string, number>;
  speed_kmh: number;
  max_speed_kmh?: number;
  acceleration_ms2?: number;
  distance_m?: number;
  court_position?: [number, number] | null;
  position_px?: [number, number] | null;
  zone?: string;
  shot?: ShotData;
}

// ── Ball Data ───────────────────────────────────────────────
export interface BallData {
  position: [number, number] | null;
  speed_kmh: number;
  trajectory: [number, number][];
  detected: boolean;
}

// ── Shot Data ───────────────────────────────────────────────
export interface ShotData {
  type: 'forehand' | 'backhand' | 'serve' | 'volley' | 'unknown';
  confidence: number;
  is_new_shot?: boolean;
  counts?: Record<string, number>;
}

// ── Metrics ─────────────────────────────────────────────────
export interface SessionMetrics {
  duration_sec: number;
  total_frames: number;
  total_shots: number;
  shot_counts: Record<string, number>;
  shots_per_hour: number;
  avg_ball_speed_kmh: number;
  max_ball_speed_kmh: number;
  avg_rally_length: number;
  longest_rally: number;
  player_distances_m: Record<number, number>;
}

// ── Frame Payload (WebSocket message) ───────────────────
export interface FramePayload {
  type: 'frame' | 'metadata' | 'complete' | 'error';
  frame_number?: number;
  total_frames?: number;
  frame_data?: string; // base64 JPEG
  player?: {
    landmarks_3d?: Record<string, { x: number; y: number; z: number; visibility: number }>;
    landmarks_2d?: Record<string, { x: number; y: number }>;
    joint_angles_3d?: Record<string, number>;
    angular_velocity?: Record<string, number>;
  } | null;
  // AI Coaching Notes
  new_notes?: Array<{
    timestamp: string;
    frame: number;
    joint: string;
    severity: 'warning' | 'error' | 'good';
    flaw: string;
    angle: number;
    optimal_range: string;
    impact: string;
    drill: string;
  }>;
  all_notes?: Array<{
    timestamp: string;
    frame: number;
    joint: string;
    severity: 'warning' | 'error' | 'good';
    flaw: string;
    angle: number;
    optimal_range: string;
    impact: string;
    drill: string;
  }>;
  total_notes?: number;
  // Metadata fields
  fps?: number;
  width?: number;
  height?: number;
  // Error
  error?: string;
}

// ── Video Info ───────────────────────────────────────────────
export interface VideoInfo {
  video_id: string;
  filename: string;
  status: 'uploaded' | 'processing' | 'completed' | 'error';
}

// ── App State ───────────────────────────────────────────────
export type AppView = 'upload' | 'dashboard';

export interface PlaybackState {
  playing: boolean;
  speed: number;
  currentFrame: number;
  totalFrames: number;
  fps: number;
}
