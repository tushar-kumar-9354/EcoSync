'use client';

import { useEffect, useRef, useCallback } from 'react';

interface WebSocketMessage {
  type: 'sensor_update' | 'alert';
  sensor_id?: string;
  alert?: any;
  data?: any;
}

export function useWebSocket(onMessage: (msg: WebSocketMessage) => void, enabled = true) {
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return;

    const wsBase = process.env.NEXT_PUBLIC_WS_URL || `ws://${window.location.hostname}:8000`;
    const wsUrl = `${wsBase}/api/v1/ws`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current(data);
        } catch (e) {
          console.error('WebSocket parse error:', e);
        }
      };

      wsRef.current.onclose = () => {
        // Reconnect after 3 seconds
        setTimeout(connect, 3000);
      };

      wsRef.current.onerror = () => {
        wsRef.current?.close();
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect, enabled]);

  return wsRef.current;
}
