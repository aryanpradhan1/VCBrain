import { useNavigate, useParams } from "react-router-dom"
import { motion } from "motion/react"
import { MessageCircle } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { DotPattern } from "@/components/magicui/dot-pattern"
import { ShimmerButton } from "@/components/magicui/shimmer-button"
import { AnimatedShinyText } from "@/components/magicui/animated-shiny-text"
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
    <div className="relative min-h-dvh overflow-hidden">
      <DotPattern
        width={22}
        height={22}
        cr={1}
        className="text-slate-300/60 mask-[radial-gradient(480px_circle_at_center,white,transparent)]"
      />
      <Page className="relative mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center px-6 py-16 text-center">
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
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
              <AnimatedShinyText className="text-sm font-medium tracking-wide uppercase">
                Your Founder Score
              </AnimatedShinyText>
            </motion.div>

            <div className="mt-4 flex items-baseline gap-3 tabular-nums">
              <span className="bg-gradient-to-b from-slate-900 to-slate-600 bg-clip-text text-8xl font-semibold tracking-tighter text-transparent">
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
              <ShimmerButton
                onClick={() => navigate(`/founder/${id}/interview`)}
                background="oklch(0.19 0.01 255)"
                className="gap-2 px-7 py-3 text-sm font-semibold shadow-lg">
                <MessageCircle className="size-4" />
                Start interview
              </ShimmerButton>
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
