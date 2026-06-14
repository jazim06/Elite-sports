/**
 * UploadZone — Drag & drop video upload with progress indicator
 */
import { useState, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../utils/constants';
import type { VideoInfo } from '../utils/types';

interface UploadZoneProps {
  onUploadComplete: (videoInfo: VideoInfo) => void;
}

export function UploadZone({ onUploadComplete }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const handleFile = useCallback(
    async (file: File) => {
      if (file.size === 0) {
        setError('File is empty or corrupted. If dragging from Apple Photos, try exporting it to your Desktop first.');
        return;
      }

      setError(null);
      setUploading(true);
      setProgress(0);

      const formData = new FormData();
      formData.append('file', file);

      try {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            setProgress(Math.round((e.loaded / e.total) * 100));
          }
        });

        const response = await new Promise<{ video_id: string; filename: string }>(
          (resolve, reject) => {
            xhr.onload = () => {
              if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
              } else {
                reject(new Error(JSON.parse(xhr.responseText).detail || 'Upload failed'));
              }
            };
            xhr.onerror = () => reject(new Error('Network error'));
            xhr.open('POST', `${API_BASE_URL}/api/upload`);
            xhr.send(formData);
          },
        );

        onUploadComplete({
          video_id: response.video_id,
          filename: response.filename,
          status: 'uploaded',
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [onUploadComplete],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleClick = () => fileInputRef.current?.click();

  return (
    <div className="upload-zone-overlay">
      <div
        className={`upload-zone animate-fade-in ${isDragOver ? 'dragover' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={handleClick}
        id="upload-zone"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".mp4,.mov,.avi,.mkv,.webm"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
          id="file-input"
        />

        {!uploading ? (
          <>
            <div className="upload-icon">🎾</div>
            <h2>Drop your tennis video here</h2>
            <p>
              Upload an iPhone recording (.mp4, .mov) to start analyzing
              <br />
              player movement, biomechanics, and ball trajectory
            </p>
            <button className="btn btn-primary" type="button">
              Choose File
            </button>
          </>
        ) : (
          <>
            <div className="spinner" />
            <h2>Uploading...</h2>
            <div className="upload-progress-bar">
              <div
                className="upload-progress-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-secondary">{progress}%</p>
          </>
        )}

        {error && (
          <p style={{ color: 'var(--color-danger)', fontSize: '0.85rem' }}>
            ❌ {error}
          </p>
        )}
      </div>
    </div>
  );
}
