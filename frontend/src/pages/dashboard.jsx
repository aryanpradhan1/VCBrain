import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { motion } from "motion/react"
import { ChevronRight, Search } from "lucide-react"

import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AxisDots,
  ChannelBadge,
  ColdStartBadge,
} from "@/components/shared/chips"
import { Page, stagger } from "@/components/shared/page"
import { ScoreBadge } from "@/components/shared/score-badge"
import { EmptyState, ErrorBanner } from "@/components/shared/states"
import { listOpportunities } from "@/lib/api"
import { useAsync } from "@/lib/use-async"
import { pitchOf } from "@/fixtures/opportunities"

function Row({ opp }) {
  return (
    <motion.li variants={stagger.item}>
      <Link
        to={`/opportunities/${opp.company_id}`}
        className="group flex items-center gap-4 rounded-2xl bg-card p-4 card-hairline transition-all duration-200 hover:card-hairline-hover hover:-translate-y-px sm:px-5">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-secondary text-sm font-semibold text-secondary-foreground">
          {opp.company_name[0]}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-sm font-semibold tracking-tight">{opp.company_name}</span>
            <ChannelBadge channel={opp.sourcing_channel} />
            {opp.cold_start_flag && <ColdStartBadge />}
          </div>
          <p className="mt-0.5 truncate text-sm text-muted-foreground">{pitchOf(opp)}</p>
        </div>

        <div className="hidden shrink-0 sm:block">
          <AxisDots
            founder_axis={opp.founder_axis}
            market_axis={opp.market_axis}
            idea_vs_market_axis={opp.idea_vs_market_axis}
          />
        </div>

        <div className="shrink-0 text-right">
          <ScoreBadge score={opp.founder_score} size="sm" />
        </div>

        <ChevronRight className="size-4 shrink-0 text-slate-300 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-slate-400" />
      </Link>
    </motion.li>
  )
}

function RowSkeleton() {
  return (
    <div className="flex items-center gap-4 rounded-2xl bg-card p-4 card-hairline sm:px-5">
      <Skeleton className="size-10 rounded-xl" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-44" />
        <Skeleton className="h-3 w-4/5" />
      </div>
      <Skeleton className="h-5 w-16" />
    </div>
  )
}

export default function Dashboard() {
  const { data, error, loading, retry } = useAsync(listOpportunities)
  const [query, setQuery] = useState("")

  const filtered = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    if (!q) return data
    return data.filter((o) =>
      [o.company_name, pitchOf(o), o.sourcing_channel, o.verdict]
        .join(" ")
        .toLowerCase()
        .includes(q)
    )
  }, [data, query])

  return (
    <Page>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Pipeline</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Ranked by Founder Score — inbound and sourced, one funnel.
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search founders, sectors, signals…"
            className="rounded-full pl-9"
          />
        </div>
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
          {query ? `No matches for “${query}”.` : "No opportunities in the pipeline yet."}
        </EmptyState>
      )}

      {!loading && !error && filtered.length > 0 && (
        <motion.ul
          variants={stagger.container}
          initial="initial"
          animate="animate"
          className="space-y-3">
          {filtered.map((opp) => (
            <Row key={opp.company_id} opp={opp} />
          ))}
        </motion.ul>
      )}
    </Page>
  )
}
