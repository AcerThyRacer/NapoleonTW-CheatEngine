/**
 * Custom React hook for WebSocket communication with the Python backend.
 * Manages connection lifecycle, reconnection, and message dispatch.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { InboundMessage, OutboundMessage } from "../types/websocket";

export interface UseWebSocketOptions {
  url: string;
  /** Reconnect delay in ms (default 2000) */
  reconnectDelay?: number;
  onMessage?: (msg: InboundMessage) => void;
}

export interface UseWebSocketReturn {
  connected: boolean;
  send: (msg: OutboundMessage) => void;
  lastMessage: InboundMessage | null;
}

export function useWebSocket({
  url,
  reconnectDelay = 2000,
  onMessage,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<InboundMessage | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setConnected(true);
        // Request full state on connection
        ws.send(JSON.stringify({ type: "get_state" }));
      };

      ws.onmessage = (event) => {
        try {
          const msg: InboundMessage = JSON.parse(event.data);
          setLastMessage(msg);
          onMessageRef.current?.(msg);
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        // Auto-reconnect
        reconnectTimer.current = setTimeout(connect, reconnectDelay);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      reconnectTimer.current = setTimeout(connect, reconnectDelay);
    }
  }, [url, reconnectDelay]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((msg: OutboundMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { connected, send, lastMessage };
}
