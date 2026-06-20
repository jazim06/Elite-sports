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

// ── Biomechanics Engine Types ─────────────────────────────
export interface Landmark {
  x: number;
  y: number;
  z?: number;
  visibility?: number;
}

// ── Two-Pass Architecture Types ───────────────────────────
export interface SegmentVelocity {
  pelvis: number;  // deg/sec — rotation speed of pelvis line in transverse plane
  trunk:  number;  // deg/sec — rotation speed of shoulder line in transverse plane
  arm:    number;  // deg/sec — angular speed of upper-arm unit vector
  hand:   number;  // deg/sec — angular speed of forearm unit vector
}

export interface KinematicSequence {
  detected: boolean;
  dominant_side?: 'RIGHT' | 'LEFT';
  contact_frame?: number;
  contact_time?: number;
  phases?: {
    windup:         [number, number];
    acceleration:   [number, number];
    contact:        number;
    follow_through: [number, number];
  };
  peaks?: Record<'pelvis' | 'trunk' | 'arm' | 'hand', {
    frame: number;
    time: number;
    speed_deg_per_sec: number;
  }>;
  order?: string[];
  is_proximal_to_distal?: boolean;
  sequence_score?: number;
  hip_shoulder_separation?: {
    peak_deg: number;
    peak_time: number;
  };
}

export interface FrameData {
  frame: number;
  timestamp: number;
  landmarks_2d: Record<string, { x: number; y: number; v?: number }>;
  landmarks_3d?: Record<string, { x: number; y: number; z: number; v?: number }>;
  joint_angles: Record<string, number> | null;
  angular_velocity: Record<string, number> | null;  // deg/sec; keys suffixed _vel
  segment_velocity?: SegmentVelocity | null;
}

export interface AnalysisData {
  video_id: string;
  metadata: {
    fps: number;
    total_frames: number;
    processed_frames: number;
    width: number;
    height: number;
    duration_sec: number;
    processing_time_sec: number;
  };
  frames: FrameData[];
  coaching_notes: CoachingNote[];
  kinematic_sequence?: KinematicSequence;
}

export interface CoachingNote {
  timestamp: string;
  frame: number;
  joint: string;
  severity: 'warning' | 'error' | 'good';
  flaw: string;
  actual_angle: number;
  optimal_range: [number, number];
  impact: string;
  drill: string;
}

// ── WebSocket Payload (Progress Only) ───────────────────
export interface ProgressPayload {
  type: 'progress' | 'complete' | 'error';
  progress?: number;
  current_frame?: number;
  total_frames?: number;
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
