type IconProps = { className?: string }

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

export function NimIcon({ className }: IconProps) {
  // Stylised chip/die — a GPU-served endpoint.
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
      <rect x="4.6" y="4.6" width="6.8" height="6.8" rx="1.4" />
      <path d="M6.6 2.4v2.2M9.4 2.4v2.2M6.6 11.4v2.2M9.4 11.4v2.2M2.4 6.6h2.2M2.4 9.4h2.2M11.4 6.6h2.2M11.4 9.4h2.2" />
    </svg>
  )
}
