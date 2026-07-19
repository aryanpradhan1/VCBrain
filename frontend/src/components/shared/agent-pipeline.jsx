import {
  Brain,
  Crosshair,
  FileText,
  Filter,
  ScanSearch,
  ShieldCheck,
} from "lucide-react"

import { cn } from "@/lib/utils"

const agentIcons = {
  screen: Filter,
  intake: ScanSearch,
  thesis: Crosshair,
  scorer: Brain,
  diligence: ShieldCheck,
  memo: FileText,
}

const duration = (ms) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`)

// A trace is audit information, not a product-tour graphic. This deliberately
// reads like a compact processing ledger: stage, method, finding, and latency.
export function AgentPipeline({ trace, className }) {
  if (!trace?.length) return null

  const totalMs = trace.reduce((total, step) => total + (step.ms ?? 0), 0)
  const aiSteps = trace.filter((step) => step.kind === "ai").length

  return (
    <div className={cn("overflow-hidden rounded-xl border border-border bg-card", className)}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-slate-50/70 px-4 py-3">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold tracking-tight">Processing trace</span>
          <span className="text-xs text-muted-foreground">{trace.length} stages · {aiSteps} AI judgments</span>
        </div>
        <span className="font-mono text-[11px] tabular-nums text-muted-foreground">{(totalMs / 1000).toFixed(1)}s total</span>
      </div>

      <ol className="divide-y divide-border">
        {trace.map((step, index) => {
          const Icon = agentIcons[step.agent] ?? Brain
          const ai = step.kind === "ai"
          return (
            <li key={`${step.agent}-${index}`} className="grid grid-cols-[30px_minmax(118px,0.8fr)_minmax(0,2fr)_44px] items-center gap-3 px-4 py-3.5 sm:grid-cols-[30px_148px_minmax(0,2fr)_52px]">
              <span className={cn("flex size-7 items-center justify-center rounded-md border", ai ? "border-violet-200 bg-violet-50 text-violet-700" : "border-slate-200 bg-slate-50 text-slate-600")}>
                <Icon className="size-3.5" strokeWidth={2} />
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-sm font-medium">{step.label}</span>
                  <span className={cn("hidden rounded-sm px-1.5 py-0.5 text-[9px] font-bold tracking-[0.08em] uppercase sm:inline", ai ? "bg-violet-50 text-violet-700" : "bg-slate-100 text-slate-500")}>
                    {ai ? "AI" : "Rule"}
                  </span>
                </div>
                <span className="mt-0.5 block text-[10px] font-medium tracking-wide text-muted-foreground uppercase">Stage {String(index + 1).padStart(2, "0")}</span>
              </div>
              <p className="min-w-0 text-[12px] leading-relaxed text-muted-foreground sm:text-[13px]">{step.summary}</p>
              <span className="text-right font-mono text-[10px] tabular-nums text-muted-foreground">{duration(step.ms)}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
