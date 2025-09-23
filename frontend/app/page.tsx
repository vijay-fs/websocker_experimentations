'use client';

import { useState, useEffect } from 'react';
import { useSocket } from '@/hooks/useSocket';
import Image from 'next/image';

interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  onClose: () => void;
}

const Toast = ({ message, type, onClose }: ToastProps) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-yellow-500',
    info: 'bg-blue-500'
  }[type];

  return (
    <div className={`fixed top-4 right-4 ${bgColor} text-white px-4 py-3 rounded-lg shadow-lg z-50 max-w-sm`}>
      <div className="flex items-center gap-2">
        <span className="flex-1">{message}</span>
        <button onClick={onClose} className="ml-2 text-white hover:text-gray-200">×</button>
      </div>
    </div>
  );
};

interface BatchStatus {
  batch_id: string;
  status: string;
  progress: number;
  messages: string[];
  created_at: string;
  updated_at: string;
  result?: any;
}

interface Process {
  batchId: string;
  status: BatchStatus;
  isActive: boolean;
}

export default function Home() {
  const { pusher, isConnected, subscribeToProcess, batchProgressMap, error } = useSocket();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [activeProcesses, setActiveProcesses] = useState<Map<string, Process>>(new Map());
  const [toasts, setToasts] = useState<Array<{id: string, message: string, type: 'success' | 'error' | 'warning' | 'info'}>>([]);

  const addToast = (message: string, type: 'success' | 'error' | 'warning' | 'info') => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, { id, message, type }]);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  // Handle real-time updates
  useEffect(() => {
    console.log('batchProgressMap changed:', Array.from(batchProgressMap.entries()));
    batchProgressMap.forEach((progress, batchId) => {
      console.log(`Update for ${batchId}: ${progress.progress}%`);
      
      if (progress.messageType === 'success' || progress.messageType === 'error') {
        addToast(progress.message, progress.messageType as 'success' | 'error' | 'warning' | 'info');
      }
      
      setActiveProcesses(prev => {
        const newMap = new Map(prev);
        const existing = newMap.get(batchId);
        
        const updatedStatus: BatchStatus = {
          batch_id: batchId,
          status: progress.progress === 100 ? 'completed' : 'running',
          progress: progress.progress,
          messages: existing?.status.messages ?
            (existing.status.messages.includes(progress.message) ?
              existing.status.messages :
              [...existing.status.messages, progress.message]) :
            [progress.message],
          created_at: existing?.status.created_at || new Date().toISOString(),
          updated_at: progress.timestamp,
          result: progress.result
        };
        
        newMap.set(batchId, {
          batchId,
          status: updatedStatus,
          isActive: progress.progress < 100
        });
        
        return newMap;
      });
      
      // Only fetch batch status as fallback if Pusher connection was lost
      if (progress.progress === 100 && !isConnected) {
        console.log(`Pusher disconnected, fetching final status for ${batchId}`);
        setTimeout(() => {
          fetch(`http://localhost:8000/api/batch-status/${batchId}`)
            .then(response => response.ok ? response.json() : Promise.reject('Failed'))
            .then(data => {
              console.log(`Fallback data fetched for ${batchId}:`, data);
              setActiveProcesses(prev => {
                const newMap = new Map(prev);
                const process = newMap.get(batchId);
                if (process && data.result) {
                  newMap.set(batchId, {
                    ...process,
                    status: { ...process.status, result: data.result }
                  });
                }
                return newMap;
              });
            })
            .catch(error => console.warn(`Fallback fetch failed for ${batchId}:`, error));
        }, 1000);
      }
    });
  }, [batchProgressMap]);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadStatus(`Selected file: ${file.name}`);
    }
  };

  const handleUploadButtonClick = async () => {
    if (!selectedFile) return;

    try {
      setUploadStatus('Uploading file...');
      
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload file');
      }

      const data = await response.json();
      setUploadStatus(`File uploaded successfully. Processing started with batch ID: ${data.batch_id}`);
      
      // Subscribe immediately
      subscribeToProcess(data.batch_id);
      
      // Initialize process state
      const initialStatus: BatchStatus = {
        batch_id: data.batch_id,
        status: 'queued',
        progress: 0,
        messages: [data.message],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      setActiveProcesses(prev => {
        const newMap = new Map(prev);
        newMap.set(data.batch_id, {
          batchId: data.batch_id,
          status: initialStatus,
          isActive: true
        });
        return newMap;
      });
      
      setSelectedFile(null);
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus('Error uploading file');
    }
  };

  const getActiveProcessesArray = () => {
    return Array.from(activeProcesses.values()).sort((a, b) => 
      new Date(b.status.created_at).getTime() - new Date(a.status.created_at).getTime()
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Toast notifications */}
      <div className="fixed top-4 right-4 space-y-2 z-50">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
      
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">WebSocket Process Monitor</h1>
        
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center gap-4 mb-4">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm">
              Pusher: {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
        </div>

        <div className="mb-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Upload Engineering Drawing</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select an engineering drawing image
              </label>
              <input
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              <p className="mt-1 text-sm text-gray-500">Supported formats: JPG, PNG, BMP, TIFF</p>
            </div>

            {uploadStatus && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded">
                <p className="text-sm text-blue-700">{uploadStatus}</p>
              </div>
            )}

            <button
              onClick={handleUploadButtonClick}
              disabled={!selectedFile || !isConnected}
              className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded transition-colors"
            >
              Process Engineering Drawing
            </button>
          </div>
        </div>

        <div className="grid gap-4 mb-6">
          <h2 className="text-xl font-semibold">Active & Recent Processes</h2>
          
          {getActiveProcessesArray().length === 0 && (
            <div className="bg-white rounded-lg shadow-md p-6 text-center text-gray-500">
              No processes started yet. Upload an engineering drawing to begin processing.
            </div>
          )}
          
          {getActiveProcessesArray().map((process) => (
            <div key={process.batchId} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Batch ID: {process.batchId}
                  </h3>
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-3 h-3 rounded-full ${
                      process.status.status === 'completed' ? 'bg-green-500' :
                      process.status.status === 'running' ? 'bg-blue-500 animate-pulse' :
                      process.status.status === 'failed' ? 'bg-red-500' :
                      'bg-yellow-500'
                    }`}></div>
                    <span className="text-sm font-medium capitalize">
                      {process.status.status}
                    </span>
                    <span className="text-lg font-bold text-blue-600">
                      {process.status.progress}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Enhanced Progress Bar with Stages */}
              <div className="mb-4">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Validation</span>
                  <span>Processing</span>
                  <span>OCR</span>
                  <span>Complete</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 relative">
                  {/* Stage markers */}
                  <div className="absolute top-0 h-3 w-px bg-gray-300" style={{ left: '10%' }}></div>
                  <div className="absolute top-0 h-3 w-px bg-gray-300" style={{ left: '30%' }}></div>
                  <div className="absolute top-0 h-3 w-px bg-gray-300" style={{ left: '60%' }}></div>
                  <div className="absolute top-0 h-3 w-px bg-gray-300" style={{ left: '90%' }}></div>

                  {/* Progress fill */}
                  <div
                    className={`h-3 rounded-full transition-all duration-500 ease-out ${
                      process.status.status === 'completed' ? 'bg-green-500' :
                      process.status.status === 'failed' ? 'bg-red-500' :
                      'bg-blue-500'
                    }`}
                    style={{ width: `${Math.max(process.status.progress, 0)}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0%</span>
                  <span>25%</span>
                  <span>50%</span>
                  <span>75%</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Current Message with Enhanced Display */}
              <div className="mb-4">
                <div className="text-sm font-medium text-gray-900 mb-2">
                  Current Step: {process.status.messages[process.status.messages.length - 1] || 'Processing...'}
                </div>

                {/* Progress Steps Timeline */}
                {process.status.messages.length > 1 && (
                  <details className="mt-3">
                    <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">
                      View All Progress Steps ({process.status.messages.length})
                    </summary>
                    <div className="mt-2 bg-gray-50 rounded p-3 max-h-32 overflow-y-auto">
                      {process.status.messages.map((message, index) => (
                        <div key={index} className="flex items-center gap-2 py-1 text-xs">
                          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                            index === process.status.messages.length - 1
                              ? 'bg-blue-500 animate-pulse'
                              : 'bg-green-400'
                          }`}></div>
                          <span className={`${
                            index === process.status.messages.length - 1
                              ? 'text-gray-900 font-medium'
                              : 'text-gray-600'
                          }`}>
                            {message}
                          </span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>

              {/* Results Section */}
              {process.status.result && (
                <div className="border-t pt-4">
                  <h4 className="text-md font-semibold text-gray-900 mb-3">OCR Results</h4>
                  
                  {/* Stats */}
                  {process.status.result.processing_stats && (
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div className="bg-blue-50 p-3 rounded">
                        <div className="text-xs text-blue-600 font-medium">Detections</div>
                        <div className="text-xl font-bold text-blue-900">
                          {process.status.result.processing_stats.total_detections}
                        </div>
                      </div>
                      <div className="bg-green-50 p-3 rounded">
                        <div className="text-xs text-green-600 font-medium">High Confidence</div>
                        <div className="text-xl font-bold text-green-900">
                          {process.status.result.processing_stats.high_confidence_detections}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Detected Text */}
                  {process.status.result.detected_symbols && process.status.result.detected_symbols.length > 0 && (
                    <div className="mb-4">
                      <h5 className="text-sm font-semibold text-gray-800 mb-2">
                        Detected Text ({process.status.result.detected_symbols.length} items)
                      </h5>
                      <div className="bg-gray-50 rounded p-3 max-h-32 overflow-y-auto">
                        {process.status.result.detected_symbols.map((symbol: any, index: number) => (
                          <div key={index} className="flex justify-between py-1">
                            <span className="text-sm font-medium">{symbol.text}</span>
                            <span className="text-xs text-gray-500">
                              {(symbol.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Image */}
                  {process.status.result.marked_image && (
                    <div className="mb-4">
                      <h5 className="text-sm font-semibold text-gray-800 mb-2">
                        Processed Image
                      </h5>
                      <div className="relative max-w-full">
                        <Image
                          src={`data:image/jpeg;base64,${process.status.result.marked_image}`}
                          alt="OCR Results"
                          width={600}
                          height={400}
                          className="rounded border shadow-sm w-full h-auto"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
