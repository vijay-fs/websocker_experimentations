import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

interface BatchProgress {
  batchId: string;
  message: string;
  timestamp: string;
  progress: number;
}

interface UseSocketReturn {
  socket: Socket | null;
  isConnected: boolean;
  subscribeToProcess: (batchId: string) => void;
  unsubscribeFromProcess: (batchId: string) => void;
  batchProgressMap: Map<string, BatchProgress>;
  error: string | null;
}

export const useSocket = (serverUrl: string = 'http://localhost:8001'): UseSocketReturn => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [batchProgressMap, setBatchProgressMap] = useState<Map<string, BatchProgress>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  useEffect(() => {
    const socketInstance = io(serverUrl, {
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
    });

    socketInstance.on('connect', () => {
      console.log('Connected to Socket.IO server');
      setIsConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
    });

    socketInstance.on('disconnect', (reason) => {
      console.log('Disconnected from Socket.IO server:', reason);
      setIsConnected(false);
      
      if (reason === 'io server disconnect') {
        socketInstance.connect();
      }
    });

    socketInstance.on('connect_error', (error) => {
      console.error('Connection error:', error);
      reconnectAttempts.current++;
      
      if (reconnectAttempts.current >= maxReconnectAttempts) {
        setError(`Failed to connect after ${maxReconnectAttempts} attempts. Please check if the server is running.`);
      } else {
        setError(`Connection attempt ${reconnectAttempts.current}/${maxReconnectAttempts} failed. Retrying...`);
      }
    });

    socketInstance.on('batch_progress', (data: BatchProgress) => {
      console.log('Frontend received batch progress:', data);
      setBatchProgressMap(prev => {
        console.log('Current batch progress map size:', prev.size);
        const newMap = new Map(prev);
        newMap.set(data.batchId, data);
        console.log('Updated batch progress map size:', newMap.size);
        console.log('Updated batch progress map:', Array.from(newMap.entries()));
        return newMap;
      });
    });

    socketInstance.on('reconnect', () => {
      console.log('Reconnected to Socket.IO server');
      setError(null);
      reconnectAttempts.current = 0;
    });

    socketInstance.on('reconnect_failed', () => {
      console.error('Failed to reconnect to Socket.IO server');
      setError('Failed to reconnect to server. Please refresh the page.');
    });

    setSocket(socketInstance);

    return () => {
      socketInstance.disconnect();
    };
  }, [serverUrl]);

  const subscribeToProcess = (batchId: string) => {
    if (socket && isConnected) {
      console.log(`Frontend subscribing to batch ${batchId}`);
      socket.emit('subscribe_to_batch', batchId);
      console.log(`Subscription request sent for batch ${batchId}`);
    } else {
      console.error('Cannot subscribe: Socket not connected. Connected:', isConnected, 'Socket:', !!socket);
      setError('Cannot subscribe: Socket not connected');
    }
  };

  const unsubscribeFromProcess = (batchId: string) => {
    if (socket && isConnected) {
      console.log(`Unsubscribing from batch ${batchId}`);
      socket.emit('unsubscribe_from_batch', batchId);
    }
  };

  return {
    socket,
    isConnected,
    subscribeToProcess,
    unsubscribeFromProcess,
    batchProgressMap,
    error,
  };
};