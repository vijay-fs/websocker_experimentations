/**
 * PostHog Analytics Integration for Frontend
 * Tracks user interactions, errors, and performance metrics
 */
import posthog from 'posthog-js';

let isInitialized = false;

/**
 * Initialize PostHog client
 */
export function initPostHog() {
  if (typeof window === 'undefined') return;
  
  const apiKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  const host = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com';
  
  if (apiKey && !isInitialized) {
    try {
      posthog.init(apiKey, {
        api_host: host,
        loaded: (posthog) => {
          if (process.env.NODE_ENV === 'development') {
            posthog.opt_out_capturing();
            console.log('PostHog initialized (opt-out in development)');
          }
        },
      });
      isInitialized = true;
    } catch (error) {
      console.error('Failed to initialize PostHog:', error);
    }
  }
}

/**
 * Track a custom event
 */
export function trackEvent(eventName: string, properties?: Record<string, any>) {
  if (!isInitialized) return;
  
  try {
    posthog.capture(eventName, properties);
  } catch (error) {
    console.error(`Failed to track event '${eventName}':`, error);
  }
}

/**
 * Track file upload started
 */
export function trackUploadStarted(fileName: string, fileSize: number, fileType: string) {
  trackEvent('file_upload_started', {
    file_name: fileName,
    file_size_bytes: fileSize,
    file_type: fileType,
    component: 'frontend_upload',
  });
}

/**
 * Track file upload completed
 */
export function trackUploadCompleted(batchId: string, fileName: string, uploadTime: number) {
  trackEvent('file_upload_completed', {
    batch_id: batchId,
    file_name: fileName,
    upload_time_ms: uploadTime,
    component: 'frontend_upload',
  });
}

/**
 * Track file upload failed
 */
export function trackUploadFailed(fileName: string, errorMessage: string) {
  trackEvent('file_upload_failed', {
    file_name: fileName,
    error_message: errorMessage,
    component: 'frontend_upload',
  });
}

/**
 * Track processing progress viewed
 */
export function trackProgressViewed(batchId: string, progress: number) {
  trackEvent('processing_progress_viewed', {
    batch_id: batchId,
    progress_percentage: progress,
    component: 'frontend_progress',
  });
}

/**
 * Track results expanded
 */
export function trackResultsExpanded(batchId: string, detectionCount: number) {
  trackEvent('results_expanded', {
    batch_id: batchId,
    detection_count: detectionCount,
    component: 'frontend_results',
  });
}

/**
 * Track full-size image opened
 */
export function trackFullSizeImageOpened(batchId: string) {
  trackEvent('full_size_image_opened', {
    batch_id: batchId,
    component: 'frontend_results',
  });
}

/**
 * Track WebSocket connection status
 */
export function trackWebSocketConnection(status: 'connected' | 'disconnected' | 'error', errorMessage?: string) {
  trackEvent('websocket_connection', {
    status,
    error_message: errorMessage,
    component: 'frontend_websocket',
  });
}

/**
 * Track error occurred
 */
export function trackError(errorType: string, errorMessage: string, context?: Record<string, any>) {
  trackEvent('error_occurred', {
    error_type: errorType,
    error_message: errorMessage,
    component: 'frontend',
    ...context,
  });
}

/**
 * Track page view
 */
export function trackPageView(pageName: string) {
  if (!isInitialized) return;
  
  try {
    posthog.capture('$pageview', {
      page_name: pageName,
    });
  } catch (error) {
    console.error('Failed to track page view:', error);
  }
}

/**
 * Identify user (optional - for user tracking)
 */
export function identifyUser(userId: string, properties?: Record<string, any>) {
  if (!isInitialized) return;
  
  try {
    posthog.identify(userId, properties);
  } catch (error) {
    console.error('Failed to identify user:', error);
  }
}

/**
 * Reset user session
 */
export function resetUser() {
  if (!isInitialized) return;
  
  try {
    posthog.reset();
  } catch (error) {
    console.error('Failed to reset user:', error);
  }
}
