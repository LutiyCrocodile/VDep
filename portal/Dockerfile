# Multi-stage build for production (context: repo root)
FROM node:18-alpine AS base

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY portal/package.json ./
RUN npm install

FROM base AS builder
WORKDIR /app
ARG AUTH_INTERNAL_URL=http://auth-service:8000
ARG NEXT_PUBLIC_AUTH_URL=http://localhost:8000
ARG NEXT_PUBLIC_VIDEO_URL=http://localhost:3000
ARG NEXT_PUBLIC_MESSENGER_URL=http://localhost:3005
ARG NEXT_PUBLIC_SUPPORT_URL=http://localhost:3004
ARG NEXT_PUBLIC_DASHBOARD_URL=http://localhost:5173
ENV AUTH_INTERNAL_URL=$AUTH_INTERNAL_URL
ENV NEXT_PUBLIC_AUTH_URL=$NEXT_PUBLIC_AUTH_URL
ENV NEXT_PUBLIC_VIDEO_URL=$NEXT_PUBLIC_VIDEO_URL
ENV NEXT_PUBLIC_MESSENGER_URL=$NEXT_PUBLIC_MESSENGER_URL
ENV NEXT_PUBLIC_SUPPORT_URL=$NEXT_PUBLIC_SUPPORT_URL
ENV NEXT_PUBLIC_DASHBOARD_URL=$NEXT_PUBLIC_DASHBOARD_URL
COPY --from=deps /app/node_modules ./node_modules
COPY portal/ .
COPY shared/ /shared
RUN npm run build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

RUN mkdir .next
RUN chown nextjs:nodejs .next

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3001

ENV PORT 3001
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
