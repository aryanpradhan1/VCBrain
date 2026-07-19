import { Network, Radar, Waypoints } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { Page } from "@/components/shared/page"
import { SourcingIntelligence } from "@/components/shared/sourcing-intelligence"
import { ErrorBanner } from "@/components/shared/states"
import { listOpportunities } from "@/lib/api"
import { useAsync } from "@/lib/use-async"

export default function NetworkIntelligence() {
  const { data, error, loading, retry } = useAsync(() => listOpportunities(), [])
  const publicCount = data?.filter((item) => item.enrichment?.reference_profile).length || 0
  const founderCount = data?.filter((item) => item.enrichment?.reference_profile).reduce((sum, item) => sum + (item.enrichment?.founders?.length || 0), 0) || 0

  return (
    <Page>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 text-[10px] font-semibold tracking-[0.12em] text-muted-foreground uppercase">Sourcing intelligence</div>
          <h1 className="text-[28px] font-semibold tracking-[-0.035em]">Network map</h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">See how founders become visible, where strong signals cluster, and which adjacent communities the fund should explore next.</p>
        </div>
        {data && <div className="flex gap-2"><Metric icon={Network} value={publicCount} label="verified companies"/><Metric icon={Waypoints} value={founderCount} label="mapped founders"/></div>}
      </div>

      <div className="mb-5 flex items-start gap-3 rounded-xl border border-violet-100 bg-violet-50/60 px-4 py-3 text-xs leading-relaxed text-violet-950">
        <Radar className="mt-0.5 size-4 shrink-0 text-violet-600" />
        <span><strong>How to read this:</strong> edges explain where each record came from; cohort cards summarize patterns. They are directional sourcing signals, not claims that an institution or degree causes founder success.</span>
      </div>

      {error && <ErrorBanner message="Couldn't load network intelligence." onRetry={retry} />}
      {loading && <Skeleton className="h-[680px] rounded-xl" />}
      {!loading && !error && data && <SourcingIntelligence opportunities={data} />}
    </Page>
  )
}

function Metric({ icon: Icon, value, label }) {
  return <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 shadow-sm"><span className="flex size-7 items-center justify-center rounded-lg bg-slate-100"><Icon className="size-3.5 text-slate-600"/></span><span><strong className="block text-sm tabular-nums">{value}</strong><span className="block text-[9px] text-muted-foreground">{label}</span></span></div>
}
