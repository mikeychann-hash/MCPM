# Use official Node.js runtime
FROM node:20-alpine AS base
WORKDIR /app

# Install dependencies and build
FROM base AS builder
COPY package.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

# Production image
FROM node:20-alpine AS runner
ENV NODE_ENV=production
WORKDIR /app
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.mjs ./next.config.mjs

EXPOSE 3000
CMD ["npm", "run", "start"]
