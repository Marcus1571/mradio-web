FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# opencode is a self-contained native binary distributed via npm (Bun-compiled;
# no Node.js needed at runtime, only to fetch it here). Version is pinned, not
# @latest, so builds stay reproducible — .github/workflows/bump-opencode.yml
# opens a PR when a newer release is published, instead of the image silently
# changing between builds.
FROM node:22-slim AS opencode-build
ARG OPENCODE_VERSION=1.18.28
RUN npm install --global opencode-ai@${OPENCODE_VERSION}

# OpenAI's official Codex CLI — same "real trusted binary" reasoning as
# opencode above, but for a different problem: auth.openai.com's OAuth
# device-code endpoint sits behind a Cloudflare bot/TLS-fingerprint
# challenge that flatly rejects plain HTTP clients (curl, httpx), even
# with realistic headers — confirmed live during development. The real
# CLI passes it because it's a genuine, trusted client; this app only
# uses it to perform `codex login --device-auth` (see codex_oauth.py),
# not to run any agent/coding features. `npm install @openai/codex`
# resolves the correct platform-specific binary automatically via
# optionalDependencies (confirmed: it's the same package, tagged per
# platform, e.g. @openai/codex@<version>-linux-x64) — no separate
# package name needed. Version pinned for the same reproducibility
# reason as opencode above.
FROM node:22-slim AS codex-build
ARG CODEX_VERSION=0.153.4
RUN npm install --global @openai/codex@${CODEX_VERSION}

FROM python:3.11-slim AS backend
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend-build /frontend/dist ./static
COPY --from=opencode-build /usr/local/lib/node_modules/opencode-ai/bin/opencode.exe /usr/local/bin/opencode
COPY --from=codex-build /usr/local/bin/node /usr/local/bin/node
COPY --from=codex-build /usr/local/lib/node_modules/@openai /usr/local/lib/node_modules/@openai
RUN ln -s /usr/local/lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex

# GeoLite2-City powers the admin analytics map (backend/app/geoip.py).
# Pulled from a redistribution mirror (MIT-licensed repackaging of
# MaxMind's own CC-BY-SA data) so no MaxMind account/license key is
# needed. Refreshed whenever the image is rebuilt — see KB.md.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -fsSL -o GeoLite2-City.mmdb \
       https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
