import express, { Request, Response } from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';

const app = express();
const httpServer = createServer(app);

app.use(cors({
  origin: "http://localhost:3000",
  credentials: true
}));

const io = new Server(httpServer, {
  cors: {
    origin: "http://localhost:3000",
    methods: ["GET", "POST"],
    credentials: true
  }
});

interface BatchUpdate {
  type: string;
  batch_id: string;
  message: string;
  progress: number;
  timestamp: string;
}

const connectedClients = new Map<string, Set<string>>();

io.on('connection', (socket) => {
  console.log(`Client connected: ${socket.id}`);

 // Store the last time a client subscribed to a batch to prevent spam
  const subscriptionTimestamps = new Map<string, number>();

  socket.on('subscribe_to_batch', (batchId: string) => {
    const key = `${socket.id}:${batchId}`;
    const now = Date.now();
    const lastSubscribe = subscriptionTimestamps.get(key) || 0;
    
    // Prevent spam subscriptions (less than 100ms apart)
    if (now - lastSubscribe < 100) {
      return;
    }
    
    subscriptionTimestamps.set(key, now);
    console.log(`Client ${socket.id} subscribed to batch ${batchId}`);
    
    socket.join(`batch_${batchId}`);
    
    if (!connectedClients.has(batchId)) {
      connectedClients.set(batchId, new Set());
    }
    connectedClients.get(batchId)?.add(socket.id);
  });

  socket.on('unsubscribe_from_batch', (batchId: string) => {
    console.log(`Client ${socket.id} unsubscribed from batch ${batchId}`);
    
    socket.leave(`batch_${batchId}`);
    connectedClients.get(batchId)?.delete(socket.id);
    
    if (connectedClients.get(batchId)?.size === 0) {
      connectedClients.delete(batchId);
    }
  });

  socket.on('batch_update', (data: BatchUpdate) => {
    console.log(`Received batch update for ${data.batch_id}: ${data.message} (${data.progress}%)`);
    console.log(`Clients subscribed to batch_${data.batch_id}:`, connectedClients.get(data.batch_id)?.size || 0);
    
    const progressData = {
      batchId: data.batch_id,
      message: data.message,
      timestamp: data.timestamp,
      progress: data.progress
    };
    
    console.log(`Emitting batch_progress to room batch_${data.batch_id}:`, progressData);
    io.to(`batch_${data.batch_id}`).emit('batch_progress', progressData);
    console.log(`Broadcast completed for batch ${data.batch_id}`);
  });

  socket.on('disconnect', (reason) => {
    console.log(`Client disconnected: ${socket.id}, reason: ${reason}`);
    
    connectedClients.forEach((clients, batchId) => {
      if (clients.has(socket.id)) {
        clients.delete(socket.id);
        if (clients.size === 0) {
          connectedClients.delete(batchId);
        }
      }
    });
  });

  // Handle errors
  socket.on('error', (error) => {
    console.error(`Socket error for client ${socket.id}:`, error);
  });
});


app.get('/health', (_req: Request, res: Response) => {
  res.json({ 
    status: 'healthy', 
    connectedClients: connectedClients.size,
    timestamp: new Date().toISOString()
  });
});

app.get('/status', (_req: Request, res: Response) => {
  const status = {
    connectedClients: Array.from(connectedClients.entries()).map(([batchId, clients]) => ({
      batchId,
      clientCount: clients.size,
      clientIds: Array.from(clients)
    })),
    totalClients: io.engine.clientsCount,
    timestamp: new Date().toISOString()
  };
  
  res.json(status);
});

const PORT = process.env.PORT || 8001;

httpServer.listen(PORT, () => {
  console.log(`Socket.IO server running on port ${PORT}`);
  console.log(`Health check available at http://localhost:${PORT}/health`);
});
