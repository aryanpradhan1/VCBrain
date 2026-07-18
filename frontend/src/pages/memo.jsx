import { Link, useParams } from "react-router-dom"
import { motion } from "motion/react"
import {
  ArrowLeft,
  CircleCheck,
  ExternalLink,
  Flag,
  Quote,
  ShieldAlert,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ChannelBadge,
  ColdStartBadge,
  ConfidenceChip,
  RatingPill,
} from "@/components/shared/chips"
import { DecisionBar } from "@/components/shared/decision-bar"
import { Page, stagger } from "@/components/shared/page"
import { ScoreBadge } from "@/components/shared/score-badge"
import { scoreDot, verdictMeta } from "@/components/shared/semantics"
import { ErrorBanner } from "@/components/shared/states"
import { TrendArrow } from "@/components/shared/trend"
import { getOpportunity } from "@/lib/api"
import { useAsync } from "@/lib/use-async"
import { cn } from "@/lib/utils"

function Citations({ citations }) {
  if (!citations?.length) return null
  return (
    <ul className="mt-3 space-y-1.5 border-t border-border pt-3">
      {citations.map((c) => (
        <li key={c} className="flex gap-1.5 text-xs text-muted-foreground">
          <Quote className="mt-0.5 size-3 shrink-0 text-slate-300" />
          {c}
        </li>
      ))}
    </ul>
  )
}

// The three axes — equal width, never merged into one number.
function AxisCards({ opp }) {
  const axes = [
    {
      name: "Founder",
      head: (
        <span className="inline-flex items-center gap-1.5 tabular-nums">
          <span className={cn("size-2 rounded-full", scoreDot(opp.founder_axis.score))} />
          <span className="text-xl font-semibold tracking-tight">{opp.founder_axis.score}</span>
        </span>
      ),
      axis: opp.founder_axis,
    },
    { name: "Market", head: <RatingPill rating={opp.market_axis.rating} />, axis: opp.market_axis },
    {
      name: "Idea vs Market",
      head: <RatingPill rating={opp.idea_vs_market_axis.rating} />,
      axis: opp.idea_vs_market_axis,
    },
  ]
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {axes.map(({ name, head, axis }) => (
        <motion.div key={name} variants={stagger.item}>
          <Card className="h-full gap-3">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  {name}
                </CardTitle>
                <TrendArrow trend={axis.trend} withLabel />
              </div>
              <div className="pt-1">{head}</div>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-foreground/80">{axis.rationale}</p>
              <Citations citations={axis.citations} />
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}

// Per-claim trust — claim + evidence + confidence chip, never per-company.
function TrustList({ claims }) {
  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle>Trust Score — claim by claim</CardTitle>
      </CardHeader>
      <CardContent className="px-0">
        <ul>
          {claims.map((c, i) => (
            <li key={c.claim}>
              {i > 0 && <Separator />}
              <div className="flex items-start gap-4 px-5 py-3.5">
                <span className="w-28 shrink-0 pt-0.5 text-sm font-medium capitalize">
                  {c.claim.replaceAll("_", " ")}
                </span>
                <p className="flex-1 text-sm leading-relaxed text-foreground/80">{c.evidence}</p>
                <ConfidenceChip confidence={c.confidence} short />
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

const sectionTitles = {
  company_snapshot: "Company snapshot",
  investment_hypotheses: "Investment hypotheses",
  swot: "SWOT",
  problem_and_product: "Problem & product",
  traction_kpis: "Traction & KPIs",
}

function MemoSection({ title, children }) {
  return (
    <section>
      <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">{title}</h3>
      {children}
    </section>
  )
}

function Swot({ swot }) {
  const groups = Object.entries(swot ?? {})
  if (!groups.length) return <p className="text-sm text-muted-foreground">Not available.</p>
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {groups.map(([key, items]) => (
        <div key={key} className="rounded-xl bg-secondary/60 p-3.5">
          <div className="mb-1.5 text-xs font-semibold capitalize">{key}</div>
          <ul className="space-y-1">
            {(items ?? []).map((it) => (
              <li key={it} className="text-sm leading-snug text-foreground/80">
                {it}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

// Appendix 1: required fully populated; optional shown filled-or-flagged, never omitted.
function MemoCard({ memo }) {
  const { required, optional_or_flagged } = memo
  return (
    <Card className="gap-4">
      <CardHeader>
        <CardTitle>Investment memo</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <MemoSection title={sectionTitles.company_snapshot}>
          <p className="text-sm leading-relaxed text-foreground/80">{required.company_snapshot}</p>
        </MemoSection>

        <MemoSection title={sectionTitles.investment_hypotheses}>
          <ol className="list-decimal space-y-1.5 pl-4">
            {required.investment_hypotheses.map((h) => (
              <li key={h} className="text-sm leading-relaxed text-foreground/80">
                {h}
              </li>
            ))}
          </ol>
        </MemoSection>

        <MemoSection title={sectionTitles.swot}>
          <Swot swot={required.swot} />
        </MemoSection>

        <MemoSection title={sectionTitles.problem_and_product}>
          <p className="text-sm leading-relaxed text-foreground/80">{required.problem_and_product}</p>
        </MemoSection>

        <MemoSection title={sectionTitles.traction_kpis}>
          <p className="text-sm leading-relaxed text-foreground/80">{required.traction_kpis}</p>
        </MemoSection>

        <Separator />

        {Object.entries(optional_or_flagged ?? {}).map(([key, value]) => {
          const flagged = /not disclosed|flagged/i.test(value)
          return (
            <MemoSection key={key} title={key.replaceAll("_", " ")}>
              <p
                className={cn(
                  "flex items-start gap-1.5 text-sm leading-relaxed",
                  flagged ? "text-amber-700" : "text-foreground/80"
                )}>
                {flagged && <Flag className="mt-0.5 size-3.5 shrink-0" />}
                {value}
              </p>
            </MemoSection>
          )
        })}
      </CardContent>
    </Card>
  )
}

// Its own visually distinct panel — never a section inside the memo.
function AdversarialPanel({ challenges }) {
  if (!challenges?.length) return null
  return (
    <div className="rounded-2xl border border-amber-200/80 bg-amber-50/70 p-5">
      <div className="mb-2.5 flex items-center gap-2 text-amber-800">
        <ShieldAlert className="size-4" />
        <span className="text-sm font-semibold tracking-tight">Adversarial view — the case against</span>
      </div>
      <ul className="space-y-2">
        {challenges.map((c) => (
          <li key={c} className="flex gap-2 text-sm leading-relaxed text-amber-900/90">
            <span className="mt-2 size-1 shrink-0 rounded-full bg-amber-500" />
            {c}
          </li>
        ))}
      </ul>
    </div>
  )
}

function PortfolioCheck({ check }) {
  const Icon = check.overlap ? Flag : CircleCheck
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 rounded-xl px-4 py-3 text-sm",
        check.overlap ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"
      )}>
      <Icon className="size-4 shrink-0" />
      <span className="font-medium">{check.overlap ? "Portfolio overlap" : "No portfolio overlap"}</span>
      <span className={cn("truncate", check.overlap ? "text-red-600/80" : "text-emerald-700/70")}>
        {check.note}
      </span>
    </div>
  )
}

function MemoSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-24 rounded-2xl" />
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-48 rounded-2xl" />
        <Skeleton className="h-48 rounded-2xl" />
        <Skeleton className="h-48 rounded-2xl" />
      </div>
      <Skeleton className="h-64 rounded-2xl" />
    </div>
  )
}

export default function Memo() {
  const { id } = useParams()
  const { data: opp, error, loading, retry } = useAsync(() => getOpportunity(id), [id])

  return (
    <Page>
      <Link
        to="/"
        className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
        <ArrowLeft className="size-4" />
        Pipeline
      </Link>

      {error && <ErrorBanner message="Couldn't load this opportunity." onRetry={retry} />}
      {loading && <MemoSkeleton />}

      {opp && (
        <motion.div variants={stagger.container} initial="initial" animate="animate" className="space-y-4">
          <motion.div variants={stagger.item} className="flex flex-wrap items-end justify-between gap-4 pb-1">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-3xl font-semibold tracking-tight">{opp.company_name}</h1>
                <ChannelBadge channel={opp.sourcing_channel} />
                {opp.cold_start_flag && <ColdStartBadge />}
                <Badge variant={verdictMeta[opp.verdict].variant}>
                  Recommendation: {verdictMeta[opp.verdict].label}
                </Badge>
              </div>
              <Link
                to={`/founder/${opp.founder_id}`}
                className="mt-1.5 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
                What the founder sees
                <ExternalLink className="size-3" />
              </Link>
            </div>
            <div className="text-right">
              <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                Founder Score
              </div>
              <ScoreBadge score={opp.founder_score} size="md" animated />
            </div>
          </motion.div>

          <AxisCards opp={opp} />

          <motion.div variants={stagger.item}>
            <TrustList claims={opp.claim_trust} />
          </motion.div>

          <motion.div variants={stagger.item}>
            <MemoCard memo={opp.memo} />
          </motion.div>

          <motion.div variants={stagger.item}>
            <AdversarialPanel challenges={opp.adversarial_view.challenges} />
          </motion.div>

          <motion.div variants={stagger.item}>
            <PortfolioCheck check={opp.portfolio_check} />
          </motion.div>

          <motion.div variants={stagger.item}>
            <DecisionBar opportunity={opp} />
          </motion.div>
        </motion.div>
      )}
    </Page>
  )
}
