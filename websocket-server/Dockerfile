# Use Node.js 22 to match local environment
FROM node:22

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Use ts-node directly instead of building
EXPOSE 8001

# Start the server with ts-node
CMD ["npx", "ts-node", "src/server.ts"]
