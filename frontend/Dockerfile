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

# Set build-time environment variables
ARG NEXT_PUBLIC_PUSHER_APP_KEY
ARG NEXT_PUBLIC_PUSHER_CLUSTER
ARG NEXT_PUBLIC_PUSHER_USE_TLS
ARG NEXT_PUBLIC_API_URL

# Make them available as environment variables
ENV NEXT_PUBLIC_PUSHER_APP_KEY=$NEXT_PUBLIC_PUSHER_APP_KEY
ENV NEXT_PUBLIC_PUSHER_CLUSTER=$NEXT_PUBLIC_PUSHER_CLUSTER
ENV NEXT_PUBLIC_PUSHER_USE_TLS=$NEXT_PUBLIC_PUSHER_USE_TLS
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the Next.js application with ESLint disabled
RUN npm run build -- --no-lint

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
