# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build the application
# We use a build argument for VITE_API_URL so it can be baked into the client code
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build
RUN npm prune --production

# Run stage
FROM node:20-alpine AS runner

WORKDIR /app

# Copy built assets and production dependencies
COPY --from=builder /app/build build/
COPY --from=builder /app/node_modules node_modules/
COPY package.json .

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000
# The server can also respect ORIGIN if behind a proxy
ENV ORIGIN=http://localhost:3000

CMD ["node", "build"]
