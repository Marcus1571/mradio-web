export type IconProps = { className?: string }

export function PlayIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="currentColor">
      <path d="M4 2.5v11l10-5.5Z" />
    </svg>
  )
}

export function PauseIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="currentColor">
      <rect x="3" y="2" width="4" height="12" rx="1" />
      <rect x="9" y="2" width="4" height="12" rx="1" />
    </svg>
  )
}

export function StopIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="currentColor">
      <rect x="3" y="3" width="10" height="10" rx="1" />
    </svg>
  )
}

export function VolumeIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M2 6h2.5L8 3.3v9.4L4.5 10H2Z" />
      <path d="M10.5 6a3 3 0 0 1 0 4" />
    </svg>
  )
}

export function MuteIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M2 6h2.5L8 3.3v9.4L4.5 10H2Z" />
      <path d="M11 5.5 14.5 9M14.5 5.5 11 9" />
    </svg>
  )
}

export function RefreshIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2v3.5H10" />
    </svg>
  )
}

export function SparkleIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M8 1.5 9.6 5.9 14 7l-4.4 1.1L8 12.5 6.4 8.1 2 7l4.4-1.1Z" />
    </svg>
  )
}

export function ExternalLinkIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M6 4h6v6M12 4 4 12" />
    </svg>
  )
}

export function StarIcon({ className, filled }: IconProps & { filled?: boolean }) {
  return (
    <svg
      className={className}
      viewBox="0 0 16 16"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="1.3"
    >
      <path d="M8 1.5l1.9 4 4.4.6-3.2 3 .8 4.4L8 11.4l-3.9 2.1.8-4.4-3.2-3 4.4-.6Z" />
    </svg>
  )
}

export function TrashIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M3 4.5h10M6 4.5V3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1.5M4.5 4.5 5 13a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1l.5-8.5" />
    </svg>
  )
}

export function PencilIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M10.5 2.5 13.5 5.5 5 14 2 14.5 2.5 11.5Z" strokeLinejoin="round" />
      <path d="M9 4l3 3" />
    </svg>
  )
}

export function CheckIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 8.5 6.5 12 13 4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function XIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
    </svg>
  )
}

export function SunIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1v1.5M8 13.5V15M15 8h-1.5M2.5 8H1M12.7 3.3l-1 1M4.3 11.7l-1 1M12.7 12.7l-1-1M4.3 4.3l-1-1" />
    </svg>
  )
}

export function MoonIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M13.5 9.5A5.8 5.8 0 0 1 6.5 2.5a5.8 5.8 0 1 0 7 7Z" />
    </svg>
  )
}

export function ChevronDownIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M4 6l4 4 4-4" />
    </svg>
  )
}

export function MoveIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M8 2v12M2 8h12M4 5 2 8l2 3M12 5l2 3-2 3M5 4l3-2 3 2M5 12l3 2 3-2" />
    </svg>
  )
}

/* ---------- AI provider marks ----------
   Same monoline language as the icons above (16x16, 1.4 stroke,
   currentColor) so they sit as quiet marks beside a heading rather
   than as pasted-in brand assets — and so they inherit the page's ink
   and adapt to dark mode for free. Suggestive of each provider's
   identity, deliberately not reproductions of trademarked logos. */

export function ChatGPTIcon({ className }: IconProps) {
  // Interlocking hexagonal knot, echoing OpenAI's woven motif.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M8 2.2 12.4 4.7v5L8 12.2 3.6 9.7v-5Z" />
      <path d="M8 7.1 12.4 4.7M8 7.1v5.1M8 7.1 3.6 4.7" />
    </svg>
  )
}

export function OpenCodeIcon({ className }: IconProps) {
  // Angle brackets around a caret — a terminal/code agent.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M5.3 4.4 2.2 8l3.1 3.6M10.7 4.4 13.8 8l-3.1 3.6" />
      <path d="M9.2 3.4 6.8 12.6" />
    </svg>
  )
}

export function GeminiIcon({ className }: IconProps) {
  // Asymmetric faceted diamond, echoing Gemini's own mark — distinct
  // from SparkleIcon's symmetric 4-point star and GrokIcon's crossing
  // strokes.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M8 2c0 3.3 2.7 6 6 6-3.3 0-6 2.7-6 6 0-3.3-2.7-6-6-6 3.3 0 6-2.7 6-6Z" strokeLinejoin="round" />
    </svg>
  )
}

export function OpenRouterIcon({ className }: IconProps) {
  // Three paths converging into one node, echoing "routing" — distinct
  // from GeminiIcon's diamond and NimIcon's/OpenCodeIcon's marks.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <circle cx="8" cy="8" r="1.6" />
      <path d="M8 6.4V2.5M8 9.6V13.5M6.6 8.8 3.2 11.3M9.4 8.8l3.4 2.5M6.6 7.2 3.2 4.7M9.4 7.2l3.4-2.5" strokeLinecap="round" />
    </svg>
  )
}

export function MistralIcon({ className }: IconProps) {
  // A wind/gust motif (three curved swoops), echoing "Mistral" the wind —
  // distinct from OpenRouterIcon's converging paths and GeminiIcon's diamond.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M2.5 5.5h8.2a1.8 1.8 0 1 0-1.5-2.8" strokeLinecap="round" />
      <path d="M2.5 8h10.4a1.8 1.8 0 1 1-1.5 2.8" strokeLinecap="round" />
      <path d="M2.5 10.5h6.2a1.8 1.8 0 1 0-1.5 2.8" strokeLinecap="round" />
    </svg>
  )
}

export function OllamaIcon({ className }: IconProps) {
  // A llama silhouette abstracted to two ears and a muzzle.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M5.8 6.6V4l1.3 1.3M10.2 6.6V4L8.9 5.3" />
      <path d="M5.8 6.6h4.4v3.2a2.2 2.2 0 0 1-4.4 0Z" />
      <path d="M7.2 12v1.6M8.8 12v1.6" />
    </svg>
  )
}

export function GrokIcon({ className }: IconProps) {
  // Two crossing angular strokes, echoing xAI's own mark — distinct from
  // SparkleIcon's 4-point star (used elsewhere for AI liner notes).
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M3 3 8 8M13 3 8 8M8 8 3 13M8 8l5 5" strokeLinecap="round" />
    </svg>
  )
}

export function NimIcon({ className }: IconProps) {
  // Stylised chip/die — a GPU-served endpoint.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <rect x="4.6" y="4.6" width="6.8" height="6.8" rx="1.4" />
      <path d="M6.6 2.4v2.2M9.4 2.4v2.2M6.6 11.4v2.2M9.4 11.4v2.2M2.4 6.6h2.2M2.4 9.4h2.2M11.4 6.6h2.2M11.4 9.4h2.2" />
    </svg>
  )
}

export function DahlIcon({ className }: IconProps) {
  // A capital D with a diagonal slash — distinctive, simple, and
  // deliberately different from all other provider marks here.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M10.5 2.5v11" strokeLinecap="round" />
      <path d="M4.5 3.5h6a4 4 0 0 1 0 8h-6" />
      <path d="M4.5 13.5l8-3" strokeLinecap="round" />
    </svg>
  )
}

export function SpotifyIcon({ className }: IconProps) {
  // Real Spotify mark (solid green circle, three white sound-wave bars) —
  // path data from the official icon, via Wikimedia Commons
  // (File:Spotify_logo_without_text.svg). Not currentColor: this is a
  // recognizable brand mark, meant to render in Spotify's real green
  // regardless of surrounding text color.
  return (
    <svg className={className} viewBox="0 0 168 168" fill="none">
      <path
        fill="#1ED760"
        d="m83.996 0.277c-46.249 0-83.743 37.493-83.743 83.742 0 46.251 37.494 83.741 83.743 83.741 46.254 0 83.744-37.49 83.744-83.741 0-46.246-37.49-83.738-83.745-83.738l0.001-0.004zm38.404 120.78c-1.5 2.46-4.72 3.24-7.18 1.73-19.662-12.01-44.414-14.73-73.564-8.07-2.809 0.64-5.609-1.12-6.249-3.93-0.643-2.81 1.11-5.61 3.926-6.25 31.9-7.291 59.263-4.15 81.337 9.34 2.46 1.51 3.24 4.72 1.73 7.18zm10.25-22.805c-1.89 3.075-5.91 4.045-8.98 2.155-22.51-13.839-56.823-17.846-83.448-9.764-3.453 1.043-7.1-0.903-8.148-4.35-1.04-3.453 0.907-7.093 4.354-8.143 30.413-9.228 68.222-4.758 94.072 11.127 3.07 1.89 4.04 5.91 2.15 8.976v-0.001zm0.88-23.744c-26.99-16.031-71.52-17.505-97.289-9.684-4.138 1.255-8.514-1.081-9.768-5.219-1.254-4.14 1.08-8.513 5.221-9.771 29.581-8.98 78.756-7.245 109.83 11.202 3.73 2.209 4.95 7.016 2.74 10.733-2.2 3.722-7.02 4.949-10.73 2.739z"
      />
    </svg>
  )
}

export function AppleMusicIcon({ className }: IconProps) {
  // Real Apple Music mark (rounded-square gradient with the musical-note
  // glyph) — path data isolated from the official app icon via Wikimedia
  // Commons (File:Apple_Music_icon.svg). Not currentColor, same reasoning
  // as SpotifyIcon/DeezerIcon above.
  return (
    <svg className={className} viewBox="0 0 1024 1024" fill="none">
      <defs>
        <linearGradient id="apple-music-gradient" x1="512" y1="0" x2="512" y2="1024" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#FA57C1" />
          <stop offset="1" stopColor="#FC3C44" />
        </linearGradient>
      </defs>
      <rect width="1024" height="1024" rx="228" fill="url(#apple-music-gradient)" />
      <path
        fill="#fff"
        d="M675.4 224.4c-8.6 1-90.5 16.6-99.6 18.6l-217.3 43.9-.3.1c-2.4.6-4.5 1.5-6.4 2.7a24.7 24.7 0 0 0-10.8 15.9c-.6 2.8-.6 2.1-.6 148.1v143.1l-.4.1c-11.2-2.1-24.4-1.3-35.6 2-27.5 8.2-46.5 30.3-49.2 57.2-.4 3.8-.4 12.1 0 15.8 3.5 33.4 33.5 58.5 68.6 57.5 5.5-.2 9.2-.6 14.4-1.7 26.7-5.6 47.9-25 54.3-49.7 2.4-9.4 2.2-3.6 2.2-113.9V464l1.3-.3c.7-.2 45.7-9.3 100-20.3l98.7-19.9 1.3-.3v157.7l-.5-.1c-6.4-1.2-16.7-1.6-23.9-.9-33.9 3.3-60.5 26.5-65.9 57.4-.9 5.3-.9 15.8 0 21.1 3.8 21.8 18.3 39.9 39.4 49.4 8.9 4 17.6 6.1 28.1 6.7 33.9 2 63.7-17.5 71.9-46.8 2.1-7.6 1.9-1.6 1.9-125.4V405.3c0-97.4-.1-114.2-.4-115.6a17 17 0 0 0-13-13.4c-2.1-.5-4.2-.6-6.2-.4z"
      />
    </svg>
  )
}

export function DeezerIcon({ className }: IconProps) {
  // Real Deezer mark (2023 rebrand: a purple heart formed from vertical
  // waveform ovals) — path data isolated from the official wordmark SVG
  // via Wikimedia Commons (File:Deezer_logo,_2023.svg), text portion
  // dropped. Not currentColor, same reasoning as SpotifyIcon above.
  return (
    <svg className={className} viewBox="0 0 49 49" fill="none">
      <path
        fill="#A238FF"
        d="M41.0955 7.32313C41.5396 4.74914 42.1912 3.13054 42.913 3.12744H42.9146C44.2606 3.13208 45.3517 8.7454 45.3517 15.6759C45.3517 22.6063 44.259 28.2243 42.9115 28.2243C42.3591 28.2243 41.8494 27.2704 41.4389 25.6719C40.7903 31.5233 39.4443 35.5459 37.8862 35.5459C36.6806 35.5459 35.5986 33.1296 34.8722 29.3188C34.3762 36.5662 33.1279 41.708 31.6689 41.708C30.7533 41.708 29.9185 39.6705 29.3005 36.3529C28.5573 43.2014 26.8405 48 24.8382 48C22.836 48 21.1162 43.2029 20.376 36.3529C19.7625 39.6705 18.9278 41.708 18.0075 41.708C16.5486 41.708 15.3033 36.5662 14.8043 29.3188C14.0779 33.1296 12.999 35.5459 11.7903 35.5459C10.2337 35.5459 8.88621 31.5249 8.23763 25.6719C7.83017 27.2751 7.31741 28.2243 6.76497 28.2243C5.41745 28.2243 4.32478 22.6063 4.32478 15.6759C4.32478 8.7454 5.41745 3.12744 6.76497 3.12744C7.48833 3.12744 8.13538 4.75068 8.58405 7.32313C9.30283 2.88473 10.4703 0 11.7903 0C13.3576 0 14.7158 4.07975 15.3583 10.0038C15.987 5.69216 16.9408 2.94348 18.0091 2.94348C19.5061 2.94348 20.7789 8.34964 21.2505 15.8908C22.1371 12.0243 23.4205 9.59876 24.8413 9.59876C26.2621 9.59876 27.5455 12.0259 28.4306 15.8908C28.9037 8.34964 30.1749 2.94348 31.672 2.94348C32.7387 2.94348 33.691 5.69216 34.3228 10.0038C34.9637 4.07975 36.3219 0 37.8892 0C39.2047 0 40.3767 2.88628 41.0955 7.32313ZM0.837891 14.4417C0.837891 11.3436 1.45748 8.83142 2.22204 8.83142C2.9866 8.83142 3.60619 11.3436 3.60619 14.4417C3.60619 17.5397 2.9866 20.0519 2.22204 20.0519C1.45748 20.0519 0.837891 17.5397 0.837891 14.4417ZM46.0693 14.4417C46.0693 11.3436 46.6888 8.83142 47.4534 8.83142C48.218 8.83142 48.8376 11.3436 48.8376 14.4417C48.8376 17.5397 48.218 20.0519 47.4534 20.0519C46.6888 20.0519 46.0693 17.5397 46.0693 14.4417Z"
      />
    </svg>
  )
}
