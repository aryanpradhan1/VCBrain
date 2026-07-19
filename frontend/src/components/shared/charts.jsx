import { motion } from "motion/react"

import { cn } from "@/lib/utils"

// ── TAM / SAM / SOM — nested proportional circles ─────────────────────────
// Magnitude at three nested scopes → sequential single hue, light→dark,
// every circle direct-labeled (satisfies the palette contrast relief rule).
const tiers = [
  { key: "tam", label: "TAM", fill: "#e0f2fe", text: "#0c4a6e" },
  { key: "sam", label: "SAM", fill: "#7dd3fc", text: "#0c4a6e" },
  { key: "som", label: "SOM", fill: "#0284c7", text: "#ffffff" },
]

export function MarketChart({ market, className }) {
  if (!market) return null
  if (![market.tam, market.sam, market.som].every((value) => Number.isFinite(value) && value > 0)) {
    return (
      <p className={cn("text-sm leading-relaxed text-foreground/80", className)}>
        {market.basis ?? "No market-sizing evidence was supplied."}
      </p>
    )
  }
  const { unit = "$B", basis } = market
  const H = 190
  const maxR = 82
  const maxV = market.tam
  const r = (v) => Math.max(maxR * Math.sqrt(v / maxV), 7)

  return (
    <div className={cn("flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-6", className)}>
      <svg width={maxR * 2 + 8} height={H} className="mx-auto shrink-0" role="img" aria-label="Market size: TAM, SAM, SOM">
        {tiers.map((t, i) => {
          const radius = r(market[t.key])
          return (
            <motion.circle
              key={t.key}
              cx={maxR + 4}
              cy={H - 4 - radius}
              r={radius}
              fill={t.fill}
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.12, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              style={{ transformOrigin: `${maxR + 4}px ${H - 4}px` }}
            />
          )
        })}
      </svg>
      <div className="flex-1 space-y-2.5">
        {tiers.map((t) => (
          <div key={t.key} className="flex items-center gap-2.5">
            <span className="size-3 shrink-0 rounded-full" style={{ background: t.fill, boxShadow: "inset 0 0 0 1px rgb(0 0 0 / 0.06)" }} />
            <span className="w-11 text-xs font-semibold">{t.label}</span>
            <span className="text-sm font-semibold tabular-nums">
              {unit.startsWith("$") ? `$${market[t.key]}B` : `${market[t.key]}${unit}`}
            </span>
            <span className="text-[11px] text-muted-foreground">
              {t.key === "tam" ? "total market" : t.key === "sam" ? "serviceable" : "obtainable (3yr)"}
            </span>
          </div>
        ))}
        {basis && <p className="pt-1 text-[11px] leading-relaxed text-muted-foreground">{basis}</p>}
      </div>
    </div>
  )
}

// ── Founder Score formula — weighted composition bar ──────────────────────
// Fixed component identity → categorical palette (validated: CVD ΔE 17.1,
// normal 18.1); every segment direct-labeled below.
const components = [
  { label: "Track record", weight: 30, color: "#0ea5e9", note: "GitHub, launches, prior exits" },
  { label: "Traction signal", weight: 20, color: "#10b981", note: "upvotes, stars, growth" },
  { label: "Founder-market fit", weight: 25, color: "#8b5cf6", note: "AI-judged coherence" },
  { label: "Resilience", weight: 25, color: "#f59e0b", note: "interview response pattern" },
]

export function ScoreFormulaBar({ className }) {
  return (
    <div className={className}>
      <div className="flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full">
        {components.map((c) => (
          <motion.div
            key={c.label}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            style={{ width: `${c.weight}%`, background: c.color, transformOrigin: "left" }}
            className="rounded-[3px]"
          />
        ))}
      </div>
      <div className="mt-2.5 grid grid-cols-2 gap-x-3 gap-y-1.5">
        {components.map((c) => (
          <div key={c.label} className="flex items-start gap-1.5">
            <span className="mt-1 size-2 shrink-0 rounded-full" style={{ background: c.color }} />
            <div className="leading-tight">
              <span className="text-[11px] font-semibold">
                {c.label} <span className="text-muted-foreground tabular-nums">{c.weight}%</span>
              </span>
              <div className="text-[10px] text-muted-foreground">{c.note}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
