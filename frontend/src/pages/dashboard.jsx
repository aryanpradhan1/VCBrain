import { useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { motion } from "motion/react"
import {
  Banknote,
  Gauge,
  Inbox,
  Radar,
  Search,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { AxisDots, ChannelBadge, ColdStartBadge } from "@/components/shared/chips"
import { Page, stagger } from "@/components/shared/page"
import { ScoreBadge } from "@/components/shared/score-badge"
import { SignalIcons } from "@/components/shared/signal-chips"
import {
  fmtAmount,
  trustTally,
  verdictMeta,
} from "@/components/shared/semantics"
import { EmptyState, ErrorBanner } from "@/components/shared/states"
import { listOpportunities } from "@/lib/api"
import { useAsync } from "@/lib/use-async"
import { cn } from "@/lib/utils"
import { pitchOf } from "@/fixtures/opportunities"

const verdictFilters = ["all", "approve", "review", "decline"]

function StatTile({ icon: Icon, label, value, suffix, prefix, caption, tint }) {
  return (
      <div className="flex h-full min-w-0 flex-col rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-2">
          <span className={cn("flex size-7 items-center justify-center rounded-lg", tint)}>
            <Icon className="size-3.5" strokeWidth={2.2} />
          </span>
          <span className="truncate text-xs font-medium text-muted-foreground">{label}</span>
        </div>
        <div className="mt-2.5 text-2xl font-semibold tracking-tight tabular-nums">
          {prefix}
          {value}
          {suffix}
        </div>
        <div className="mt-0.5 truncate text-[11px] text-muted-foreground">{caption}</div>
      </div>
  )
}

function TrustDots({ claims }) {
  const t = trustTally(claims)
  const groups = [
    { n: t.high, cls: "bg-emerald-500", label: "high" },
    { n: t.medium, cls: "bg-amber-400", label: "medium" },
    { n: t.low, cls: "bg-red-400", label: "low" },
  ]
  return (
    <span
      className="inline-flex h-7 min-w-7 items-center justify-center gap-0.5 rounded-md border border-border bg-white px-1.5"
      title={`Claim trust: ${t.high} high · ${t.medium} medium · ${t.low} low`}>
      {groups.map(
        ({ n, cls, label }) =>
          n > 0 && (
            <span key={label} className="inline-flex items-center gap-0.5">
              {Array.from({ length: n }).map((_, i) => (
                <span key={i} className={cn("size-1.5 rounded-full", cls)} />
              ))}
            </span>
          )
      )}
    </span>
  )
}

function FounderMarks({ founders }) {
  if (!founders?.length) return null
  return (
    <span className="flex -space-x-1.5" title={founders.map((founder) => founder.name).join(", ")}>
      {founders.slice(0, 3).map((founder, index) => (
        founder.avatar ? (
          <img key={founder.name} src={founder.avatar} alt={founder.name} className="size-6 rounded-full border-2 border-card object-cover" style={{ zIndex: 3 - index }} />
        ) : (
          <span key={founder.name} className="flex size-6 items-center justify-center rounded-full border-2 border-card bg-slate-800 text-[9px] font-bold text-white" style={{ zIndex: 3 - index }}>
            {founder.name?.[0] || "F"}
          </span>
        )
      ))}
    </span>
  )
}

function Row({ opp }) {
  return (
    <motion.li variants={stagger.item}>
      <Link
        to={`/opportunities/${opp.company_id}`}
        className="group grid gap-3 px-4 py-4 transition-colors hover:bg-slate-50/70 sm:grid-cols-[minmax(0,1fr)_126px] sm:gap-6 sm:px-5 lg:grid-cols-[minmax(0,1fr)_134px_126px]">
        <div className="flex min-w-0 gap-3">
        <span
          className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-sm font-bold text-white">
          {opp.company_name[0]}
        </span>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-[15px] font-semibold tracking-tight">{opp.company_name}</span>
            <Badge variant={verdictMeta[opp.verdict].variant}>{verdictMeta[opp.verdict].label}</Badge>
            <ChannelBadge channel={opp.sourcing_channel} compact />
            {opp.cold_start_flag && <ColdStartBadge compact />}
            {opp.enrichment && (
              <span className="text-[11px] font-medium text-muted-foreground">
                {opp.enrichment.sector} · {opp.enrichment.stage} · {opp.enrichment.geography}
              </span>
            )}
          </div>
          <p className="truncate text-sm text-muted-foreground">{pitchOf(opp)}</p>
          <div className="flex flex-wrap items-center gap-2">
            <FounderMarks founders={opp.enrichment?.founders} />
            <SignalIcons signals={opp.public_signals} />
            <TrustDots claims={opp.claim_trust} />
          </div>
        </div>
        </div>

        <div className="hidden shrink-0 flex-col items-end justify-center gap-1.5 sm:flex">
          <span title="value ± confidence interval — the band narrows as independent evidence corroborates">
            <ScoreBadge score={opp.founder_score} size="sm" />
          </span>
          <span title="Founder / Market / Idea-vs-Market — three independent axes, never averaged">
            <AxisDots
              founder_axis={opp.founder_axis}
              market_axis={opp.market_axis}
              idea_vs_market_axis={opp.idea_vs_market_axis}
            />
          </span>
        </div>

        <div className="hidden flex-col items-end justify-center lg:flex">
          {opp.amount_recommended > 0 ? (
            <span className="text-sm font-semibold tracking-tight tabular-nums">{fmtAmount(opp.amount_recommended)}</span>
          ) : (
            <span className="text-xs font-medium text-muted-foreground">No check</span>
          )}
        </div>
      </Link>
    </motion.li>
  )
}

function RowSkeleton() {
  return (
    <div className="flex items-center gap-4 border-b border-border px-4 py-4 sm:px-5">
      <Skeleton className="size-11 rounded-xl" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-52" />
        <Skeleton className="h-3 w-4/5" />
        <Skeleton className="h-5 w-64 rounded-full" />
      </div>
      <Skeleton className="h-10 w-20" />
    </div>
  )
}

export default function Dashboard() {
  const { data, error, loading, retry } = useAsync(listOpportunities)
  const [query, setQuery] = useState("")
  const [verdict, setVerdict] = useState("all")
  const [searchParams] = useSearchParams()
  const sourcingOnly = searchParams.get("channel") === "outbound"

  const filtered = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    return data.filter((o) => {
      if (sourcingOnly && o.sourcing_channel !== "outbound") return false
      if (verdict !== "all" && o.verdict !== verdict) return false
      if (!q) return true
      return [o.company_name, pitchOf(o), o.sourcing_channel, o.verdict]
        .join(" ")
        .toLowerCase()
        .includes(q)
    })
  }, [data, query, verdict, sourcingOnly])

  const stats = useMemo(() => {
    if (!data) return null
    const avg = Math.round(data.reduce((a, o) => a + o.founder_score.value, 0) / data.length)
    const sourced = data.filter((o) => o.sourcing_channel === "outbound").length
    const totalK = data.reduce((a, o) => a + (o.verdict === "approve" ? o.amount_recommended : 0), 0) / 1000
    return { count: data.length, avg, sourced, totalK }
  }, [data])

  return (
    <Page>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 text-[10px] font-semibold tracking-[0.12em] text-muted-foreground uppercase">Investment workspace</div>
          <h1 className="text-[28px] font-semibold tracking-[-0.035em]">
            {sourcingOnly ? "Sourcing radar" : "Pipeline"}
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {sourcingOnly
              ? "Founders we found before they applied — activated above the score threshold."
              : "Ranked by Founder Score — inbound and sourced, one funnel."}
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search founders, sectors, signals…"
            className="h-10 rounded-lg bg-card pl-9 shadow-none"
          />
        </div>
      </div>

      {stats && (
        <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile icon={Inbox} label="In pipeline" value={stats.count} caption="all channels, deduplicated" tint="bg-sky-50 text-sky-600" />
          <StatTile icon={Gauge} label="Avg Founder Score" value={stats.avg} caption="event-triggered, never resets" tint="bg-emerald-50 text-emerald-600" />
          <StatTile icon={Radar} label="Sourced outbound" value={stats.sourced} caption="found before they applied" tint="bg-violet-50 text-violet-600" />
          <StatTile icon={Banknote} label="Checks recommended" value={stats.totalK} prefix="$" suffix="K" caption="pending partner decision" tint="bg-amber-50 text-amber-600" />
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-1.5">
        {verdictFilters.map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setVerdict(v)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors",
              verdict === v
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-card text-muted-foreground card-hairline hover:text-foreground"
            )}>
            {v}
          </button>
        ))}
        {sourcingOnly && (
          <Link to="/" className="ml-1 text-xs font-medium text-muted-foreground underline underline-offset-2 hover:text-foreground">
            clear sourcing filter
          </Link>
        )}
      </div>

      {error && <ErrorBanner message="Couldn't load the pipeline. The backend may still be waking up." onRetry={retry} />}

      {loading && (
        <div className="space-y-3">
          <RowSkeleton />
          <RowSkeleton />
          <RowSkeleton />
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <EmptyState>
          {query || verdict !== "all" ? "No opportunities match these filters." : "No opportunities in the pipeline yet."}
        </EmptyState>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="hidden grid-cols-[minmax(0,1fr)_134px_126px] gap-6 border-b border-border bg-slate-50/70 px-5 py-2.5 text-[10px] font-semibold tracking-[0.1em] text-muted-foreground uppercase lg:grid">
            <span>Company & diligence signal</span><span className="text-right">Founder Score</span><span className="text-right">Recommended</span>
          </div>
          <motion.ul variants={stagger.container} initial="initial" animate="animate" className="divide-y divide-border">
            {filtered.map((opp) => <Row key={opp.company_id} opp={opp} />)}
          </motion.ul>
        </div>
      )}
    </Page>
  )
}
