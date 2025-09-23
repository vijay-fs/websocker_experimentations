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
  // Create a ref to track the last processed batch progress to prevent unnecessary updates
  const lastBatchProgressRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    // Get Pusher configuration from environment variables
    const pusherKey = process.env.NEXT_PUBLIC_PUSHER_APP_KEY || 'f69118021e989cd5a601';
    const pusherCluster = process.env.NEXT_PUBLIC_PUSHER_CLUSTER || 'ap2';

    console.log('🔧 Pusher config:', {
      key: pusherKey,
      cluster: pusherCluster,
      forceTLS: true,
      env: process.env.NODE_ENV,
      allEnvVars: {
        NEXT_PUBLIC_PUSHER_APP_KEY: process.env.NEXT_PUBLIC_PUSHER_APP_KEY,
        NEXT_PUBLIC_PUSHER_CLUSTER: process.env.NEXT_PUBLIC_PUSHER_CLUSTER
      }
    });

    const pusherInstance = new Pusher(pusherKey, {
      cluster: pusherCluster,
      forceTLS: true,
      disableStats: true
    });

    const handleConnectionStateChange = (state: string) => {
      console.log('🔗 Pusher connection state changed:', state);
      setIsConnected(state === 'connected');
      
      if (state === 'disconnected' || state === 'failed') {
        setError('WebSocket connection lost. Attempting to reconnect...');
      } else if (state === 'connected') {
        setError(null);
        console.log('✅ Pusher connected successfully');
      }
    };

    pusherInstance.connection.bind('connected', () => handleConnectionStateChange('connected'));
    pusherInstance.connection.bind('disconnected', () => handleConnectionStateChange('disconnected'));
    pusherInstance.connection.bind('failed', () => handleConnectionStateChange('failed'));

    pusherInstance.connection.bind('error', (error: any) => {
      console.error('Pusher connection error:', error);
      setError(`Connection error: ${error.message || 'Unknown error'}`);
    });

    pusherInstance.connection.bind('unavailable', () => {
      console.error('Pusher connection unavailable');
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
      console.log(`🔔 Frontend subscribing to channel ${channelName}`);
      console.log(`🔗 Pusher connection state: ${pusher.connection.state}`);
      
      // Check if already subscribed
      if (channelsRef.current.has(channelName)) {
        console.log(`Already subscribed to ${channelName}`);
        return;
      }
      
      const channel = pusher.subscribe(channelName);
      channelsRef.current.set(channelName, channel);
      
      console.log(`✅ Successfully subscribed to ${channelName}`);
      
      // Bind to ALL possible events to debug what's being received
      channel.bind_global((eventName: string, data: any) => {
        console.log(`🌍 GLOBAL EVENT RECEIVED: ${eventName}`, JSON.stringify(data, null, 2));
        console.log(`🌍 Event timestamp: ${new Date().toISOString()}`);
        console.log(`🌍 Channel: ${channelName}`);
        
        // Store in window for inspection
        if (!(window as any).__allEvents) (window as any).__allEvents = [];
        (window as any).__allEvents.push({
          timestamp: new Date().toISOString(),
          channel: channelName,
          event: eventName,
          data: data
        });
      });
      
      channel.bind('batch_update', (data: any) => {
        console.log('📨 RAW Received update:', JSON.stringify(data, null, 2));
        (window as any).__lastBatchUpdate = data;
        // Extract data from nested structure if needed
        const updateData = data.data || data;
        console.log('📨 PROCESSED update data:', JSON.stringify(updateData, null, 2));

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

        console.log(`✅ Update for batch ${batchProgress.batchId}: ${batchProgress.progress}% - ${batchProgress.message}`);

        setBatchProgressMap(prev => {
          const newMap = new Map(prev);
          newMap.set(batchProgress.batchId, batchProgress);
          console.log('🗺️ batchProgressMap updated:', Array.from(newMap.entries()));
          return newMap;
        });
      });
      
      channel.bind('pusher:subscription_succeeded', () => {
        console.log(`Successfully subscribed to ${channelName}`);
      });
      
      channel.bind('pusher:subscription_error', (error: any) => {
        console.error(`Failed to subscribe to ${channelName}:`, error);
        setError(`Failed to subscribe to batch ${batchId}`);
      });
      
      // Track active subscription
      setActiveSubscriptions(prev => {
        const newSet = new Set(prev);
        newSet.add(batchId);
        return newSet;
      });
    } else {
      console.error('Cannot subscribe: Pusher not available. Connected:', isConnected, 'Pusher:', !!pusher);
      // Don't set error - allow subscription to work when pusher becomes available
    }
  }, [pusher, isConnected]);

  const unsubscribeFromProcess = useCallback((batchId: string) => {
    if (pusher) {
      const channelName = `batch.${batchId}`;
      console.log(`Unsubscribing from channel ${channelName}`);
      
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
