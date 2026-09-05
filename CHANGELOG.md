# Changelog

## [0.1.3] - 2026-09-05

Fixed a real playback bug found right after deploying 0.1.2: stations could
get stuck showing "Connecting…" forever, even though audio played fine —
only clicking Reconnect fixed it.

- Root cause: the audio stream connection and the now-playing WebSocket are
  two independent requests with no ordering guarantee. If the stream's
  `station`/`title` events arrived before the WebSocket had finished
  connecting, they were silently dropped — pre-existing since the
  WebSocket was first built, but far more likely to show up over a real
  network (reverse proxy) than on localhost, which is why it went
  unnoticed until now.
- Fix: the backend now remembers the latest `station`/`title` event per
  player session and replays it immediately when the WebSocket connects,
  instead of dropping events sent to nobody.
- Added structured logging (`mradio.stream`, `mradio.nowplaying`,
  `mradio.ws` loggers) for connect/disconnect/publish/subscribe events, so
  this kind of issue is visible in `docker logs` instead of requiring code
  archaeology to diagnose.

## [0.1.2] - 2026-09-05

Four small UI/UX bugs found reviewing the live 0.1.1 deployment against the
original design mockup:

- Wikipedia link now uses `rel="noopener noreferrer"`.
- NIM provider fields prefill with NVIDIA's hosted endpoint and
  `minimaxai/minimax-m3` on new installs, instead of OpenAI defaults;
  KB.md gained the missing "how to get an API key" walkthrough, linked
  from the AI providers page.
- Genre tag no longer crowds the station name in the favorites grid.
- Now-playing panel gained a stream metadata row (bitrate, sample rate,
  format, buffer health, elapsed time) that was entirely missing before.

## [0.1.1] - 2026-09-05

Confirmed working end-to-end: first real `docker compose build && docker
compose up` (previously only tested piece-by-piece), deployed to LT behind
Nginx Proxy Manager, logged in, played a stream, got AI liner notes.

- No pre-release flag — this build is verified, not just built.
- README: added a measured "Footprint" section (client JS heap, CPU,
  bundle size, server-side container resource use) from profiling the
  live deployment.

## [0.1.0] - 2026-09-04

First fully working build of mradio-web — a self-hosted, multi-user
rewrite of mradio as a browser-based internet radio player.

- Multi-user accounts (SQLite), admin-created, no public sign-up
- Per-user favorites (12 slots) and settings, matching mradio's own file format
- Browser-native playback via a stream proxy (fixes HTTPS-page/HTTP-station blocking)
- Live now-playing over WebSocket, parsed from ICY metadata
- AI liner notes: opencode (bundled), Ollama, or any OpenAI-compatible
  endpoint (e.g. NVIDIA NIM) — shared cache, admin-managed credentials,
  per-user provider choice
- Single-container Docker deployment (see KB.md)

Marked pre-release: not yet verified with a real docker build/compose up
outside this build's own testing.
