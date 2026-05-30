import React, { useRef, useEffect } from 'react';
import { Sparkles, AlertTriangle, AlertCircle, Clock, Dumbbell } from 'lucide-react';

export interface CoachingNote {
  timestamp: string;
  frame: number;
  joint: string;
  severity: 'warning' | 'error' | 'good';
  flaw: string;
  angle: number;
  optimal_range: string;
  impact: string;
  drill: string;
}

interface AICoachPanelProps {
  notes: CoachingNote[];
  isProcessing: boolean;
  onNoteClick?: (frame: number) => void;
}

const severityConfig = {
  error: {
    border: 'border-red-500/30',
    bg: 'bg-red-500/5',
    hoverBg: 'hover:bg-red-500/10',
    icon: <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />,
    badge: 'bg-red-500/20 text-red-300',
    label: 'Issue',
  },
  warning: {
    border: 'border-amber-500/30',
    bg: 'bg-amber-500/5',
    hoverBg: 'hover:bg-amber-500/10',
    icon: <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />,
    badge: 'bg-amber-500/20 text-amber-300',
    label: 'Caution',
  },
  good: {
    border: 'border-emerald-500/30',
    bg: 'bg-emerald-500/5',
    hoverBg: 'hover:bg-emerald-500/10',
    icon: <Sparkles className="w-4 h-4 text-emerald-400 flex-shrink-0" />,
    badge: 'bg-emerald-500/20 text-emerald-300',
    label: 'Good',
  },
};

const AICoachPanel: React.FC<AICoachPanelProps> = ({ notes, isProcessing, onNoteClick }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new notes arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [notes.length]);

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-lg)',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: '300px',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexShrink: 0,
      }}>
        <Sparkles className="w-4 h-4" style={{ color: 'var(--accent-secondary)' }} />
        <span style={{
          fontSize: '0.75rem',
          fontWeight: 700,
          textTransform: 'uppercase' as const,
          letterSpacing: '0.1em',
          color: 'var(--text-secondary)',
        }}>
          AI Coach Notes
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: '0.7rem',
          padding: '2px 8px',
          borderRadius: '999px',
          background: 'var(--accent-secondary-dim)',
          color: 'var(--accent-secondary)',
          fontWeight: 600,
        }}>
          {notes.length} {notes.length === 1 ? 'note' : 'notes'}
        </span>
      </div>

      {/* Notes List */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        {notes.length === 0 ? (
          <div style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: '8px',
            padding: '24px',
          }}>
            {isProcessing ? (
              <>
                <div className="spinner" style={{ width: '24px', height: '24px', borderWidth: '2px' }} />
                <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                  Analyzing biomechanics...
                </p>
              </>
            ) : (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textAlign: 'center' }}>
                Upload a video to start analysis
              </p>
            )}
          </div>
        ) : (
          notes.map((note, idx) => {
            const config = severityConfig[note.severity] || severityConfig.warning;
            return (
              <div
                key={`${note.frame}-${note.joint}-${idx}`}
                className={`${config.bg} ${config.border} ${onNoteClick ? config.hoverBg : ''}`}
                onClick={() => onNoteClick && onNoteClick(note.frame)}
                style={{
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  borderRadius: '10px',
                  padding: '10px 12px',
                  animation: 'fadeIn 0.3s ease-out',
                  cursor: onNoteClick ? 'pointer' : 'default',
                  transition: 'all 0.2s ease-in-out',
                }}
              >
                {/* Note Header */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  marginBottom: '6px',
                }}>
                  {config.icon}
                  <span style={{
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    flex: 1,
                  }}>
                    {note.joint}
                  </span>
                  <span className={config.badge} style={{
                    fontSize: '0.6rem',
                    fontWeight: 700,
                    padding: '1px 6px',
                    borderRadius: '4px',
                    textTransform: 'uppercase' as const,
                    letterSpacing: '0.05em',
                  }}>
                    {config.label}
                  </span>
                </div>

                {/* Flaw */}
                <p style={{
                  fontSize: '0.78rem',
                  fontWeight: 500,
                  color: 'var(--text-primary)',
                  marginBottom: '4px',
                  lineHeight: 1.4,
                }}>
                  {note.flaw}
                </p>

                {/* Angle */}
                <div style={{
                  display: 'flex',
                  gap: '12px',
                  fontSize: '0.7rem',
                  color: 'var(--text-tertiary)',
                  marginBottom: '6px',
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <Clock className="w-3 h-3" /> {note.timestamp}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>
                    {note.angle}° (optimal: {note.optimal_range})
                  </span>
                </div>

                {/* Impact */}
                <p style={{
                  fontSize: '0.72rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.5,
                  marginBottom: '6px',
                }}>
                  {note.impact}
                </p>

                {/* Drill */}
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '6px',
                  padding: '6px 8px',
                  borderRadius: '6px',
                  background: 'hsla(220, 20%, 20%, 0.3)',
                }}>
                  <Dumbbell className="w-3.5 h-3.5 flex-shrink-0" style={{
                    color: 'var(--accent-primary)',
                    marginTop: '1px',
                  }} />
                  <p style={{
                    fontSize: '0.7rem',
                    color: 'var(--accent-primary)',
                    lineHeight: 1.4,
                    fontWeight: 500,
                  }}>
                    {note.drill}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default AICoachPanel;
