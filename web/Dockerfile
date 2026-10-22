# ThinkAlgo OJ -- image frontend Next.js (standalone).
#
# Build context PHẢI là web/ (docker build web/), không phải gốc repo: gốc repo có
# package.json của Django/websocket nên Next.js sẽ suy ra gốc theo dõi sai và lồng
# server.js vào thư mục con. Build trên CI (GitHub Actions), không build trên server.
FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-bookworm-slim AS run
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    # Docker tự gán HOSTNAME là id container; Next.js dùng biến này để chọn địa chỉ nghe.
    HOSTNAME=127.0.0.1 \
    NODE_OPTIONS=--max-old-space-size=256
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/web-healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "server.js"]
