# ── Build stage ────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (better layer caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Bake the API URL into the client bundle via build argument
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build
RUN npm prune --production

# ── Run stage ─────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runner

WORKDIR /app

# Run as non-root user for security
RUN adduser --disabled-password --no-create-home appuser

# Copy built assets and production dependencies
COPY --from=builder --chown=appuser:appuser /app/build build/
COPY --from=builder --chown=appuser:appuser /app/node_modules node_modules/
COPY --from=builder --chown=appuser:appuser /app/package.json .

USER appuser

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000
ENV ORIGIN=http://localhost:3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:3000/ || exit 1

CMD ["node", "build"]
