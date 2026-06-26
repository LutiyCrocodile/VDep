# Multi-stage build (dev + prod)
# Build context: repo root (../../ relative to docker-compose.yml)
# This allows COPY of both frontend/ and shared/ directories
FROM node:18-alpine AS base
WORKDIR /app
COPY frontend/package.json ./
RUN npm install

# ── Development ──────────────────────────────────────────────────────────────
FROM base AS development
COPY frontend/ .
COPY shared/ /shared
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]

# ── Production builder ────────────────────────────────────────────────────────
FROM base AS builder
# Build-time public URLs (embedded into JS bundle by Next.js)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_VIDEO_API_URL=http://localhost:8001
ARG NEXT_PUBLIC_STREAMING_API_URL=http://localhost:8002
ARG NEXT_PUBLIC_NOTIFICATION_API_URL=http://localhost:8003
ARG NEXT_PUBLIC_SEARCH_API_URL=http://localhost:8004
ARG NEXT_PUBLIC_HLS_PUBLIC_BASE=http://localhost:8888
ARG NEXT_PUBLIC_RTMP_HOST=localhost
ARG NEXT_PUBLIC_PORTAL_URL=http://localhost:3002
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_VIDEO_API_URL=$NEXT_PUBLIC_VIDEO_API_URL
ENV NEXT_PUBLIC_STREAMING_API_URL=$NEXT_PUBLIC_STREAMING_API_URL
ENV NEXT_PUBLIC_NOTIFICATION_API_URL=$NEXT_PUBLIC_NOTIFICATION_API_URL
ENV NEXT_PUBLIC_SEARCH_API_URL=$NEXT_PUBLIC_SEARCH_API_URL
ENV NEXT_PUBLIC_HLS_PUBLIC_BASE=$NEXT_PUBLIC_HLS_PUBLIC_BASE
ENV NEXT_PUBLIC_RTMP_HOST=$NEXT_PUBLIC_RTMP_HOST
ENV NEXT_PUBLIC_PORTAL_URL=$NEXT_PUBLIC_PORTAL_URL
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/ .
COPY shared/ /shared
RUN npm run build

# ── Production runner ─────────────────────────────────────────────────────────
FROM node:18-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["npm", "start"]
