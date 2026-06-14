/**
 * useWebSocket — Manages WebSocket connection for processing progress.
 * 
 * In the two-pass architecture, this is ONLY used to receive progress
 * updates (0-100%) while the backend analyzes the video in the background.
 */
import { useRef, useCallback, useState, useEffect } from 'react';
import { WS_BASE_URL } from '../utils/constants';
import type { ProgressPayload } from '../utils/types';

interface UseWebSocketReturn {
  connect: (videoId: string) => void;
  disconnect: () => void;
  isConnected: boolean;
  isProcessing: boolean;
}

export function useWebSocket(
  onMessage: (data: ProgressPayload) => void,
): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  
  // Update ref to always hold the latest callback without triggering reconnects
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const connect = useCallback(
    (videoId: string) => {
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      // Connect to the new progress endpoint
      const url = `${WS_BASE_URL}/ws/progress/${videoId}`;
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('✅ Progress WebSocket connected');
        setIsConnected(true);
        setIsProcessing(true);
      };

      ws.onmessage = (event) => {
        try {
          const data: ProgressPayload = JSON.parse(event.data);
          onMessageRef.current(data);

          if (data.status === 'completed' || data.status === 'error' || data.type === 'complete') {
            setIsProcessing(false);
            ws.close();
          }
        } catch (err) {
          console.error('Failed to parse progress WS message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('Progress WebSocket error:', err);
      };

      ws.onclose = () => {
        console.log('Progress WebSocket disconnected');
        setIsConnected(false);
        setIsProcessing(false);
      };

      wsRef.current = ws;
    },
    [onMessage],
  );

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  return { connect, disconnect, isConnected, isProcessing };
}
