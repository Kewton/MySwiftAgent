# mySwiftAgentCore Dockerfile
# Multi-stage build for production-ready TypeScript service

# ==========================================
# Stage 1: Build
# ==========================================
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including dev)
RUN npm ci

# Copy source code
COPY tsconfig.json ./
COPY src/ ./src/

# Build TypeScript
RUN npm run build

# ==========================================
# Stage 2: Production
# ==========================================
FROM node:20-slim AS production

WORKDIR /app

# Create non-root user
RUN groupadd -r myswiftagent && useradd -r -g myswiftagent myswiftagent

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --omit=dev && npm cache clean --force

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Set ownership
RUN chown -R myswiftagent:myswiftagent /app

# Switch to non-root user
USER myswiftagent

# Environment variables
ENV NODE_ENV=production
ENV PORT=8006
ENV HOST=0.0.0.0

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8006/health || exit 1

# Start the service
CMD ["node", "dist/index.js"]
