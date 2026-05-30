/**
 * VideoCanvas — Displays annotated video frames streamed from the backend.
 * Includes playback controls (play/pause, speed, progress bar).
 */
import { useRef, useEffect, useCallback } from 'react';
import { PLAYBACK_SPEEDS } from '../utils/constants';
import type { PlaybackState } from '../utils/types';

interface VideoCanvasProps {
  frameData: string | null; // base64 JPEG
  playback: PlaybackState;
  onPlayPause: () => void;
  onSpeedChange: (speed: number) => void;
  onSeek: (frame: number) => void;
  isProcessing: boolean;
}

export function VideoCanvas({
  frameData,
  playback,
  onPlayPause,
  onSpeedChange,
  onSeek,
  isProcessing,
}: VideoCanvasProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  // Update image when new frame arrives
  useEffect(() => {
    if (frameData && imgRef.current) {
      imgRef.current.src = `data:image/jpeg;base64,${frameData}`;
    }
  }, [frameData]);

  // Progress bar click handler
  const handleProgressClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!progressRef.current || playback.totalFrames === 0) return;
      const rect = progressRef.current.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      const frame = Math.round(pct * playback.totalFrames);
      onSeek(frame);
    },
    [playback.totalFrames, onSeek],
  );

  const progressPct =
    playback.totalFrames > 0
      ? (playback.currentFrame / playback.totalFrames) * 100
      : 0;

  const formatTime = (frame: number, fps: number) => {
    const validFps = fps && fps > 0 ? fps : 30;
    const totalSecs = frame / validFps;
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins}:${secs.toFixed(1).padStart(4, '0')}`;
  };

  return (
    <div className="video-canvas-container" id="video-canvas">
      {/* Video frame */}
      {frameData ? (
        <img
          ref={imgRef}
          alt="Analyzed tennis frame"
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
        />
      ) : (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--text-tertiary)',
            fontSize: '1.1rem',
          }}
        >
          {isProcessing ? (
            <div style={{ textAlign: 'center' }}>
              <div className="spinner" style={{ margin: '0 auto 16px' }} />
              <p>Initializing CV pipeline...</p>
            </div>
          ) : (
            <p>Upload a video to begin analysis</p>
          )}
        </div>
      )}

      {/* Playback controls overlay */}
      {frameData && (
        <div className="video-controls">
          {/* Play/Pause */}
          <button
            className="btn btn-icon"
            onClick={onPlayPause}
            title={playback.playing ? 'Pause' : 'Play'}
            id="play-pause-btn"
            style={{ background: 'transparent', border: 'none' }}
          >
            {playback.playing ? '⏸' : '▶️'}
          </button>

          {/* Progress bar */}
          <div
            className="video-progress"
            ref={progressRef}
            onClick={handleProgressClick}
            id="progress-bar"
          >
            <div
              className="video-progress-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Frame counter & Timestamp */}
          <span
            className="text-mono"
            style={{
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              minWidth: '110px',
              textAlign: 'right',
              display: 'flex',
              flexDirection: 'column',
              lineHeight: 1.2,
            }}
          >
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              {formatTime(playback.currentFrame, playback.fps)} / {formatTime(playback.totalFrames, playback.fps)}
            </span>
            <span style={{ fontSize: '0.65rem', opacity: 0.6 }}>
              Fr {playback.currentFrame} / {playback.totalFrames}
            </span>
          </span>

          {/* Speed selector */}
          <div className="speed-selector">
            {PLAYBACK_SPEEDS.map((s) => (
              <button
                key={s}
                className={`speed-btn ${playback.speed === s ? 'active' : ''}`}
                onClick={() => onSpeedChange(s)}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
