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

// "What the system actually did" — a clean beam row of agent nodes on top,
// with each step's detail given room to breathe in a grid below.
export function AgentPipeline({ trace, className }) {
  const containerRef = useRef(null)
  const nodeRefs = useMemo(() => (trace ?? []).map(() => createRef()), [trace])

  if (!trace?.length) return null
  const totalMs = trace.reduce((a, t) => a + (t.ms ?? 0), 0)

  return (
    <div className={className}>
      {/* Beam row — icons and names only */}
      <div className="overflow-x-auto pb-1">
        <div ref={containerRef} className="relative min-w-[540px] px-2">
          <div className="flex items-start justify-between">
            {trace.map((step, i) => {
              const Icon = agentIcons[step.agent] ?? Brain
              const ai = step.kind === "ai"
              return (
                <div key={step.agent} className="flex w-20 flex-col items-center gap-2 text-center">
                  <div
                    ref={nodeRefs[i]}
                    className={cn(
                      "relative z-10 flex size-12 items-center justify-center rounded-2xl border bg-card shadow-sm transition-transform hover:-translate-y-0.5 hover:shadow-md",
                      ai ? "border-violet-200 text-violet-600" : "border-slate-200 text-slate-500"
                    )}>
                    <span className="absolute -top-1.5 -right-1.5 flex size-4 items-center justify-center rounded-full border border-card bg-secondary text-[8px] font-bold text-muted-foreground">
                      {i + 1}
                    </span>
                    <Icon className="size-5" strokeWidth={1.9} />
                  </div>
                  <div className="text-[11px] font-semibold leading-tight">{step.label}</div>
                  <div
                    className={cn(
                      "rounded-full px-2 py-px text-[9px] font-semibold tracking-wide uppercase",
                      ai ? "bg-violet-50 text-violet-600" : "bg-slate-100 text-slate-500"
                    )}>
                    {ai ? "AI" : "Rule"}
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
              startYOffset={-24}
              endYOffset={-24}
              pathColor="#cbd5e1"
              pathOpacity={0.45}
              gradientStartColor="#8b5cf6"
              gradientStopColor="#0ea5e9"
            />
          ))}
        </div>
      </div>

      {/* Step details — spread out, two columns */}
      <div className="mt-5 grid gap-x-8 gap-y-3 border-t border-border pt-4 sm:grid-cols-2">
        {trace.map((step) => {
          const ai = step.kind === "ai"
          return (
            <div key={step.agent} className="rounded-xl px-2 py-1.5 transition-colors hover:bg-secondary/50 sm:-mx-2">
              <div className="flex items-start gap-2.5">
              <span className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", ai ? "bg-violet-400" : "bg-slate-300")} />
              <div className="min-w-0 text-[12px] leading-relaxed">
                <span className="font-semibold">{step.label}</span>
                <span className="text-muted-foreground/70 tabular-nums">
                  {" · "}
                  {step.ms >= 1000 ? `${(step.ms / 1000).toFixed(1)}s` : `${step.ms}ms`}
                </span>
                <div className="text-muted-foreground">{step.summary}</div>
              </div>
              </div>
            </div>
          )
        })}
      </div>

      <p className="mt-4 text-center text-[11px] text-muted-foreground">
        Full pass in <span className="font-medium tabular-nums">{(totalMs / 1000).toFixed(1)}s</span> — deterministic
        gates run first, so AI reasoning is spent only where judgment matters.
      </p>
    </div>
  )
}
