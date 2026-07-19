import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  ArrowRight,
  CheckCircle2,
  CircleOff,
  Clock3,
  ExternalLink,
  GitBranch,
  MailCheck,
  Orbit,
  Radar,
  RefreshCw,
  Rocket,
  ScanSearch,
  Sparkles,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Page } from "@/components/shared/page"
import { ErrorBanner } from "@/components/shared/states"
import { listOutboundLeads, triggerOutboundScan } from "@/lib/api"
import { useAsync } from "@/lib/use-async"
import { cn } from "@/lib/utils"

const statusMeta = {
  not_activated: { label: "Below activation threshold", icon: CircleOff, cls: "bg-slate-100 text-slate-600" },
  delivered_no_response: { label: "Outreach sent", icon: MailCheck, cls: "bg-sky-50 text-sky-700" },
  declined: { label: "Declined outreach", icon: CircleOff, cls: "bg-red-50 text-red-700" },
  converted: { label: "Converted to application", icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-700" },
}

export default function Outbound() {
  const { data, error, loading, retry } = useAsync(() => listOutboundLeads(), [])
  const [status, setStatus] = useState("all")
  const [scanning, setScanning] = useState(false)
  const [scanMessage, setScanMessage] = useState(null)
  const leads = useMemo(() => data || [], [data])

  useEffect(() => {
    if (!scanning) return undefined
    const poll = window.setInterval(retry, 5000)
    const stop = window.setTimeout(() => setScanning(false), 60000)
    return () => { window.clearInterval(poll); window.clearTimeout(stop) }
  }, [scanning, retry])

  const filtered = useMemo(() => leads.filter((lead) => status === "all" || lead.outreach_status === status), [leads, status])
  const counts = useMemo(() => ({ sent: leads.filter((lead) => lead.outreach_status === "delivered_no_response").length, converted: leads.filter((lead) => lead.outreach_status === "converted").length, declined: leads.filter((lead) => lead.outreach_status === "declined").length }), [leads])

  const startScan = async () => {
    setScanning(true)
    setScanMessage(null)
    try {
      const response = await triggerOutboundScan()
      setScanMessage({ error: false, text: response.detail })
      window.setTimeout(retry, 1200)
    } catch {
      setScanning(false)
      setScanMessage({ error: true, text: "The scan could not start. Check the backend keys and server logs." })
    }
  }

  return (
    <Page>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 text-[10px] font-semibold tracking-[0.12em] text-violet-600 uppercase">Outbound sourcing</div>
          <h1 className="text-[28px] font-semibold tracking-[-0.035em]">Sourcing radar</h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">Discover technical founders before they raise, activate the strongest matches, and track conversion into the same investment funnel.</p>
        </div>
        <Button onClick={startScan} disabled={scanning} className="rounded-full px-4"><RefreshCw className={cn("size-4", scanning && "animate-spin")}/>{scanning ? "Scan running…" : "Run bounded scan"}</Button>
      </div>

      {scanMessage && <div className={cn("mb-4 rounded-xl px-4 py-3 text-xs", scanMessage.error ? "bg-red-50 text-red-700" : "bg-violet-50 text-violet-800")}>{scanMessage.text}</div>}

      <ScanFlow scanning={scanning}/>

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Stat icon={MailCheck} value={counts.sent} label="Awaiting response" note="activated above threshold" tone="sky"/>
        <Stat icon={CheckCircle2} value={counts.converted} label="Converted" note="entered full application" tone="emerald"/>
        <Stat icon={CircleOff} value={counts.declined} label="Declined" note="suppressed from outreach" tone="red"/>
      </div>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-lg border border-border bg-card p-0.5 text-xs font-medium">
          {["all", "delivered_no_response", "converted", "declined"].map((value) => <button key={value} type="button" onClick={() => setStatus(value)} className={cn("rounded-md px-3 py-1.5", status === value ? "bg-slate-950 text-white" : "text-muted-foreground")}>{value === "all" ? "All leads" : statusMeta[value].label}</button>)}
        </div>
        <button type="button" onClick={retry} className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground hover:text-foreground"><RefreshCw className="size-3"/> Refresh</button>
      </div>

      {error && <ErrorBanner message="Couldn't load outbound leads." onRetry={retry}/>} 
      {loading && !data && <LeadSkeleton/>}
      {!loading && !error && filtered.length === 0 && <div className="rounded-xl border border-dashed border-border bg-card px-6 py-14 text-center"><Radar className="mx-auto size-7 text-slate-300"/><h2 className="mt-3 text-sm font-semibold">No activated leads yet</h2><p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-muted-foreground">Run the bounded scan. Candidates are written to Memory, but this view only shows founders who crossed the activation threshold and entered outreach.</p></div>}
      {filtered.length > 0 && <div className="overflow-hidden rounded-xl border border-border bg-card"><div className="hidden grid-cols-[minmax(0,1fr)_130px_180px_150px] gap-4 border-b border-border bg-slate-50/70 px-5 py-2.5 text-[10px] font-semibold tracking-[.08em] text-muted-foreground uppercase lg:grid"><span>Founder discovered</span><span>Partial score</span><span>Outreach</span><span>Next step</span></div>{filtered.map((lead) => <LeadRow key={lead.founder_id} lead={lead}/>)}</div>}

      <div className="mt-4 flex items-start gap-2 rounded-xl bg-slate-50 px-4 py-3 text-[10px] leading-relaxed text-muted-foreground"><Sparkles className="mt-0.5 size-3.5 shrink-0 text-violet-500"/><span>Outbound uses a partial score on a <strong>0–50 scale</strong> because deck and interview evidence do not exist yet. Once a founder applies, their public Memory history converges with the full 0–100 assessment.</span></div>
    </Page>
  )
}

function ScanFlow({ scanning }) {
  const steps = [
    { icon: Orbit, label: "Discover", note: "GitHub · HN · PH · arXiv" },
    { icon: ScanSearch, label: "Thesis filter", note: "bounded candidates" },
    { icon: Radar, label: "Partial score", note: "public signals · /50" },
    { icon: MailCheck, label: "Activate", note: "threshold + contact" },
    { icon: Rocket, label: "Converge", note: "full application" },
  ]
  return <div className="mb-5 overflow-x-auto rounded-xl border border-border bg-slate-950 p-4 text-white"><div className="flex min-w-[720px] items-center">{steps.map(({ icon: Icon, label, note }, index) => <div key={label} className="contents"><div className="flex min-w-0 flex-1 items-center gap-2.5"><span className={cn("flex size-9 shrink-0 items-center justify-center rounded-xl bg-white/10 text-violet-300", scanning && index === 0 && "animate-pulse bg-violet-500/30")}><Icon className="size-4"/></span><span className="min-w-0"><strong className="block text-xs">{label}</strong><span className="block truncate text-[9px] text-slate-400">{note}</span></span></div>{index < steps.length - 1 && <ArrowRight className="mx-3 size-3.5 shrink-0 text-slate-600"/>}</div>)}</div></div>
}

function LeadRow({ lead }) {
  const meta = statusMeta[lead.outreach_status] || statusMeta.not_activated
  const Icon = meta.icon
  const identity = lead.founder_id.replace(/^founder-/, "").replaceAll("_", " ")
  const converted = lead.outreach_status === "converted" && lead.company_id && !lead.company_id.startsWith("pending_")
  return <div className="grid gap-3 border-b border-border px-4 py-4 last:border-0 sm:px-5 lg:grid-cols-[minmax(0,1fr)_130px_180px_150px] lg:items-center lg:gap-4"><div className="flex min-w-0 items-center gap-3"><span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-xs font-bold text-white">{identity[0]?.toUpperCase() || "F"}</span><div className="min-w-0"><div className="truncate text-sm font-semibold capitalize">{identity}</div><div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-muted-foreground"><GitBranch className="size-3"/> discovered from bounded public signals {lead.cold_start_flag && <Badge variant="caution">Cold start</Badge>}</div></div></div><div><div className="text-lg font-semibold tabular-nums">{lead.founder_score.value}<span className="text-xs font-normal text-muted-foreground"> / 50</span></div><div className="text-[9px] text-muted-foreground">± {lead.founder_score.confidence_interval} · {lead.founder_score.trend}</div></div><div><span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold", meta.cls)}><Icon className="size-3"/>{meta.label}</span>{lead.last_event_at && <div className="mt-1 flex items-center gap-1 text-[9px] text-muted-foreground"><Clock3 className="size-2.5"/>{new Date(lead.last_event_at).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</div>}</div><div>{converted ? <Link to={`/opportunities/${lead.company_id}`} className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-700 hover:underline">Open application <ExternalLink className="size-3"/></Link> : <span className="text-[10px] leading-relaxed text-muted-foreground">Awaiting founder application</span>}</div></div>
}

function Stat({ icon: Icon, value, label, note, tone }) { const styles = { sky: "bg-sky-50 text-sky-600", emerald: "bg-emerald-50 text-emerald-600", red: "bg-red-50 text-red-600" }; return <div className="rounded-xl border border-border bg-card p-4"><div className="flex items-center gap-2"><span className={cn("flex size-7 items-center justify-center rounded-lg", styles[tone])}><Icon className="size-3.5"/></span><span className="text-xs font-medium text-muted-foreground">{label}</span></div><div className="mt-2 text-2xl font-semibold">{value}</div><div className="text-[10px] text-muted-foreground">{note}</div></div> }

function LeadSkeleton() { return <div className="space-y-2">{[1,2,3].map((item) => <Skeleton key={item} className="h-20 rounded-xl"/>)}</div> }
