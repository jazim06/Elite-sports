/**
 * Tennia — Elite Biomechanics AI Coach
 * Two-Pass Architecture Version
 */
import { useState, useCallback, useEffect } from 'react';
import { Header } from './components/Header';
import { UploadZone } from './components/UploadZone';
import { VideoCanvas } from './components/VideoCanvas';
import { ThreeDWorld } from './components/ThreeDWorld';
import { BiomechanicsCard } from './components/BiomechanicsCard';
import KinematicSequenceChart from './components/KinematicSequenceChart';
import AICoachPanel from './components/AICoachPanel';
import { useWebSocket } from './hooks/useWebSocket';
import { API_BASE_URL } from './utils/constants';
import type {
  AppView,
  VideoInfo,
  AnalysisData,
  FrameData,
  ProgressPayload,
} from './utils/types';

function App() {
  const [view, setView] = useState<AppView>('upload');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  
  // Two-Pass State
  const [progress, setProgress] = useState(0);
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  
  // Active frame state (updated by VideoCanvas as it plays)
  const [activeFrame, setActiveFrame] = useState<FrameData | null>(null);
  const [seekToFrame, setSeekToFrame] = useState<number | null>(null);

  // ── 1. Fetch Analysis Data when processing finishes ─────────────────
  const fetchAnalysisData = async (videoId: string) => {
    try {
      console.log('Fetching full analysis data...');
      const res = await fetch(`${API_BASE_URL}/api/analysis/${videoId}`);
      if (!res.ok) throw new Error('Failed to fetch analysis data');
      
      const data: AnalysisData = await res.json();
      setAnalysisData(data);
      
      // Also construct the URL to the physical video file
      setVideoUrl(`${API_BASE_URL}/api/video/${videoId}`);
      
    } catch (err) {
      console.error(err);
    }
  };

  // ── 2. WebSocket handler (Progress Only) ─────────────────────────
  const handleProgress = useCallback((data: ProgressPayload) => {
    if (data.progress !== undefined) {
      setProgress(data.progress);
    }
    
    // Switch to playback mode when complete
    if (data.status === 'completed' || data.type === 'complete') {
      if (videoInfo?.video_id) {
        fetchAnalysisData(videoInfo.video_id);
      }
    }
  }, [videoInfo]);

  const { connect, isProcessing } = useWebSocket(handleProgress);

  // ── 3. Upload handler ───────────────────────────────────────────
  const handleUploadComplete = useCallback(
    (info: VideoInfo) => {
      setVideoInfo(info);
      setView('dashboard');
      setProgress(0);
      setAnalysisData(null);
      setVideoUrl(null);
      setActiveFrame(null);
      
      // Start listening for progress on the new video
      connect(info.video_id);
    },
    [connect],
  );

  const handleSeek = useCallback((frame: number) => {
    setSeekToFrame(frame);
    // Clear it out right after so the same frame can be clicked again
    setTimeout(() => setSeekToFrame(null), 100);
  }, []);

  const handleUploadClick = useCallback(() => {
    setView('upload');
  }, []);

  // ── Build Synthetic Data for Sidebar/Charts ─────────────────────
  const syntheticPlayer = activeFrame?.joint_angles
    ? {
        id: 1,
        bbox: [0, 0, 0, 0] as [number, number, number, number],
        keypoints: null,
        joint_angles: activeFrame.joint_angles,
        speed_kmh: 0,
      }
    : null;

  // We need to convert the full analysis frame array into the format the chart expects
  // But we only want to show the current 60 frames (sliding window)
  const getChartData = () => {
    if (!analysisData || !activeFrame) return [];
    
    // Find index of current frame
    const currentIndex = analysisData.frames.findIndex(f => f.frame === activeFrame.frame);
    if (currentIndex === -1) return [];

    // Get window of 60 frames ending at current
    const startIdx = Math.max(0, currentIndex - 60);
    const windowFrames = analysisData.frames.slice(startIdx, currentIndex + 1);

    return windowFrames.map((f) => ({
      frame: f.frame,
      hip_vel: f.angular_velocity?.hip_right_vel || 0,
      shoulder_vel: f.angular_velocity?.shoulder_right_vel || 0,
      elbow_vel: f.angular_velocity?.elbow_right_vel || 0,
    }));
  };

  return (
    <div className="app">
      <Header
        videoInfo={videoInfo}
        isProcessing={isProcessing && !analysisData}
        onUploadClick={handleUploadClick}
      />

      {view === 'upload' ? (
        <UploadZone onUploadComplete={handleUploadComplete} />
      ) : (
        <main className="main-content">
          {/* Side-by-side Video and 3D World */}
          <div className="media-container" style={{ display: 'flex', gap: '16px', minHeight: 0, alignItems: 'flex-start' }}>
            {/* Video */}
            <section className="video-section" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <VideoCanvas
                videoUrl={videoUrl}
                analysisData={analysisData}
                isProcessing={isProcessing}
                progress={progress}
                onFrameChange={setActiveFrame}
                seekToFrame={seekToFrame}
              />
            </section>
            {/* 3D World */}
            <section className="three-d-section" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <ThreeDWorld activeFrame={activeFrame} />
            </section>
          </div>

          {/* Sidebar: Biomechanics + AI Notes */}
          <aside className="analytics-sidebar">
            <BiomechanicsCard player={syntheticPlayer} />
            <AICoachPanel 
              notes={analysisData?.coaching_notes || []} 
              isProcessing={isProcessing && !analysisData} 
              onNoteClick={handleSeek} 
            />
          </aside>

          {/* Bottom: Kinematic Sequence */}
          <section className="bottom-panels" style={{ gridTemplateColumns: '1fr' }}>
            <KinematicSequenceChart data={getChartData()} />
          </section>
        </main>
      )}
    </div>
  );
}

export default App;
