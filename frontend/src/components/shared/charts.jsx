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
              {market.display?.[t.key] ?? (unit.startsWith("$") ? `$${market[t.key]}B` : `${market[t.key]}${unit}`)}
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

// A visual comparison without collapsing the three axes into one score. Founder
// remains numeric; Market and Idea-vs-Market stay categorical on bear/neutral/bull tracks.
export function DecisionLandscape({ opportunity, className }) {
  if (!opportunity) return null
  const rows = [
    { label: "Founder", kind: "score", value: opportunity.founder_axis?.score ?? 0, trend: opportunity.founder_axis?.trend },
    { label: "Market", kind: "rating", value: opportunity.market_axis?.rating ?? "neutral", trend: opportunity.market_axis?.trend },
    { label: "Idea vs Market", kind: "rating", value: opportunity.idea_vs_market_axis?.rating ?? "neutral", trend: opportunity.idea_vs_market_axis?.trend },
  ]
  return (
    <div className={cn("rounded-xl border border-border bg-card p-4", className)}>
      <div className="mb-4 flex items-start justify-between gap-3"><div><div className="text-xs font-semibold">Independent-axis landscape</div><p className="mt-0.5 text-[10px] text-muted-foreground">Three judgments shown together, never averaged.</p></div><div className="flex items-center gap-2 text-[8px] font-semibold tracking-wide text-muted-foreground uppercase"><span>Low / Bear</span><span>Mid / Neutral</span><span>High / Bull</span></div></div>
      <div className="space-y-4">
        {rows.map((row, index) => {
          const percent = row.kind === "score" ? Math.max(0, Math.min(100, row.value)) : ({ bear: 14, neutral: 50, bullish: 86 }[row.value] ?? 50)
          const display = row.kind === "score" ? row.value : row.value === "bullish" ? "Bullish" : row.value[0].toUpperCase() + row.value.slice(1)
          return <div key={row.label} className="grid grid-cols-[92px_minmax(0,1fr)_70px] items-center gap-3"><div><div className="text-[11px] font-semibold">{row.label}</div><div className={cn("text-[9px]", row.trend === "improving" ? "text-emerald-600" : row.trend === "declining" ? "text-red-500" : "text-muted-foreground")}>{row.trend === "improving" ? "↗" : row.trend === "declining" ? "↘" : "→"} {row.trend}</div></div><div className="relative h-2 rounded-full bg-gradient-to-r from-red-100 via-slate-100 to-emerald-100"><span className="absolute left-1/2 top-[-3px] h-3.5 w-px bg-slate-300"/><motion.span initial={{ left: "50%", opacity: 0 }} animate={{ left: `${percent}%`, opacity: 1 }} transition={{ delay: index * .12, duration: .55, ease: [0.16, 1, 0.3, 1] }} className={cn("absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow", percent > 66 ? "bg-emerald-500" : percent < 34 ? "bg-red-400" : "bg-slate-500")}/></div><div className="text-right text-xs font-semibold tabular-nums">{display}</div></div>
        })}
      </div>
    </div>
  )
}

export function EvidenceCoverageChart({ claims = [], sources = [], className }) {
  const trust = claims.reduce((tally, claim) => ({ ...tally, [claim.confidence]: (tally[claim.confidence] || 0) + 1 }), { high: 0, medium: 0, low: 0 })
  const total = Math.max(claims.length, 1)
  const highEnd = (trust.high / total) * 100
  const mediumEnd = highEnd + (trust.medium / total) * 100
  const bucketFor = (source) => {
    const text = `${source.type} ${source.title}`
    if (source.type === "deck") return "Deck"
    if (/github|linkedin|profile|founder/i.test(text)) return "People"
    if (/arxiv|paper|research|publication/i.test(text)) return "Research"
    if (/news|press|market|website|company/i.test(text)) return "Market & press"
    return "Other"
  }
  const sourceGroups = ["Deck", "People", "Market & press", "Research", "Other"].map((label) => ({ label, count: sources.filter((source) => bucketFor(source) === label).length }))
  const maxSources = Math.max(...sourceGroups.map((group) => group.count), 1)
  const uniqueSources = new Set(sources.map((source) => source.url).filter(Boolean)).size
  return (
    <div className={cn("rounded-xl border border-border bg-card p-4", className)}>
      <div className="mb-4"><div className="text-xs font-semibold">Evidence coverage</div><p className="mt-0.5 text-[10px] text-muted-foreground">Trust is calculated per claim; source volume is shown separately.</p></div>
      <div className="grid grid-cols-[112px_minmax(0,1fr)] items-center gap-5">
        <div className="relative mx-auto flex size-24 items-center justify-center rounded-full" style={{ background: claims.length ? `conic-gradient(#10b981 0 ${highEnd}%, #f59e0b ${highEnd}% ${mediumEnd}%, #f87171 ${mediumEnd}% 100%)` : "#e2e8f0" }}><span className="flex size-[70px] flex-col items-center justify-center rounded-full bg-card"><strong className="text-xl tabular-nums">{claims.length}</strong><span className="text-[8px] text-muted-foreground">claims checked</span></span></div>
        <div className="space-y-2.5">{[["High", trust.high, "bg-emerald-500"], ["Medium", trust.medium, "bg-amber-400"], ["Low", trust.low, "bg-red-400"]].map(([label, value, tone]) => <div key={label} className="grid grid-cols-[50px_minmax(0,1fr)_20px] items-center gap-2"><span className="text-[9px] font-medium text-muted-foreground">{label}</span><span className="h-1.5 overflow-hidden rounded-full bg-slate-100"><motion.span initial={{ width: 0 }} animate={{ width: `${(value / total) * 100}%` }} className={cn("block h-full rounded-full", tone)}/></span><strong className="text-right text-[10px] tabular-nums">{value}</strong></div>)}</div>
      </div>
      <div className="mt-4 border-t border-border pt-3"><div className="mb-2 flex items-center justify-between text-[9px] font-semibold tracking-wide text-muted-foreground uppercase"><span>Source mix</span><span>{uniqueSources} unique links</span></div><div className="grid grid-cols-2 gap-x-4 gap-y-2">{sourceGroups.map((group) => <div key={group.label}><div className="mb-1 flex justify-between text-[9px]"><span>{group.label}</span><span className="tabular-nums text-muted-foreground">{group.count}</span></div><div className="h-1.5 rounded-full bg-slate-100"><span className="block h-full rounded-full bg-violet-400" style={{ width: `${(group.count / maxSources) * 100}%` }}/></div></div>)}</div></div>
    </div>
  )
}
