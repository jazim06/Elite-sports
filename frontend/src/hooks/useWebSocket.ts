/**
 * useWebSocket — Manages WebSocket connection for real-time analytics streaming.
 */
import { useRef, useCallback, useState } from 'react';
import { WS_BASE_URL } from '../utils/constants';
import type { FramePayload } from '../utils/types';

interface UseWebSocketReturn {
  connect: (videoId: string) => void;
  disconnect: () => void;
  sendMessage: (msg: Record<string, unknown>) => void;
  isConnected: boolean;
  isProcessing: boolean;
}

export function useWebSocket(
  onMessage: (data: FramePayload) => void,
): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const connect = useCallback(
    (videoId: string) => {
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      const url = `${WS_BASE_URL}/ws/analytics/${videoId}`;
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
        setIsProcessing(true);
      };

      ws.onmessage = (event) => {
        try {
          const data: FramePayload = JSON.parse(event.data);
          onMessage(data);

          if (data.type === 'complete') {
            setIsProcessing(false);
          }
        } catch (err) {
          console.error('Failed to parse WS message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
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

  const sendMessage = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { connect, disconnect, sendMessage, isConnected, isProcessing };
}
