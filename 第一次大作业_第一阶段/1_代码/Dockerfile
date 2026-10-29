FROM node:24-alpine AS web
WORKDIR /web
RUN corepack enable && corepack prepare pnpm@11.25.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

FROM python:3.12-slim
WORKDIR /srv
COPY backend/ /srv/backend/
COPY database/ /srv/database/
RUN pip install --no-cache-dir -r /srv/backend/requirements-lock.txt && pip install --no-cache-dir --no-deps /srv/backend
COPY --from=web /web/dist /srv/frontend/dist
WORKDIR /srv/backend
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
