# One image: the review UI is built in a Node stage and shipped inside the Python package.
FROM node:24-slim AS ui
WORKDIR /app/ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src/ src/
COPY --from=ui /app/src/citefield/web src/citefield/web
RUN uv sync --locked --no-dev
ENV PATH=/app/.venv/bin:$PATH CITEFIELD_DATA=/data
VOLUME /data
EXPOSE 8484
# 0.0.0.0 inside the container only; compose publishes the port on the host's localhost (v1 has no login)
CMD ["citefield", "serve", "--host", "0.0.0.0", "--port", "8484"]
