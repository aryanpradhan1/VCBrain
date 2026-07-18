import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react"

import { cn } from "@/lib/utils"
import { trendMeta } from "./semantics"

const icons = { improving: ArrowUpRight, stable: ArrowRight, declining: ArrowDownRight }

export function TrendArrow({ trend, withLabel = false, className }) {
  const Icon = icons[trend] ?? ArrowRight
  const meta = trendMeta[trend] ?? trendMeta.stable
  return (
    <span className={cn("inline-flex items-center gap-0.5", meta.cls, className)}>
      <Icon className="size-3.5" strokeWidth={2.25} aria-label={meta.label} />
      {withLabel && <span className="text-xs font-medium">{meta.label}</span>}
    </span>
  )
}
