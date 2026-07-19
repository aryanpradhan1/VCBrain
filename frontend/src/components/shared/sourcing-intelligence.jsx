import { ArrowRight, GitBranch, GraduationCap, Network, Rocket, Sparkles } from "lucide-react"

import { cn } from "@/lib/utils"

const channels = [
  { label: "GitHub", icon: GitBranch, x: 34, y: 36, tone: "text-slate-700 bg-slate-100" },
  { label: "Hackathons", icon: GraduationCap, x: 36, y: 126, tone: "text-sky-700 bg-sky-50" },
  { label: "Launches", icon: Rocket, x: 145, y: 160, tone: "text-amber-700 bg-amber-50" },
]

export function SourcingIntelligence({ opportunities = [] }) {
  const outbound = opportunities.filter((item) => item.sourcing_channel === "outbound")
  const approvals = outbound.filter((item) => item.verdict === "approve").length
  const conversion = outbound.length ? Math.round((approvals / outbound.length) * 100) : 0

  return (
    <section className="mb-6 overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border bg-slate-50/70 px-4 py-3.5">
        <div className="flex items-start gap-2.5">
          <span className="mt-0.5 flex size-7 items-center justify-center rounded-lg bg-violet-100 text-violet-700"><Network className="size-3.5" /></span>
          <div><h2 className="text-sm font-semibold tracking-tight">Sourcing intelligence</h2><p className="mt-0.5 text-[11px] text-muted-foreground">Where early founders become visible—and which pathways deserve another scan.</p></div>
        </div>
        <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-1 text-[9px] font-semibold tracking-wide text-violet-700 uppercase">Seeded demo cohort</span>
      </div>

      <div className="grid gap-0 lg:grid-cols-[260px_minmax(0,1fr)]">
        <div className="border-b border-border p-4 lg:border-r lg:border-b-0">
          <div className="relative mx-auto h-[190px] max-w-[230px] overflow-hidden rounded-lg border border-slate-100 bg-[radial-gradient(circle_at_center,_#fafafa_0,_#fff_65%)]">
            <svg aria-hidden="true" className="absolute inset-0 h-full w-full" viewBox="0 0 230 190"><path d="M58 48 C95 52 104 87 112 94" fill="none" stroke="#cbd5e1" strokeWidth="1.5" /><path d="M58 138 C90 132 101 106 112 96" fill="none" stroke="#cbd5e1" strokeWidth="1.5" /><path d="M162 164 C149 133 136 113 120 101" fill="none" stroke="#cbd5e1" strokeWidth="1.5" /></svg>
            {channels.map(({ label, icon: Icon, x, y, tone }) => <div key={label} className="absolute -translate-x-1/2 -translate-y-1/2 text-center" style={{ left: x, top: y }}><span className={cn("mx-auto flex size-8 items-center justify-center rounded-full border border-white shadow-sm", tone)}><Icon className="size-3.5" /></span><span className="mt-1 block text-[9px] font-medium text-slate-600">{label}</span></div>)}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center"><span className="flex size-11 items-center justify-center rounded-full bg-slate-900 text-white shadow-md"><Sparkles className="size-4" /></span><span className="mt-1 block text-[9px] font-semibold text-slate-700">FounderScore</span></div>
          </div>
        </div>
        <div className="grid gap-px bg-border sm:grid-cols-3">
          <Metric label="Sourced this cohort" value={outbound.length} caption="deduplicated before review" />
          <Metric label="Reached decision" value={`${conversion}%`} caption="seeded outcome feedback" />
          <div className="bg-card p-4"><div className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">Next scan</div><div className="mt-2 flex items-center gap-1 text-sm font-semibold">University hackathons <ArrowRight className="size-3.5 text-violet-600" /></div><p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">Suggested from the demo channel map; production learns this from conversion outcomes.</p></div>
        </div>
      </div>
    </section>
  )
}

function Metric({ label, value, caption }) {
  return <div className="bg-card p-4"><div className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">{label}</div><div className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">{value}</div><p className="mt-1 text-[11px] text-muted-foreground">{caption}</p></div>
}
