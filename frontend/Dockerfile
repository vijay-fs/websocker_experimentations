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

# Build the Next.js application with ESLint disabled
RUN npm run build -- --no-lint

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
