'use client';

import { useState, useEffect } from 'react';
import { useSocket } from '@/hooks/useSocket';

interface BatchStatus {
  batch_id: string;
  status: string;
  progress: number;
  messages: string[];
  created_at: string;
  updated_at: string;
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
  
  const { isConnected, subscribeToProcess, unsubscribeFromProcess, batchProgressMap, error } = useSocket();

  useEffect(() => {
    batchProgressMap.forEach((progress, batchId) => {
      setActiveProcesses(prev => {
        const newMap = new Map(prev);
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
        
        return newMap;
      });
    });
  }, [batchProgressMap]);

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
      setActiveProcesses(prev => {
        const newMap = new Map(prev);
        newMap.set(data.batch_id, {
          batchId: data.batch_id,
          status: {
            batch_id: data.batch_id,
            status: 'initialized',
            progress: 0,
            messages: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          },
          isActive: true
        });
        return newMap;
      });
      
      subscribeToProcess(data.batch_id);
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
            <h2 className="text-xl font-semibold mb-4">Start New Process</h2>
            
            <button
              onClick={startProcess}
              disabled={!isConnected}
              className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded transition-colors"
            >
              Start New Long Process
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
