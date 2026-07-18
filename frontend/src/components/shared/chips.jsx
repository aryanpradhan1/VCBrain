import { ArrowDownLeft, ArrowUpRight, Sprout } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { confidenceMeta, ratingMeta, scoreDot } from "./semantics"

// bullish/neutral/bear pill — same mapping everywhere a judgment appears.
export function RatingPill({ rating }) {
  const meta = ratingMeta[rating] ?? ratingMeta.neutral
  return (
    <Badge variant={meta.variant}>
      <span className={cn("size-1.5 rounded-full", meta.dot)} />
      {meta.label}
    </Badge>
  )
}

// high/medium/low confidence chip — memo + trust list share this exact component.
export function ConfidenceChip({ confidence, short = false }) {
  const meta = confidenceMeta[confidence] ?? confidenceMeta.medium
  return <Badge variant={meta.variant}>{short ? confidence : meta.label}</Badge>
}

// Same amber tag + same copy every time cold_start_flag fires. Never customized.
export function ColdStartBadge({ compact = false }) {
  if (compact) {
    return (
      <span title="Cold start — thin public data, wide confidence interval" className="inline-flex size-7 items-center justify-center rounded-md bg-amber-50 text-amber-700">
        <Sprout className="size-3.5" />
      </span>
    )
  }
  return (
    <Badge variant="caution">
      <Sprout />
      Cold start — thin public data, wide interval
    </Badge>
  )
}

export function ChannelBadge({ channel, compact = false }) {
  const inbound = channel === "inbound"
  const Icon = inbound ? ArrowDownLeft : ArrowUpRight
  if (compact) {
    return (
      <span title={inbound ? "Inbound application" : "Sourced outbound"} className="inline-flex size-7 items-center justify-center rounded-md border border-border bg-white text-slate-400">
        <Icon className="size-3.5" />
      </span>
    )
  }
  return (
    <Badge variant="outline" className="gap-1">
      <Icon className="size-3 text-slate-400" />
      {inbound ? "Inbound" : "Sourced"}
    </Badge>
  )
}

// The three axis dots on dashboard rows — Founder / Market / Idea-vs-Market,
// never merged into a single averaged badge.
export function AxisDots({ founder_axis, market_axis, idea_vs_market_axis }) {
  const dots = [
    { key: "Founder", cls: scoreDot(founder_axis.score), detail: `${founder_axis.score}` },
    { key: "Market", cls: (ratingMeta[market_axis.rating] ?? ratingMeta.neutral).dot, detail: market_axis.rating },
    { key: "Idea vs Market", cls: (ratingMeta[idea_vs_market_axis.rating] ?? ratingMeta.neutral).dot, detail: idea_vs_market_axis.rating },
  ]
  return (
    <span className="inline-flex items-center gap-1.5">
      {dots.map((d) => (
        <span
          key={d.key}
          title={`${d.key}: ${d.detail}`}
          className={cn("size-2 rounded-full transition-transform hover:scale-150", d.cls)}
        />
      ))}
    </span>
  )
}
