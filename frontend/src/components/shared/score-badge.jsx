import { cn } from "@/lib/utils"
import { CountUp } from "./count-up"
import { TrendArrow } from "./trend"

// The canonical Founder Score display: value ± interval + trend arrow.
// Identical semantics on dashboard rows, memo header, and founder results.
export function ScoreBadge({ score, size = "md", animated = false, className }) {
  const { value, confidence_interval, trend } = score
  const sizes = {
    sm: { value: "text-base", pm: "text-xs", arrow: "" },
    md: { value: "text-2xl", pm: "text-sm", arrow: "" },
    lg: { value: "text-7xl tracking-tighter", pm: "text-xl", arrow: "scale-[2] ml-4 mr-2" },
  }
  const s = sizes[size]

  return (
    <span className={cn("inline-flex items-baseline gap-1.5 tabular-nums", className)}>
      <span className={cn("font-semibold tracking-tight", s.value)}>
        {animated ? <CountUp value={value} /> : value}
      </span>
      <span className={cn("font-medium text-muted-foreground", s.pm)}>
        ± {confidence_interval}
      </span>
      <TrendArrow trend={trend} className={s.arrow} />
    </span>
  )
}
