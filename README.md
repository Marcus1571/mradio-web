# mradio-web

Browser-based internet radio player. Full rewrite of the terminal app
[mradio](https://github.com/Marcus1571/mradio) as a standalone web app —
not a wrapper around the original.

- Backend: FastAPI (Python, async)
- Frontend: React + TypeScript (Vite), plain CSS with design tokens
- Real-time now-playing / AI liner-note updates over WebSocket
- Single container: FastAPI serves the API, WebSocket, and built frontend

## Layout

- `backend/` — FastAPI app
- `frontend/` — Vite + React + TypeScript app
- `Dockerfile` — multi-stage build producing one image/one port

See [`KB.md`](KB.md) for deployment (Docker Compose, reverse proxy setup),
first-login and account management, and configuring AI providers.
