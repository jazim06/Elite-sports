/**
 * Tennia — Elite Biomechanics AI Coach
 * Focus: Video + 3D Skeleton + Joint Angles + AI Coaching Notes + Kinematic Chart
 */
import { useState, useCallback } from 'react';
import { Header } from './components/Header';
import { UploadZone } from './components/UploadZone';
import { VideoCanvas } from './components/VideoCanvas';
import { BiomechanicsCard } from './components/BiomechanicsCard';
import KinematicSequenceChart from './components/KinematicSequenceChart';
import AICoachPanel from './components/AICoachPanel';
import type { CoachingNote } from './components/AICoachPanel';
import { useWebSocket } from './hooks/useWebSocket';
import type {
  AppView,
  VideoInfo,
  FramePayload,
  PlaybackState,
} from './utils/types';

function App() {
  const [view, setView] = useState<AppView>('upload');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [frameData, setFrameData] = useState<string | null>(null);

  // Biomechanics
  const [jointAngles3d, setJointAngles3d] = useState<Record<string, number>>({});
  const [kinematicData, setKinematicData] = useState<
    Array<{ frame: number; hip_vel: number; shoulder_vel: number; elbow_vel: number }>
  >([]);

  // AI Coaching Notes — accumulated list
  const [coachingNotes, setCoachingNotes] = useState<CoachingNote[]>([]);

  // Playback
  const [playback, setPlayback] = useState<PlaybackState>({
    playing: true,
    speed: 1,
    currentFrame: 0,
    totalFrames: 0,
    fps: 30,
  });

  // ── WebSocket message handler ───────────────────────
  const handleMessage = useCallback((data: FramePayload) => {
    if (data.type === 'metadata') {
      setPlayback((prev) => ({
        ...prev,
        totalFrames: data.total_frames ?? 0,
        fps: data.fps ?? 30,
      }));
      return;
    }

    if (data.type === 'frame') {
      if (data.frame_data) {
        setFrameData(data.frame_data);
      }

      if (data.player) {
        const player = data.player;

        if (player.joint_angles_3d) {
          setJointAngles3d(player.joint_angles_3d);
        }

        if (player.angular_velocity) {
          setKinematicData((prev) => {
            const newData = [
              ...prev,
              {
                frame: data.frame_number || 0,
                hip_vel: player.angular_velocity?.hip_right_vel || 0,
                shoulder_vel: player.angular_velocity?.shoulder_right_vel || 0,
                elbow_vel: player.angular_velocity?.elbow_right_vel || 0,
              },
            ];
            return newData.slice(-60);
          });
        }
      }

      // Append NEW coaching notes (backend sends only new ones per frame)
      if (data.new_notes && data.new_notes.length > 0) {
        setCoachingNotes((prev) => [...prev, ...data.new_notes!]);
      }

      // Update playback progress
      setPlayback((prev) => ({
        ...prev,
        currentFrame: data.frame_number ?? prev.currentFrame,
        totalFrames: data.total_frames ?? prev.totalFrames,
      }));
    }

    if (data.type === 'complete') {
      setPlayback((prev) => ({ ...prev, playing: false }));
      // Replace with full notes list if provided
      if (data.all_notes && data.all_notes.length > 0) {
        setCoachingNotes(data.all_notes);
      }
    }
  }, []);

  const { connect, sendMessage, isProcessing } = useWebSocket(handleMessage);

  const handleUploadComplete = useCallback(
    (info: VideoInfo) => {
      setVideoInfo(info);
      setView('dashboard');
      setFrameData(null);
      setJointAngles3d({});
      setKinematicData([]);
      setCoachingNotes([]);
      setPlayback({
        playing: true,
        speed: 1,
        currentFrame: 0,
        totalFrames: 0,
        fps: 30,
      });
      connect(info.video_id);
    },
    [connect],
  );

  const handlePlayPause = useCallback(() => {
    setPlayback((prev) => {
      const newPlaying = !prev.playing;
      sendMessage({ action: newPlaying ? 'play' : 'pause' });
      return { ...prev, playing: newPlaying };
    });
  }, [sendMessage]);

  const handleSpeedChange = useCallback(
    (speed: number) => {
      setPlayback((prev) => ({ ...prev, speed }));
      sendMessage({ action: 'speed', value: speed });
    },
    [sendMessage],
  );

  const handleSeek = useCallback(
    (frame: number) => {
      sendMessage({ action: 'seek', frame });
      setPlayback((prev) => ({ ...prev, currentFrame: frame }));
    },
    [sendMessage],
  );

  const handleUploadClick = useCallback(() => {
    setView('upload');
  }, []);

  // Build synthetic player for BiomechanicsCard
  const syntheticPlayer = Object.keys(jointAngles3d).length > 0
    ? {
        id: 1,
        bbox: [0, 0, 0, 0] as [number, number, number, number],
        keypoints: null,
        joint_angles: jointAngles3d,
        speed_kmh: 0,
      }
    : null;

  return (
    <div className="app">
      <Header
        videoInfo={videoInfo}
        isProcessing={isProcessing}
        onUploadClick={handleUploadClick}
      />

      {view === 'upload' ? (
        <UploadZone onUploadComplete={handleUploadComplete} />
      ) : (
        <main className="main-content">
          {/* Video */}
          <section className="video-section">
            <VideoCanvas
              frameData={frameData}
              playback={playback}
              onPlayPause={handlePlayPause}
              onSpeedChange={handleSpeedChange}
              onSeek={handleSeek}
              isProcessing={isProcessing && !frameData}
            />
          </section>

          {/* Sidebar: Biomechanics + AI Notes */}
          <aside className="analytics-sidebar">
            <BiomechanicsCard player={syntheticPlayer} />
            <AICoachPanel notes={coachingNotes} isProcessing={isProcessing} onNoteClick={handleSeek} />
          </aside>

          {/* Bottom: Kinematic Sequence */}
          <section className="bottom-panels" style={{ gridTemplateColumns: '1fr' }}>
            <KinematicSequenceChart data={kinematicData} />
          </section>
        </main>
      )}
    </div>
  );
}

export default App;
