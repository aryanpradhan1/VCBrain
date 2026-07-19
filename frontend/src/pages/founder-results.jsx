import { useNavigate, useParams } from "react-router-dom"
import { motion } from "motion/react"
import { MessageCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { CountUp } from "@/components/shared/count-up"
import { Page } from "@/components/shared/page"
import { ErrorBanner } from "@/components/shared/states"
import { TrendArrow } from "@/components/shared/trend"
import { getFounderResults } from "@/lib/api"
import { useAsync } from "@/lib/use-async"

// The founder sees exactly this: score ± interval, trend, narrative. Nothing else, ever.
export default function FounderResults() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, error, loading, retry } = useAsync(() => getFounderResults(id), [id])
  return (
    <div className="min-h-dvh bg-slate-50/60">
      <Page className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center px-6 py-16 text-center">
        {error && <ErrorBanner message="Couldn't load your results just now." onRetry={retry} className="text-left" />}

        {loading && (
          <div className="flex w-full flex-col items-center gap-6">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-20 w-48" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}

        {data && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }} className="text-[11px] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
              Your Founder Score
            </motion.div>

            <div className="mt-4 flex items-baseline gap-3 tabular-nums">
              <span className="text-8xl font-semibold tracking-tighter text-slate-900">
                <CountUp value={data.founder_score.value} duration={1.4} delay={0.2} />
              </span>
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
                className="text-2xl font-medium text-muted-foreground">
                ± {data.founder_score.confidence_interval}
              </motion.span>
            </div>

            <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.35 }}>
              <TrendArrow trend={data.founder_score.trend} withLabel className="mt-2 [&_svg]:size-4 [&_span]:text-sm" />
            </motion.div>

            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.55, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="mt-8 text-[15px] leading-relaxed text-foreground/75">
              {data.narrative}
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.85, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="mt-10 flex flex-col items-center">
              <Button
                onClick={() => navigate(`/founder/${id}/interview`)}
                size="lg"
                className="gap-2 rounded-lg px-5 text-sm font-semibold shadow-sm">
                <MessageCircle className="size-4" />
                Start interview
              </Button>
              <p className="mt-3 text-xs text-muted-foreground">
                A short conversation that sharpens your score — it never resets.
              </p>
            </motion.div>
          </>
        )}
      </Page>
    </div>
  )
}
