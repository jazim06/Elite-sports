/**
 * VideoCanvas — Two-Pass Architecture
 * 
 * Plays the native HTML5 video file and draws the skeleton overlay on a
 * transparent canvas synced to the video's current time.
 */
import { useRef, useEffect, useCallback, useState } from 'react';
import { PLAYBACK_SPEEDS } from '../utils/constants';
import type { AnalysisData, FrameData } from '../utils/types';

interface VideoCanvasProps {
  videoUrl: string | null;
  analysisData: AnalysisData | null;
  isProcessing: boolean;
  progress: number;
  onFrameChange: (frameData: FrameData | null) => void;
  seekToFrame?: number | null; // Trigger seek from parent (e.g. clicking a note)
}

// COCO 17-keypoint connections for drawing the skeleton (YOLOv8-Pose)
const POSE_CONNECTIONS = [
  // Head
  ['NOSE', 'LEFT_EYE'],
  ['NOSE', 'RIGHT_EYE'],
  ['LEFT_EYE', 'LEFT_EAR'],
  ['RIGHT_EYE', 'RIGHT_EAR'],
  // Torso
  ['LEFT_SHOULDER', 'RIGHT_SHOULDER'],
  ['LEFT_SHOULDER', 'LEFT_HIP'],
  ['RIGHT_SHOULDER', 'RIGHT_HIP'],
  ['LEFT_HIP', 'RIGHT_HIP'],
  // Right arm
  ['RIGHT_SHOULDER', 'RIGHT_ELBOW'],
  ['RIGHT_ELBOW', 'RIGHT_WRIST'],
  // Left arm
  ['LEFT_SHOULDER', 'LEFT_ELBOW'],
  ['LEFT_ELBOW', 'LEFT_WRIST'],
  // Right leg
  ['RIGHT_HIP', 'RIGHT_KNEE'],
  ['RIGHT_KNEE', 'RIGHT_ANKLE'],
  // Left leg
  ['LEFT_HIP', 'LEFT_KNEE'],
  ['LEFT_KNEE', 'LEFT_ANKLE'],
];

export function VideoCanvas({
  videoUrl,
  analysisData,
  isProcessing,
  progress,
  onFrameChange,
  seekToFrame,
}: VideoCanvasProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>();
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);

  // Sync parent seek request
  useEffect(() => {
    if (seekToFrame != null && analysisData && videoRef.current) {
      const timeToSeek = seekToFrame / analysisData.metadata.fps;
      videoRef.current.currentTime = timeToSeek;
      if (!isPlaying) {
        // Force a re-render/re-draw even if paused
        setCurrentTime(timeToSeek);
      }
    }
  }, [seekToFrame, analysisData]); // Don't include isPlaying as dependency

  // Binary search: find the two frames bounding `targetTime` for perfect interpolation
  const getBoundingFrames = useCallback(
    (frames: FrameData[], targetTime: number): [FrameData, FrameData | null] => {
      if (frames.length === 0) return [frames[0], null]; // Should not happen
      if (frames.length === 1) return [frames[0], null];
      if (targetTime <= frames[0].timestamp) return [frames[0], frames[1]];
      if (targetTime >= frames[frames.length - 1].timestamp) return [frames[frames.length - 1], null];

      let lo = 0;
      let hi = frames.length - 1;

      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (frames[mid].timestamp < targetTime) {
          lo = mid + 1;
        } else {
          hi = mid;
        }
      }

      // lo is the first frame with timestamp >= targetTime.
      if (lo > 0) {
        return [frames[lo - 1], frames[lo]];
      }
      return [frames[0], frames[1]];
    },
    [],
  );

  // The main render loop for the canvas overlay
  const drawOverlay = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !analysisData) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Match canvas size to video display size
    if (canvas.width !== video.clientWidth || canvas.height !== video.clientHeight) {
      canvas.width = video.clientWidth;
      canvas.height = video.clientHeight;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Find bounding frames for the current video time
    const currentVideoTime = video.currentTime;
    setCurrentTime(currentVideoTime);

    const frames = analysisData.frames;
    const [frameA, frameB] = getBoundingFrames(frames, currentVideoTime);
    if (!frameA) return;

    // Report current frame data to parent
    onFrameChange(frameA);

    // Determine the actual drawn dimensions of the video inside the canvas (object-fit: contain)
    const videoRatio = video.videoWidth / video.videoHeight;
    const containerRatio = canvas.width / canvas.height;

    let drawWidth: number, drawHeight: number, offsetX = 0, offsetY = 0;
    if (containerRatio > videoRatio) {
      // Pillarboxing (black bars on left/right)
      drawHeight = canvas.height;
      drawWidth = drawHeight * videoRatio;
      offsetX = (canvas.width - drawWidth) / 2;
    } else {
      // Letterboxing (black bars on top/bottom)
      drawWidth = canvas.width;
      drawHeight = drawWidth / videoRatio;
      offsetY = (canvas.height - drawHeight) / 2;
    }

    // Helper to get interpolated landmarks between bounding frames
    const getLandmarks = (): Record<string, { x: number; y: number; v: number }> | null => {
      if (!frameA.landmarks_2d) return null;

      // If we have a next frame, interpolate based on exact time difference
      if (frameB?.landmarks_2d && frameB.timestamp > frameA.timestamp) {
        const timeDiff = frameB.timestamp - frameA.timestamp;
        // Clamp t between 0 and 1 just in case
        const t = Math.max(0, Math.min(1, (currentVideoTime - frameA.timestamp) / timeDiff));
        
        if (t > 0 && t < 1) {
          const result: Record<string, { x: number; y: number; v: number }> = {};
          for (const name of Object.keys(frameA.landmarks_2d)) {
            const a = frameA.landmarks_2d[name] as { x: number; y: number; v?: number };
            const b = frameB.landmarks_2d[name] as { x: number; y: number; v?: number } | undefined;
            if (b) {
              result[name] = {
                x: a.x + (b.x - a.x) * t,
                y: a.y + (b.y - a.y) * t,
                v: Math.min(a.v ?? 1, b.v ?? 1),
              };
            } else {
              result[name] = { x: a.x, y: a.y, v: a.v ?? 1 };
            }
          }
          return result;
        }
      }

      // No interpolation needed or frameB missing — use frameA directly
      const result: Record<string, { x: number; y: number; v: number }> = {};
      for (const [name, pt] of Object.entries(frameA.landmarks_2d)) {
        const p = pt as { x: number; y: number; v?: number };
        result[name] = { x: p.x, y: p.y, v: p.v ?? 1 };
      }
      return result;
    };

    const landmarks = getLandmarks();

    // Draw Skeleton
    if (landmarks) {
      const VISIBILITY_THRESHOLD = 0.5;

      // Coords are normalized 0.0–1.0, map directly to the video draw area
      const mapCoords = (pt: { x: number; y: number }) => ({
        x: offsetX + pt.x * drawWidth,
        y: offsetY + pt.y * drawHeight,
      });

      // Draw connections (bones)
      ctx.lineWidth = 3;

      for (const [p1Name, p2Name] of POSE_CONNECTIONS) {
        const l1 = landmarks[p1Name];
        const l2 = landmarks[p2Name];
        if (l1 && l2 && l1.v >= VISIBILITY_THRESHOLD && l2.v >= VISIBILITY_THRESHOLD) {
          const pt1 = mapCoords(l1);
          const pt2 = mapCoords(l2);

          // Subtle gradient per bone for visual quality
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)';
          ctx.beginPath();
          ctx.moveTo(pt1.x, pt1.y);
          ctx.lineTo(pt2.x, pt2.y);
          ctx.stroke();
        }
      }

      // Draw keypoints (joints)
      for (const [name, lm] of Object.entries(landmarks)) {
        if (lm.v < VISIBILITY_THRESHOLD) continue;

        const mapped = mapCoords(lm);
        ctx.beginPath();
        ctx.arc(mapped.x, mapped.y, 5, 0, 2 * Math.PI);

        // Color code right vs left
        if (name.includes('RIGHT')) {
          ctx.fillStyle = '#ff7b00'; // Orange for right side
        } else if (name.includes('LEFT')) {
          ctx.fillStyle = '#00a8ff'; // Blue for left side
        } else {
          ctx.fillStyle = '#ffffff'; // White for center (nose, etc)
        }

        ctx.fill();
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    if (isPlaying) {
      rafRef.current = requestAnimationFrame(drawOverlay);
    }
  }, [analysisData, isPlaying, onFrameChange, getBoundingFrames]);

  // Start/stop render loop based on play state
  useEffect(() => {
    if (isPlaying) {
      rafRef.current = requestAnimationFrame(drawOverlay);
    } else {
      // Draw one last time to ensure it's up to date when paused
      drawOverlay();
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    }
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [isPlaying, drawOverlay]);

  // Video event handlers
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
    } else {
      videoRef.current.pause();
    }
  };

  const handleSpeedChange = (speed: number) => {
    if (!videoRef.current) return;
    videoRef.current.playbackRate = speed;
    setPlaybackSpeed(speed);
  };

  const formatTime = (secs: number) => {
    if (!secs || secs < 0) return '0:00.0';
    const mins = Math.floor(secs / 60);
    const remainder = secs % 60;
    return `${mins}:${remainder.toFixed(1).padStart(4, '0')}`;
  };

  return (
    <div className="video-canvas-container" id="video-canvas" style={{ position: 'relative' }}>
      
      {/* PROCESSING STATE */}
      {isProcessing && !analysisData && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', background: 'var(--bg-surface)',
          zIndex: 10
        }}>
          <div className="spinner" style={{ margin: '0 auto 16px' }} />
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Analyzing biomechanics...
          </p>
          {/* Progress bar */}
          <div style={{ width: '60%', height: '8px', background: 'var(--bg-card)', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${progress}%`, height: '100%', background: 'var(--accent-primary)', transition: 'width 0.3s ease' }} />
          </div>
          <p style={{ marginTop: '8px', fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>{progress}%</p>
        </div>
      )}

      {/* IDLE STATE */}
      {!isProcessing && !videoUrl && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: 'var(--text-tertiary)'
        }}>
          <p>Upload a video to begin analysis</p>
        </div>
      )}

      {/* PLAYBACK STATE */}
      {videoUrl && (
        <>
          {/* Native HTML5 Video Player */}
          <video
            ref={videoRef}
            src={videoUrl}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
            onSeeked={() => drawOverlay()} // Redraw when user scrubs native controls
            controls={false} // We provide custom controls below
            playsInline
          />

          {/* Transparent Canvas Overlay for Skeleton */}
          <canvas
            ref={canvasRef}
            style={{
              position: 'absolute',
              top: 0, left: 0, width: '100%', height: '100%',
              pointerEvents: 'none', // Let clicks pass through to video
              objectFit: 'contain'
            }}
          />

          {/* Custom Controls UI (matching previous look) */}
          <div className="video-controls">
            <button
              className="btn btn-icon"
              onClick={togglePlay}
              title={isPlaying ? 'Pause' : 'Play'}
              style={{ background: 'transparent', border: 'none' }}
            >
              {isPlaying ? '⏸' : '▶️'}
            </button>

            {/* Custom progress bar instead of native one for styling */}
            <div
              className="video-progress"
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const pct = (e.clientX - rect.left) / rect.width;
                if (videoRef.current && analysisData) {
                  videoRef.current.currentTime = pct * analysisData.metadata.duration_sec;
                }
              }}
            >
              <div
                className="video-progress-fill"
                style={{ 
                  width: `${analysisData ? (currentTime / analysisData.metadata.duration_sec) * 100 : 0}%` 
                }}
              />
            </div>

            <span className="text-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', minWidth: '110px', textAlign: 'right', display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {formatTime(currentTime)} / {formatTime(analysisData?.metadata.duration_sec || 0)}
              </span>
              <span style={{ fontSize: '0.65rem', opacity: 0.6 }}>
                Fr {Math.round(currentTime * (analysisData?.metadata.fps || 30))}
              </span>
            </span>

            <div className="speed-selector">
              {PLAYBACK_SPEEDS.map((s) => (
                <button
                  key={s}
                  className={`speed-btn ${playbackSpeed === s ? 'active' : ''}`}
                  onClick={() => handleSpeedChange(s)}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
