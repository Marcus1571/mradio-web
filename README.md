# mradio-web

A self-hosted, multi-user internet radio player for the browser — pick a
station, see what's playing, and get AI-generated liner notes about the
artist and track while it plays.

Full rewrite of the terminal app [mradio](https://github.com/Marcus1571/mradio)
as a standalone web app, not a wrapper around it: playback happens in the
browser's own `<audio>` element (there's no server-side speaker to play
into), and the backend proxies each station's stream so HTTP-only stations
still work from an HTTPS page.

## What it does

- **Play any station** from a curated list (classical, jazz, blues,
  country, rock, pop, focus, chill, funk) or your own stream URL, with up
  to 12 favorite slots per person.
- **Live now-playing** — artist/track parsed straight off the station's
  ICY metadata, pushed to the browser over a WebSocket as it changes.
- **AI liner notes** — a short, factual write-up about the piece and its
  composer/artist, generated on the fly and cached (shared across
  everyone, so the same track is never re-queried twice) via opencode,
  Ollama, or any OpenAI-compatible endpoint (e.g. NVIDIA NIM).
- **Multiple accounts**, each with their own favorites and provider
  choice — admin-created, no public sign-up, matching a small
  self-hosted deployment for family/friends rather than a public service.
- **Admin analytics dashboard** — who's listening right now and from
  where (a live world map), plus full play history and stats on the most
  popular stations, genres, and listeners.

## Stack

- Backend: FastAPI (Python, async)
- Frontend: React + TypeScript (Vite), plain CSS with design tokens
- SQLite for accounts/sessions; per-user JSON for favorites/config,
  matching mradio's own file format
- Single container: one FastAPI process serves the API, the WebSocket,
  and the built frontend, all on one port

## Footprint

Measured against a live deployment (Chromium via Playwright, logged in, a
station playing, AI liner notes in flight):

- **~9.5 MB JS heap**, flat over a 20s window — no leak, no growth.
- **~0.86% of one CPU core** sustained while streaming audio and holding
  the now-playing WebSocket open.
- **134 DOM nodes**, **~215 KB JS + ~21 KB CSS** shipped (gzipped: ~67 KB /
  ~4 KB) — one bundle, no framework bloat.
- Audio decoding is offloaded entirely to the browser's native `<audio>`
  element — nothing here is a custom JS audio pipeline.

Server side, the container itself runs at **under 1% CPU and ~500 MB RAM**
on a 64 GB host — negligible next to whatever else you're already running
on it.

## Layout

- `backend/` — FastAPI app
- `frontend/` — Vite + React + TypeScript app
- `Dockerfile` — multi-stage build producing one image/one port

## Getting started

See [`KB.md`](KB.md) for the full deployment reference: building and
running with Docker Compose, the reverse-proxy setup (websockets +
streaming need two non-default settings), first login, managing
accounts, and configuring each AI provider.
