import { useEffect, useRef, useState, useCallback } from 'react';
import Pusher from 'pusher-js';

interface BatchProgress {
  batchId: string;
  message: string;
  timestamp: string;
  progress: number;
  messageType?: string; // info, success, error, warning for toast notifications
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
    processing_stats?: {
      total_detections: number;
      high_confidence_detections: number;
      image_dimensions: string;
      original_dimensions: string;
      processing_time: string;
      compressed_size_kb: number;
    };
  }; // Optional result data for image processing
}

interface UsePusherReturn {
  pusher: Pusher | null;
  isConnected: boolean;
  subscribeToProcess: (batchId: string) => void;
  unsubscribeFromProcess: (batchId: string) => void;
  batchProgressMap: Map<string, BatchProgress>;
  activeSubscriptions: Set<string>;
  error: string | null;
}

export const useSocket = (): UsePusherReturn => {
  const [pusher, setPusher] = useState<Pusher | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [batchProgressMap, setBatchProgressMap] = useState<Map<string, BatchProgress>>(new Map());
  const [activeSubscriptions, setActiveSubscriptions] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const channelsRef = useRef<Map<string, any>>(new Map());

  useEffect(() => {
    
    // Get Pusher configuration from environment variables
    const pusherKey = process.env.NEXT_PUBLIC_PUSHER_APP_KEY || '';
    const pusherCluster = process.env.NEXT_PUBLIC_PUSHER_CLUSTER || 'us2';
    const pusherUseTLS = process.env.NEXT_PUBLIC_PUSHER_USE_TLS !== 'false';
    
    
    if (!pusherKey) {
      setError('Pusher configuration missing. Please set NEXT_PUBLIC_PUSHER_APP_KEY environment variable.');
      return;
    }
    
    const pusherInstance = new Pusher(pusherKey, {
      cluster: pusherCluster,
      forceTLS: pusherUseTLS,
      disableStats: true,
      enabledTransports: ['ws', 'wss']
    });

    const handleConnectionStateChange = (state: string) => {
      setIsConnected(state === 'connected');
      
      if (state === 'disconnected' || state === 'failed') {
        setError('WebSocket connection lost. Attempting to reconnect...');
      } else if (state === 'connected') {
        setError(null);
      }
    };

    pusherInstance.connection.bind('connected', () => handleConnectionStateChange('connected'));
    pusherInstance.connection.bind('disconnected', () => handleConnectionStateChange('disconnected'));
    pusherInstance.connection.bind('failed', () => handleConnectionStateChange('failed'));

    pusherInstance.connection.bind('error', (error: any) => {
      setError(`Connection error: ${error.message || 'Unknown error'}`);
    });

    pusherInstance.connection.bind('unavailable', () => {
      setError('Connection unavailable. Please check if the server is running.');
    });

    setPusher(pusherInstance);

    return () => {
      // Unsubscribe from all channels
      channelsRef.current.forEach((channel, channelName) => {
        pusherInstance.unsubscribe(channelName);
      });
      channelsRef.current.clear();
      pusherInstance.disconnect();
    };
  }, []);

  const subscribeToProcess = useCallback((batchId: string) => {
    
    if (pusher) {
      const channelName = `batch.${batchId}`;
      
      // Check if already subscribed
      if (channelsRef.current.has(channelName)) {
        return;
      }
      
      const channel = pusher.subscribe(channelName);
      channelsRef.current.set(channelName, channel);
      
      
      channel.bind('batch_update', (data: any) => {
        // Extract data from nested structure if needed
        const updateData = data.data || data;

        // Show a toast for every update
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('OCRBatchUpdate', { detail: updateData }));
        }

        const batchProgress: BatchProgress = {
          batchId: updateData.batch_id || data.batch_id,
          message: updateData.message || 'Processing...',
          timestamp: updateData.timestamp || new Date().toISOString(),
          progress: updateData.progress || 0,
          messageType: updateData.message_type || 'info',
          result: updateData.result
        };

        setBatchProgressMap(prev => {
          const newMap = new Map(prev);
          newMap.set(batchProgress.batchId, batchProgress);
          return newMap;
        });
      });
      
      channel.bind('pusher:subscription_error', (error: any) => {
        setError(`Failed to subscribe to batch ${batchId}`);
      });
      
      // Track active subscription
      setActiveSubscriptions(prev => {
        const newSet = new Set(prev);
        newSet.add(batchId);
        return newSet;
      });
    }
  }, [pusher, isConnected]);

  const unsubscribeFromProcess = useCallback((batchId: string) => {
    if (pusher) {
      const channelName = `batch.${batchId}`;
      
      const channel = channelsRef.current.get(channelName);
      if (channel) {
        pusher.unsubscribe(channelName);
        channelsRef.current.delete(channelName);
      }
      
      // Remove from active subscriptions
      setActiveSubscriptions(prev => {
        const newSet = new Set(prev);
        newSet.delete(batchId);
        return newSet;
      });
    }
  }, [pusher]);


  return {
    pusher,
    isConnected,
    subscribeToProcess,
    unsubscribeFromProcess,
    batchProgressMap,
    activeSubscriptions,
    error,
  };
};
