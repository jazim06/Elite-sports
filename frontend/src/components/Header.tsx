/**
 * Header — App header with logo and session controls
 */
import type { VideoInfo } from '../utils/types';

interface HeaderProps {
  videoInfo: VideoInfo | null;
  isProcessing: boolean;
  onUploadClick: () => void;
}

export function Header({ videoInfo, isProcessing, onUploadClick }: HeaderProps) {
  return (
    <header className="header" id="app-header">
      <div className="header-logo">
        <span className="logo-icon">🎾</span>
        <h1>Tennia</h1>
        {videoInfo && (
          <span className="badge badge-accent">{videoInfo.filename}</span>
        )}
        {isProcessing && <span className="badge badge-live">Processing</span>}
      </div>

      <div className="header-actions">
        <button className="btn btn-primary" onClick={onUploadClick} id="upload-btn">
          📁 Upload Video
        </button>
      </div>
    </header>
  );
}
