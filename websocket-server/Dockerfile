# Use Node.js 22 to match local environment
FROM node:22

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including devDependencies)
RUN npm install --include=dev

# Install ts-node and typescript globally
RUN npm install -g ts-node typescript

# Copy source code
COPY . .

# Build the TypeScript code
RUN npx tsc --outDir dist

# Expose port
EXPOSE 8001

# Start the server
CMD ["node", "dist/server.js"]
