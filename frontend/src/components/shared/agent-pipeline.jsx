import { createRef, useMemo, useRef } from "react"
import {
  Brain,
  Crosshair,
  FileText,
  Filter,
  ScanSearch,
  ShieldCheck,
} from "lucide-react"

import { AnimatedBeam } from "@/components/magicui/animated-beam"
import { cn } from "@/lib/utils"

const agentIcons = {
  screen: Filter,
  intake: ScanSearch,
  thesis: Crosshair,
  scorer: Brain,
  diligence: ShieldCheck,
  memo: FileText,
}

// "What the system actually did" — one node per agent, animated beams tracing
// the pipeline, each step labeled rule-based vs AI reasoning (the honesty story).
export function AgentPipeline({ trace, className }) {
  const containerRef = useRef(null)
  const nodeRefs = useMemo(() => (trace ?? []).map(() => createRef()), [trace])

  if (!trace?.length) return null
  const totalMs = trace.reduce((a, t) => a + (t.ms ?? 0), 0)

  return (
    <div className={className}>
      <div ref={containerRef} className="relative">
        <div className="grid grid-cols-3 gap-x-3 gap-y-6 md:grid-cols-6">
          {trace.map((step, i) => {
            const Icon = agentIcons[step.agent] ?? Brain
            const ai = step.kind === "ai"
            return (
              <div key={step.agent} className="flex min-w-0 flex-col items-center gap-2 px-0.5 text-center">
                <div
                  ref={nodeRefs[i]}
                  className={cn(
                    "z-10 flex size-11 items-center justify-center rounded-2xl border bg-card shadow-sm",
                    ai ? "border-violet-200 text-violet-600" : "border-slate-200 text-slate-500"
                  )}>
                  <Icon className="size-4.5" strokeWidth={2} />
                </div>
                <div className="min-w-0 space-y-1">
                  <div className="text-[11px] font-semibold leading-tight">{step.label}</div>
                  <div
                    className={cn(
                      "inline-block rounded-full px-1.5 py-px text-[9px] font-semibold uppercase tracking-wide",
                      ai ? "bg-violet-50 text-violet-600" : "bg-slate-100 text-slate-500"
                    )}>
                    {ai ? "AI reasoning" : "rule-based"}
                  </div>
                  <p className="text-[10px] leading-snug break-words text-muted-foreground">{step.summary}</p>
                  <div className="text-[9px] text-muted-foreground/60 tabular-nums">
                    {step.ms >= 1000 ? `${(step.ms / 1000).toFixed(1)}s` : `${step.ms}ms`}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
        {nodeRefs.slice(0, -1).map((ref, i) => (
          <AnimatedBeam
            key={i}
            containerRef={containerRef}
            fromRef={ref}
            toRef={nodeRefs[i + 1]}
            duration={4}
            delay={i * 0.4}
            pathColor="#cbd5e1"
            pathOpacity={0.5}
            gradientStartColor="#8b5cf6"
            gradientStopColor="#0ea5e9"
          />
        ))}
      </div>
      <p className="mt-3 text-center text-[11px] text-muted-foreground">
        Full pass in <span className="font-medium tabular-nums">{(totalMs / 1000).toFixed(1)}s</span> — deterministic
        gates run first so AI reasoning is spent only where judgment matters.
      </p>
    </div>
  )
}
