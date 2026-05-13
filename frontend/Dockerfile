# Multi-stage build for development
FROM node:18-alpine AS base

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Development stage
FROM base AS development
CMD ["npm", "run", "dev"]
