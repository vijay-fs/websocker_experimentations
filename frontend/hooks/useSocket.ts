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
  console.log('🚀 [useSocket] Hook initialized/re-rendered');
  const [pusher, setPusher] = useState<Pusher | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [batchProgressMap, setBatchProgressMap] = useState<Map<string, BatchProgress>>(new Map());
  const [activeSubscriptions, setActiveSubscriptions] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const channelsRef = useRef<Map<string, any>>(new Map());
  // Create a ref to track the last processed batch progress to prevent unnecessary updates
  const lastBatchProgressRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    console.log('🔧 [useSocket] useEffect triggered - initializing Pusher');
    
    // Get Pusher configuration from environment variables
    const pusherKey = process.env.NEXT_PUBLIC_PUSHER_APP_KEY || '';
    const pusherCluster = process.env.NEXT_PUBLIC_PUSHER_CLUSTER || 'us2';
    const pusherUseTLS = process.env.NEXT_PUBLIC_PUSHER_USE_TLS !== 'false';
    
    console.log('🔧 [useSocket] Pusher config:', {
      key: pusherKey,
      cluster: pusherCluster,
      forceTLS: pusherUseTLS,
      env: process.env.NODE_ENV,
      allEnvVars: {
        NEXT_PUBLIC_PUSHER_APP_KEY: process.env.NEXT_PUBLIC_PUSHER_APP_KEY,
        NEXT_PUBLIC_PUSHER_CLUSTER: process.env.NEXT_PUBLIC_PUSHER_CLUSTER,
        NEXT_PUBLIC_PUSHER_USE_TLS: process.env.NEXT_PUBLIC_PUSHER_USE_TLS
      }
    });
    
    if (!pusherKey) {
      console.error('🔧 [useSocket] NEXT_PUBLIC_PUSHER_APP_KEY is required');
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
      console.log('🔗 [useSocket] Pusher connection state changed:', state);
      console.log('🔗 [useSocket] Previous isConnected state:', isConnected);
      setIsConnected(state === 'connected');
      
      if (state === 'disconnected' || state === 'failed') {
        setError('WebSocket connection lost. Attempting to reconnect...');
        console.log('❌ [useSocket] Connection failed/disconnected');
      } else if (state === 'connected') {
        setError(null);
        console.log('✅ [useSocket] Pusher connected successfully');
      }
    };

    pusherInstance.connection.bind('connected', () => handleConnectionStateChange('connected'));
    pusherInstance.connection.bind('disconnected', () => handleConnectionStateChange('disconnected'));
    pusherInstance.connection.bind('failed', () => handleConnectionStateChange('failed'));

    pusherInstance.connection.bind('error', (error: any) => {
      console.error('[useSocket] Pusher connection error:', error);
      setError(`Connection error: ${error.message || 'Unknown error'}`);
    });

    pusherInstance.connection.bind('unavailable', () => {
      console.error('[useSocket] Pusher connection unavailable');
      setError('Connection unavailable. Please check if the server is running.');
    });

    setPusher(pusherInstance);
    console.log('✅ [useSocket] Pusher instance created and set');

    return () => {
      console.log('🧹 [useSocket] Cleanup - unsubscribing from all channels');
      // Unsubscribe from all channels
      channelsRef.current.forEach((channel, channelName) => {
        pusherInstance.unsubscribe(channelName);
      });
      channelsRef.current.clear();
      pusherInstance.disconnect();
    };
  }, []);

  const subscribeToProcess = useCallback((batchId: string) => {
    console.log(`🔔 [useSocket] subscribeToProcess called with batchId: ${batchId}`);
    console.log(`🔔 [useSocket] Current pusher state:`, !!pusher);
    console.log(`🔔 [useSocket] Current isConnected state:`, isConnected);
    
    if (pusher) {
      const channelName = `batch.${batchId}`;
      console.log(`🔔 [useSocket] Frontend subscribing to channel ${channelName}`);
      console.log(`🔗 [useSocket] Pusher connection state: ${pusher.connection.state}`);
      
      // Check if already subscribed
      if (channelsRef.current.has(channelName)) {
        console.log(`[useSocket] Already subscribed to ${channelName}`);
        return;
      }
      
      const channel = pusher.subscribe(channelName);
      channelsRef.current.set(channelName, channel);
      
      console.log(`✅ [useSocket] Successfully subscribed to ${channelName}`);
      
      // Bind to ALL possible events to debug what's being received
      channel.bind_global((eventName: string, data: any) => {
        console.log(`🌍 [useSocket] GLOBAL EVENT RECEIVED: ${eventName}`, JSON.stringify(data, null, 2));
        console.log(`🌍 [useSocket] Event timestamp: ${new Date().toISOString()}`);
        console.log(`🌍 [useSocket] Channel: ${channelName}`);
        
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
        console.log('📨 [useSocket] RAW Received update:', JSON.stringify(data, null, 2));
        (window as any).__lastBatchUpdate = data;
        // Extract data from nested structure if needed
        const updateData = data.data || data;
        console.log('📨 [useSocket] PROCESSED update data:', JSON.stringify(updateData, null, 2));

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

        console.log(`✅ [useSocket] Update for batch ${batchProgress.batchId}: ${batchProgress.progress}% - ${batchProgress.message}`);

        setBatchProgressMap(prev => {
          const newMap = new Map(prev);
          newMap.set(batchProgress.batchId, batchProgress);
          console.log('🗺️ [useSocket] batchProgressMap updated:', Array.from(newMap.entries()));
          return newMap;
        });
      });
      
      channel.bind('pusher:subscription_succeeded', () => {
        console.log(`[useSocket] Successfully subscribed to ${channelName}`);
      });
      
      channel.bind('pusher:subscription_error', (error: any) => {
        console.error(`[useSocket] Failed to subscribe to ${channelName}:`, error);
        setError(`Failed to subscribe to batch ${batchId}`);
      });
      
      // Track active subscription
      setActiveSubscriptions(prev => {
        const newSet = new Set(prev);
        newSet.add(batchId);
        return newSet;
      });
    } else {
      console.error('[useSocket] Cannot subscribe: Pusher not available. Connected:', isConnected, 'Pusher:', !!pusher);
      // Don't set error - allow subscription to work when pusher becomes available
    }
  }, [pusher, isConnected]);

  const unsubscribeFromProcess = useCallback((batchId: string) => {
    console.log(`🔕 [useSocket] unsubscribeFromProcess called with batchId: ${batchId}`);
    if (pusher) {
      const channelName = `batch.${batchId}`;
      console.log(`[useSocket] Unsubscribing from channel ${channelName}`);
      
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

  console.log(`🔍 [useSocket] Current state - isConnected: ${isConnected}, pusher: ${!!pusher}, activeSubscriptions: ${activeSubscriptions.size}, batchProgressMap: ${batchProgressMap.size}`);

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
