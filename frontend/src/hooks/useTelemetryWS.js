import { useState, useEffect, useRef } from 'react';

export function useTelemetryWS(url = 'ws://127.0.0.1:8000/ws/telemetry') {
  const [data, setData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessageTime, setLastMessageTime] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    function connect() {
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data);
            setData(parsed);
            setLastMessageTime(Date.now());
          } catch (err) {
            console.error('Failed parsing WS message:', err);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          // Attempt automatic reconnection every 2 seconds
          reconnectTimeoutRef.current = setTimeout(connect, 2000);
        };

        ws.onerror = (err) => {
          console.debug('WS connection error:', err);
          ws.close();
        };
      } catch (e) {
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connect, 2000);
      }
    }

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [url]);

  return { data, isConnected, lastMessageTime };
}
