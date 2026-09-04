"""ICY/Shoutcast metadata parsing.

The original mradio got "now playing" text from mpv's IPC socket, which
handled ICY framing internally. There's no mpv here — playback happens in
the browser's own <audio> element — so this reimplements the ICY protocol
directly: request the stream with `Icy-MetaData: 1`, the server replies
with an `icy-metaint: N` header, and the body becomes N bytes of audio,
one length byte (x16 = block size), that many bytes of
`StreamTitle='...';` text (null-padded), then N bytes of audio again,
repeating for the life of the connection.

A browser's <audio> element has no idea what ICY framing is — forwarding
the raw interleaved bytes would corrupt playback — so IcyDemuxer strips
the metadata blocks out and returns pure audio, surfacing title changes
separately."""

import re
from httpx import Headers

_TITLE_RE = re.compile(rb"StreamTitle='(.*?)';")


def parse_metaint(headers: Headers) -> int | None:
    v = headers.get("icy-metaint")
    if v is None:
        return None
    try:
        n = int(v)
    except ValueError:
        return None
    return n if n > 0 else None


def extract_title(metadata_block: bytes) -> str | None:
    m = _TITLE_RE.search(metadata_block)
    if not m or not m.group(1):
        return None
    try:
        return m.group(1).decode("utf-8")
    except UnicodeDecodeError:
        return m.group(1).decode("latin-1", "replace")


class IcyDemuxer:
    """Incremental ICY demultiplexer. Feed it upstream chunks in order via
    `feed()`; each call returns (audio_bytes, title_or_None) — the audio
    bytes to forward to the client this call, and a new StreamTitle if one
    was just completed and differs from the last one seen."""

    def __init__(self, metaint: int):
        self.metaint = metaint
        self._audio_left = metaint
        self._reading_length = True
        self._meta_needed = 0
        self._meta_buf = bytearray()
        self.last_title: str | None = None

    def feed(self, chunk: bytes) -> tuple[bytes, str | None]:
        out = bytearray()
        title = None
        i, n = 0, len(chunk)
        while i < n:
            if self._audio_left > 0:
                take = min(self._audio_left, n - i)
                out += chunk[i:i + take]
                i += take
                self._audio_left -= take
                continue
            if self._reading_length:
                length_byte = chunk[i]
                i += 1
                self._reading_length = False
                self._meta_needed = length_byte * 16
                if self._meta_needed == 0:
                    self._audio_left = self.metaint
                    self._reading_length = True
                continue
            take = min(self._meta_needed - len(self._meta_buf), n - i)
            self._meta_buf += chunk[i:i + take]
            i += take
            if len(self._meta_buf) >= self._meta_needed:
                t = extract_title(bytes(self._meta_buf))
                if t and t != self.last_title:
                    self.last_title = t
                    title = t
                self._meta_buf = bytearray()
                self._meta_needed = 0
                self._audio_left = self.metaint
                self._reading_length = True
        return bytes(out), title
