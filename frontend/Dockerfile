# Use Node.js 22 to match local environment
FROM node:22

# Set build-time environment variables
ARG NEXT_PUBLIC_PUSHER_APP_KEY
ARG NEXT_PUBLIC_PUSHER_HOST
ARG NEXT_PUBLIC_PUSHER_PORT
ARG NEXT_PUBLIC_PUSHER_SCHEME
ARG NEXT_PUBLIC_API_URL

# Make them available as environment variables
ENV NEXT_PUBLIC_PUSHER_APP_KEY=$NEXT_PUBLIC_PUSHER_APP_KEY
ENV NEXT_PUBLIC_PUSHER_HOST=$NEXT_PUBLIC_PUSHER_HOST
ENV NEXT_PUBLIC_PUSHER_PORT=$NEXT_PUBLIC_PUSHER_PORT
ENV NEXT_PUBLIC_PUSHER_SCHEME=$NEXT_PUBLIC_PUSHER_SCHEME
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

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
