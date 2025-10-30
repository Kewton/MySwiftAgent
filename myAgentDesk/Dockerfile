# ========================================
# Stage 1: Build Stage
# ========================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source code
COPY . .

# Build the SvelteKit application
RUN npm run build

# ========================================
# Stage 2: Production Stage
# ========================================
FROM node:20-alpine

WORKDIR /app

# Copy built application from builder stage
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./

# Install only production dependencies
RUN npm ci --only=production

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S sveltekit -u 1001 && \
    chown -R sveltekit:nodejs /app

USER sveltekit

# Expose port (default 8000, can be overridden by environment variable)
ENV PORT=8000
ENV HOST=0.0.0.0
ENV NODE_ENV=production

EXPOSE 8000

# Health check (requires health endpoint to be implemented)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:8000/health', (r) => { process.exit(r.statusCode === 200 ? 0 : 1); })"

# Start the application
CMD ["node", "build/index.js"]
