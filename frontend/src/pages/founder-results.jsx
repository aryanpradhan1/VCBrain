import { Link, useParams } from "react-router-dom"
import { motion } from "motion/react"
import { MessageCircle, Sparkles, TrendingUp } from "lucide-react"

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
  const { data, error, loading, retry } = useAsync(() => getFounderResults(id), [id])
  return (
    <div className="min-h-dvh bg-gradient-to-br from-slate-50 via-slate-50/80 to-blue-50/40">
      <Page className="mx-auto flex min-h-dvh max-w-2xl flex-col items-center justify-center px-6 py-16 text-center">
        {error && <ErrorBanner message="Couldn't load your results just now." onRetry={retry} className="text-left" />}

        {loading && (
          <div className="flex w-full flex-col items-center gap-6">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-20 w-48" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}

        {data && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="w-full">
            {/* Main Score Card */}
            <div className="relative overflow-hidden rounded-3xl bg-white/80 backdrop-blur-sm border border-slate-200/60 shadow-xl shadow-slate-900/5 p-12">
              {/* Decorative gradient */}
              <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 via-transparent to-violet-50/30 pointer-events-none" />

              <div className="relative">
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.4 }}
                  className="inline-flex items-center gap-2 rounded-full bg-blue-50/80 px-4 py-1.5 text-xs font-semibold tracking-wide text-blue-700 uppercase border border-blue-100">
                  <Sparkles className="size-3.5" />
                  Your Founder Score
                </motion.div>

                <div className="mt-8 flex items-baseline justify-center gap-3 tabular-nums">
                  <span className="text-9xl font-bold tracking-tighter bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 bg-clip-text text-transparent">
                    <CountUp value={data.founder_score.value} duration={1.6} delay={0.3} />
                  </span>
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.4 }}
                    className="text-3xl font-semibold text-slate-400">
                    ± {data.founder_score.confidence_interval}
                  </motion.span>
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.5 }}
                  className="mt-4">
                  <TrendArrow trend={data.founder_score.trend} withLabel className="justify-center [&_svg]:size-5 [&_span]:text-base [&_span]:font-medium" />
                </motion.div>

                <motion.p
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.7, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                  className="mx-auto mt-10 max-w-lg text-base leading-relaxed text-slate-600">
                  {data.narrative}
                </motion.p>
              </div>
            </div>

            {/* CTA Section */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 2, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="mt-8 space-y-4">

              <Button
                asChild
                size="lg"
                className="group relative h-14 gap-3 overflow-hidden rounded-2xl bg-gradient-to-r from-blue-600 to-violet-600 px-8 text-base font-semibold shadow-lg shadow-blue-500/25 transition-all hover:shadow-xl hover:shadow-blue-500/30 hover:scale-[1.02] active:scale-[0.98]">
                <Link to={`/founder/${id}/interview`}>
                  <MessageCircle className="size-5 transition-transform group-hover:scale-110" />
                  Start Interview
                  <TrendingUp className="size-4 opacity-60 transition-all group-hover:opacity-100 group-hover:translate-x-0.5" />
                </Link>
              </Button>

              <p className="text-sm text-slate-500">
                A short 5-question conversation that can improve your score
              </p>

              {/* Info Cards */}
              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 2.2 }}
                  className="rounded-xl bg-slate-50/60 border border-slate-200/40 p-4 text-left">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">How it works</div>
                  <div className="mt-1.5 text-sm text-slate-600">Answer questions about your startup to demonstrate execution ability</div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 2.3 }}
                  className="rounded-xl bg-blue-50/40 border border-blue-200/40 p-4 text-left">
                  <div className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Score impact</div>
                  <div className="mt-1.5 text-sm text-slate-600">Strong responses can boost your score — it never decreases</div>
                </motion.div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </Page>
    </div>
  )
}
