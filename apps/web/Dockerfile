FROM node:20-alpine AS build
WORKDIR /app

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN corepack enable

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/api-contracts ./packages/api-contracts
COPY apps/web ./apps/web

RUN pnpm install --frozen-lockfile
RUN pnpm --filter @chat-analyzer/web build

FROM nginx:1.27-alpine
ENV NGINX_CLIENT_MAX_BODY_SIZE=100m
COPY infra/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80
CMD ["/bin/sh", "-c", "printf 'window.__CHAT_ANALYZER_API_BASE_URL__ = \"%s\";\\n' \"${VITE_API_BASE_URL:-/api}\" > /usr/share/nginx/html/runtime-config.js; nginx -g 'daemon off;'"]
