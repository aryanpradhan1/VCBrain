import { motion } from "motion/react"

import { cn } from "@/lib/utils"
import { CountUp } from "./count-up"
import { TrendArrow } from "./trend"

const ringColor = (v) => (v >= 70 ? "stroke-emerald-500" : v >= 50 ? "stroke-slate-400" : "stroke-red-400")

// Radial Founder Score gauge: solid arc = value, faint wider arc = confidence interval band.
export function ScoreRing({ score, size = 148, className }) {
  const { value, confidence_interval, trend } = score
  const stroke = 9
  const r = (size - stroke * 2) / 2
  const c = 2 * Math.PI * r
  const frac = Math.min(value / 100, 1)
  const bandFrac = Math.min((value + confidence_interval) / 100, 1)

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className="stroke-slate-100" />
        {/* confidence band */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          className={cn(ringColor(value), "opacity-20")}
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - bandFrac) }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          className={ringColor(value)}
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - frac) }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-semibold tracking-tighter tabular-nums">
          <CountUp value={value} />
        </span>
        <span className="mt-0.5 flex items-center gap-1 text-xs font-medium text-muted-foreground tabular-nums">
          ± {confidence_interval}
          <TrendArrow trend={trend} className="[&_svg]:size-3" />
        </span>
      </div>
    </div>
  )
}
