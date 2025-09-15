import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

interface BatchProgress {
  batchId: string;
  message: string;
  timestamp: string;
  progress: number;
  result?: {
    detected_symbols?: Array<{
      text: string;
      confidence: number;
      bbox: {
        top_left: [number, number];
        top_right: [number, number];
        bottom_right: [number, number];
        bottom_left: [number, number];
      };
    }>;
    marked_image?: string;
    symbol_count?: number;
  }; // Optional result data for image processing
}

interface UseSocketReturn {
  socket: Socket | null;
  isConnected: boolean;
  subscribeToProcess: (batchId: string) => void;
  unsubscribeFromProcess: (batchId: string) => void;
  batchProgressMap: Map<string, BatchProgress>;
  activeSubscriptions: Set<string>;
  error: string | null;
}

export const useSocket = (serverUrl: string = 'http://localhost:8001'): UseSocketReturn => {
 const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [batchProgressMap, setBatchProgressMap] = useState<Map<string, BatchProgress>>(new Map());
  const [activeSubscriptions, setActiveSubscriptions] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  // Create a ref to track the last processed batch progress to prevent unnecessary updates
  const lastBatchProgressRef = useRef<Map<string, string>>(new Map());

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
      // Create a unique key for this progress update
      const progressKey = `${data.batchId}-${data.timestamp}-${data.progress}`;
      const lastProgressKey = lastBatchProgressRef.current.get(data.batchId);
      
      // Skip if we've already processed this exact progress update
      if (lastProgressKey === progressKey) {
        return;
      }
      
      lastBatchProgressRef.current.set(data.batchId, progressKey);
      console.log('Frontend received batch progress:', data);
      setBatchProgressMap(prev => {
        const newMap = new Map(prev);
        newMap.set(data.batchId, data);
        return newMap;
      });
    });

 socketInstance.on('reconnect', () => {
      console.log('Reconnected to Socket.IO server');
      setError(null);
      reconnectAttempts.current = 0;
      
      // Resubscribe to all active batches
      // Use a small delay to ensure the connection is fully established
      setTimeout(() => {
        activeSubscriptions.forEach(batchId => {
          console.log(`Resubscribing to batch ${batchId} after reconnection`);
          if (socketInstance.connected) {
            socketInstance.emit('subscribe_to_batch', batchId);
          }
        });
      }, 100);
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

 const subscribeToProcess = useCallback((batchId: string) => {
    if (socket && isConnected) {
      console.log(`Frontend subscribing to batch ${batchId}`);
      socket.emit('subscribe_to_batch', batchId);
      console.log(`Subscription request sent for batch ${batchId}`);
      
      // Track active subscription
      setActiveSubscriptions(prev => {
        const newSet = new Set(prev);
        newSet.add(batchId);
        return newSet;
      });
    } else {
      console.error('Cannot subscribe: Socket not connected. Connected:', isConnected, 'Socket:', !!socket);
      setError('Cannot subscribe: Socket not connected');
    }
  }, [socket, isConnected]);

  const unsubscribeFromProcess = useCallback((batchId: string) => {
    if (socket && isConnected) {
      console.log(`Unsubscribing from batch ${batchId}`);
      socket.emit('unsubscribe_from_batch', batchId);
      
      // Remove from active subscriptions
      setActiveSubscriptions(prev => {
        const newSet = new Set(prev);
        newSet.delete(batchId);
        return newSet;
      });
    }
  }, [socket, isConnected]);

  return {
    socket,
    isConnected,
    subscribeToProcess,
    unsubscribeFromProcess,
    batchProgressMap,
    activeSubscriptions,
    error,
  };
};
