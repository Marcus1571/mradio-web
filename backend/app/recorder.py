"""Admin-only track recorder. When armed for a player session (`sid`), the
stream proxy hands each demuxed audio chunk and any ICY title change to a
Recorder, which cuts the MP3 into one file per track and writes ID3 tags
(artist/title from the ICY title, station as album).

Only the audio *between* two title changes is kept: the first track after
arming (joined mid-song) and the last one (cut off by stop/disconnect) are
discarded, so every saved file is a whole song. Raw MP3 bytes are written
as-is — no ffmpeg, no re-encode — so this only works for MP3 streams with
ICY metadata (stream.py decides that and registers it in STREAMS)."""

import re
import uuid
from pathlib import Path

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1
from mutagen.mp3 import MP3

from .db import DATA_DIR

# Shorter than this is a jingle/ad/station-ID that changed the title, not a track.
MIN_SECONDS = 30

# sid -> {"user_id", "gen", "recordable"}: live proxied streams, set by stream.py.
STREAMS: dict[str, dict] = {}
# sids the admin has switched recording on for.
ARMED: set[str] = set()


def rec_dir(user_id: int) -> Path:
    d = DATA_DIR / "users" / str(user_id) / "recordings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .")[:120] or "track"


def parse_kbps(icy_br: str | None) -> int:
    m = re.match(r"\d+", icy_br or "")
    return int(m.group()) if m and int(m.group()) > 0 else 128


class Recorder:
    # ponytail: blocking file I/O on the event loop (small sequential writes
    # of already-buffered chunks) and the chunk that carries a title change is
    # written whole to the new track, so a cut can be off by up to one chunk
    # (~0.5s). Move to a thread / split on the metadata boundary if it matters.
    def __init__(self, user_id: int, station: str, kbps: int):
        self.dir = rec_dir(user_id)
        self.station = station
        self.kbps = kbps
        self.title: str | None = None
        self.saved = 0
        self._f = None
        self._part: Path | None = None
        self._bytes = 0

    def feed(self, audio: bytes, title: str | None) -> bool:
        """True if a finished track was saved by this call."""
        saved = False
        if title:
            saved = self._finish()
            self.title = title
            self._part = self.dir / f".{uuid.uuid4().hex}.part"
            self._f = open(self._part, "wb")
            self._bytes = 0
        if self._f and audio:
            self._f.write(audio)
            self._bytes += len(audio)
        return saved

    def discard(self) -> None:
        """Drop the in-progress (partial) track."""
        if self._f:
            self._f.close()
            self._part.unlink(missing_ok=True)
        self._f = self._part = self.title = None

    def _finish(self) -> bool:
        if not self._f:
            return False
        self._f.close()
        part, title = self._part, self.title
        self._f = self._part = None
        if self._bytes * 8 / (self.kbps * 1000) < MIN_SECONDS:
            part.unlink(missing_ok=True)
            return False
        artist, sep, track = title.partition(" - ")
        if not sep:
            artist, track = "", title
        try:
            tags = ID3(part)
        except ID3NoHeaderError:
            tags = ID3()
        tags.add(TIT2(encoding=3, text=track))
        if artist:
            tags.add(TPE1(encoding=3, text=artist))
        if self.station:
            tags.add(TALB(encoding=3, text=self.station))
        tags.save(part)
        final = self.dir / f"{_safe(title)}.mp3"
        n = 2
        while final.exists():
            final = self.dir / f"{_safe(title)} ({n}).mp3"
            n += 1
        part.rename(final)
        self.saved += 1
        return True


def list_recordings(user_id: int) -> list[dict]:
    out = []
    for p in sorted(rec_dir(user_id).glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True):
        item = {"name": p.name, "size": p.stat().st_size, "mtime": p.stat().st_mtime,
                "title": p.stem, "artist": "", "station": "", "seconds": 0}
        try:
            m = MP3(p)
            item["seconds"] = int(m.info.length)
            if m.tags:
                for key, field in (("TIT2", "title"), ("TPE1", "artist"), ("TALB", "station")):
                    if key in m.tags:
                        item[field] = str(m.tags[key])
        except Exception:
            pass
        out.append(item)
    return out
