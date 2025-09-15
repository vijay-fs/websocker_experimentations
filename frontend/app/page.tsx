'use client';

import { useState, useEffect, useRef } from 'react';
import { useSocket } from '@/hooks/useSocket';

interface BatchStatus {
  batch_id: string;
  status: string;
  progress: number;
  messages: string[];
  created_at: string;
  updated_at: string;
  process_type?: string;
  parameters?: Record<string, any>;
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
  };
  error?: string;
}

interface ActiveProcess {
  batchId: string;
  status: BatchStatus;
  isActive: boolean;
}

export default function Home() {
  const [activeProcesses, setActiveProcesses] = useState<Map<string, ActiveProcess>>(new Map());
  const [checkBatchId, setCheckBatchId] = useState<string>('');
  const [manualBatchStatus, setManualBatchStatus] = useState<BatchStatus | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  
 const { 
    isConnected, 
    subscribeToProcess, 
    unsubscribeFromProcess, 
    batchProgressMap, 
    activeSubscriptions,
    error 
  } = useSocket();

 // Restore active processes from localStorage on page load
  useEffect(() => {
    const savedBatchIds = localStorage.getItem('activeBatchIds');
    if (savedBatchIds) {
      try {
        const batchIds = JSON.parse(savedBatchIds);
        if (Array.isArray(batchIds) && batchIds.length > 0) {
          batchIds.forEach(batchId => {
            // Fetch current status for each batch regardless of connection status
            // This ensures processes are displayed immediately after refresh
            fetch(`http://localhost:8000/api/batch-status/${batchId}`)
              .then(response => {
                if (response.ok) {
                  return response.json();
                }
                throw new Error('Batch not found');
              })
              .then(data => {
                // Update the process state immediately to show in UI
                setActiveProcesses(prev => {
                  const newMap = new Map(prev);
                  newMap.set(batchId, {
                    batchId: data.batch_id,
                    status: data,
                    isActive: data.progress < 100
                  });
                  return newMap;
                });
                
                // Subscribe to the batch if it's still active AND we're connected
                if (data.progress < 100 && isConnected) {
                  // Small delay to ensure WebSocket is ready
                  setTimeout(() => {
                    subscribeToProcess(batchId);
                  }, 100);
                }
              })
              .catch(error => {
                console.error(`Error fetching status for batch ${batchId}:`, error);
                // Remove invalid batch IDs from localStorage
                const updatedBatchIds = batchIds.filter((id: string) => id !== batchId);
                localStorage.setItem('activeBatchIds', JSON.stringify(updatedBatchIds));
              });
          });
        }
      } catch (error) {
        console.error('Error parsing saved batch IDs:', error);
      }
    }
  }, []); // Empty dependency array to run only once on mount

 // Handle WebSocket connection becoming available after mount
  useEffect(() => {
    if (isConnected) {
      // Resubscribe to all active processes when connection becomes available
      Array.from(activeProcesses.values()).forEach(process => {
        if (process.isActive && !activeSubscriptions.has(process.batchId)) {
          // Small delay to ensure WebSocket is ready
          setTimeout(() => {
            subscribeToProcess(process.batchId);
          }, 100);
        }
      });
    }
  }, [isConnected, activeProcesses, activeSubscriptions, subscribeToProcess]);

 // Save all batch IDs to localStorage (both active and completed)
  // Only active subscriptions are saved to activeSubscriptions
  useEffect(() => {
    // Get all batch IDs from current processes
    const allBatchIds = Array.from(activeProcesses.values()).map(p => p.batchId);
    if (allBatchIds.length > 0) {
      localStorage.setItem('activeBatchIds', JSON.stringify(allBatchIds));
    }
  }, [activeProcesses]);

 // Create a ref to track the last processed batch progress to prevent unnecessary updates
  const lastBatchProgressRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    let hasUpdates = false;
    const newMap = new Map(activeProcesses);
    
    batchProgressMap.forEach((progress, batchId) => {
      // Create a unique key for this progress update
      const progressKey = `${batchId}-${progress.timestamp}-${progress.progress}`;
      const lastProgressKey = lastBatchProgressRef.current.get(batchId);
      
      // Skip if we've already processed this exact progress update
      if (lastProgressKey === progressKey) {
        return;
      }
      
      hasUpdates = true;
      lastBatchProgressRef.current.set(batchId, progressKey);
      
      const existing = newMap.get(batchId);
      
      const updatedStatus: BatchStatus = {
        batch_id: batchId,
        status: progress.progress === 100 ? 'completed' : 'running',
        progress: progress.progress,
        messages: existing?.status.messages ? 
          [...existing.status.messages, progress.message] : 
          [progress.message],
        created_at: existing?.status.created_at || new Date().toISOString(),
        updated_at: progress.timestamp
      };
      
      newMap.set(batchId, {
        batchId,
        status: updatedStatus,
        isActive: progress.progress < 100
      });
    });
    
    // Only update state if there were actual changes
    if (hasUpdates) {
      setActiveProcesses(newMap);
    }
  }, [batchProgressMap, activeProcesses]);

 // Keep all batch IDs in localStorage for visibility, but update active subscriptions
  // The activeSubscriptions useEffect will handle saving only active batch IDs

 const startProcess = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/start-process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          process_type: 'file_processing',
          parameters: { test: true }
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start process');
      }

      const data = await response.json();
      
      // Initialize the process in our state
      const initialStatus: BatchStatus = {
        batch_id: data.batch_id,
        status: 'initialized',
        progress: 0,
        messages: [],
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
      
      // Small delay to ensure WebSocket is ready before subscribing
      setTimeout(() => {
        subscribeToProcess(data.batch_id);
      }, 100);
    } catch (error) {
      console.error('Error starting process:', error);
    }
  };

  const checkBatchStatus = async () => {
    if (!checkBatchId) return;

    try {
      const response = await fetch(`http://localhost:8000/api/batch-status/${checkBatchId}`);
      
      if (!response.ok) {
        throw new Error('Batch not found');
      }

      const data = await response.json();
      setManualBatchStatus(data);
    } catch (error) {
      console.error('Error checking batch status:', error);
      setManualBatchStatus(null);
    }
  };

  const stopProcess = (batchId: string) => {
    unsubscribeFromProcess(batchId);
    setActiveProcesses(prev => {
      const newMap = new Map(prev);
      newMap.delete(batchId);
      return newMap;
    });
  };

  const getActiveProcessesArray = () => Array.from(activeProcesses.values());

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
      
      const response = await fetch('http://localhost:8000/api/upload-drawing', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload file');
      }

      const data = await response.json();
      setUploadStatus(`File uploaded successfully. Processing started with batch ID: ${data.batch_id}`);
      
      // Initialize the process in our state
      const initialStatus: BatchStatus = {
        batch_id: data.batch_id,
        status: 'initialized',
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
      
      // Small delay to ensure WebSocket is ready before subscribing
      setTimeout(() => {
        subscribeToProcess(data.batch_id);
      }, 100);
      
      // Clear the file input
      setSelectedFile(null);
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus('Error uploading file');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">WebSocket Process Monitor</h1>
        
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center gap-4 mb-4">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm">
              Socket.IO: {isConnected ? 'Connected' : 'Disconnected'}
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
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100"
              />
              <p className="mt-1 text-sm text-gray-500">
                Supported formats: JPG, PNG, BMP, TIFF
              </p>
            </div>
            
            <button
              onClick={handleUploadButtonClick}
              disabled={!selectedFile || !isConnected}
              className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded transition-colors"
            >
              Process Engineering Drawing
            </button>
          </div>
        </div>

        <div className="mb-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Or Start New Process</h2>
            
            <button
              onClick={startProcess}
              disabled={!isConnected}
              className="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded transition-colors"
            >
              Start New Long Process (Simulation)
            </button>
            
            <div className="mt-4 text-sm text-gray-600">
              Active Processes: {getActiveProcessesArray().filter(p => p.isActive).length} | 
              Completed: {getActiveProcessesArray().filter(p => !p.isActive).length}
            </div>
          </div>
        </div>

        <div className="grid gap-4 mb-6">
          <h2 className="text-xl font-semibold">Active & Recent Processes</h2>
          
          {getActiveProcessesArray().length === 0 && (
            <div className="bg-white rounded-lg shadow-md p-6 text-center text-gray-500">
              No processes started yet. Click "Start New Long Process" to begin.
            </div>
          )}
          
          {getActiveProcessesArray().map((process) => (
            <div 
              key={process.batchId} 
              className={`bg-white rounded-lg shadow-md p-6 border-l-4 ${
                process.isActive ? 'border-blue-500' : 'border-green-500'
              }`}
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold text-lg">
                    {process.isActive ? 'Processing' : 'Completed'} - {process.status.status}
                  </h3>
                  <p className="text-sm text-gray-600 font-mono">{process.batchId}</p>
                </div>
                <div className="flex gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    process.isActive ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                  }`}>
                    {process.isActive ? 'Running' : 'Completed'}
                  </span>
                  <button
                    onClick={() => stopProcess(process.batchId)}
                    className="bg-red-500 hover:bg-red-600 text-white font-medium py-1 px-3 rounded text-xs"
                  >
                    Remove
                  </button>
                </div>
              </div>
              
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span>Progress</span>
                  <span>{process.status.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all duration-300 ${
                      process.isActive ? 'bg-blue-600' : 'bg-green-600'
                    }`}
                    style={{ width: `${process.status.progress}%` }}
                  ></div>
                </div>
              </div>
              
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">Messages:</p>
                <div className="max-h-32 overflow-y-auto bg-gray-50 p-3 rounded text-sm space-y-1">
                  {process.status.messages.map((message, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="text-gray-400">•</span>
                      <span>{message}</span>
                    </div>
                  ))}
                  {process.status.messages.length === 0 && (
                    <span className="text-gray-400 italic">No messages yet...</span>
                  )}
                </div>
              </div>
              
              {/* Display processed image if available */}
              {process.status.result && process.status.result.marked_image && (
                <div className="mb-4">
                  <div className="flex justify-between items-center mb-2">
                    <p className="text-sm text-gray-600">Processed Image:</p>
                    <button 
                      className="text-xs bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded"
                      onClick={() => {
                        // Open image in a new tab/window
                        const imageUrl = `data:image/png;base64,${process.status.result!.marked_image}`;
                        const newWindow = window.open();
                        if (newWindow) {
                          newWindow.document.write(`<img src="${imageUrl}" style="max-width:100%;height:auto;" />`);
                          newWindow.document.close();
                        }
                      }}
                    >
                      View Full Size
                    </button>
                  </div>
                  <div className="border rounded p-2">
                    <img 
                      src={`data:image/png;base64,${process.status.result.marked_image}`} 
                      alt="Processed engineering drawing" 
                      className="max-w-full h-auto"
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      Symbols detected: {process.status.result.symbol_count}
                    </p>
                  </div>
                </div>
              )}
              
              <div className="text-xs text-gray-500 grid grid-cols-2 gap-4">
                <div>Started: {new Date(process.status.created_at).toLocaleString()}</div>
                <div>Updated: {new Date(process.status.updated_at).toLocaleString()}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Manual Batch Status Check</h2>
          
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={checkBatchId}
              onChange={(e) => setCheckBatchId(e.target.value)}
              placeholder="Enter Batch ID to check manually"
              className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
            />
            <button
              onClick={checkBatchStatus}
              disabled={!checkBatchId}
              className="bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded"
            >
              Check
            </button>
          </div>

          {manualBatchStatus && (
            <div className="space-y-3">
              <div>
                <p className="text-sm text-gray-600">Status:</p>
                <p className="font-medium">{manualBatchStatus.status}</p>
              </div>
              
              <div>
                <p className="text-sm text-gray-600">Progress:</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{ width: `${manualBatchStatus.progress}%` }}
                    ></div>
                  </div>
                  <span className="text-sm">{manualBatchStatus.progress}%</span>
                </div>
              </div>

              <div>
                <p className="text-sm text-gray-600">Messages:</p>
                <div className="max-h-32 overflow-y-auto bg-gray-50 p-2 rounded text-sm">
                  {manualBatchStatus.messages.map((message, index) => (
                    <div key={index} className="py-1">
                      {message}
                    </div>
                  ))}
                </div>
              </div>

              <div className="text-xs text-gray-500">
                <p>Created: {new Date(manualBatchStatus.created_at).toLocaleString()}</p>
                <p>Updated: {new Date(manualBatchStatus.updated_at).toLocaleString()}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
