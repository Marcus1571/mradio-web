export function formatElapsed(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}

export function formatKbps(bitrate: string | null): string | null {
  return bitrate ? `${bitrate} kbps` : null
}

export function formatKHz(sampleRate: string | null): string | null {
  const n = Number(sampleRate)
  return sampleRate && !Number.isNaN(n) ? `${(n / 1000).toFixed(1)} kHz` : null
}

export function formatCache(seconds: number): string {
  return `cache ${seconds.toFixed(1)}s`
}
