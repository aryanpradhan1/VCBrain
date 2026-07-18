import { Link, useParams } from "react-router-dom"
import { motion } from "motion/react"
import {
  AlertTriangle,
  ArrowLeft,
  CircleCheck,
  ExternalLink,
  FileText,
  Flag,
  GitBranch,
  Lightbulb,
  Link2,
  MessageCircle,
  Minus,
  Plus,
  ShieldAlert,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { BorderBeam } from "@/components/magicui/border-beam"
import { ChannelBadge, ColdStartBadge, RatingPill } from "@/components/shared/chips"
import { DecisionBar } from "@/components/shared/decision-bar"
import { Page, stagger } from "@/components/shared/page"
import { ScoreRing } from "@/components/shared/score-ring"
import { SignalChips } from "@/components/shared/signal-chips"
import { avatarGradient, scoreDot, verdictMeta } from "@/components/shared/semantics"
import { ErrorBanner } from "@/components/shared/states"
import { TrendArrow } from "@/components/shared/trend"
import { getOpportunity } from "@/lib/api"
import { useAsync } from "@/lib/use-async"
import { cn } from "@/lib/utils"

function citationIcon(text) {
  if (/github/i.test(text)) return GitBranch
  if (/deck|slide/i.test(text)) return FileText
  if (/interview/i.test(text)) return MessageCircle
  return Link2
}

function CitationChips({ citations }) {
  if (!citations?.length) return null
  return (
    <div className="mt-3 flex flex-wrap gap-1.5 border-t border-border pt-3">
      {citations.map((c) => {
        const Icon = citationIcon(c)
        return (
          <span
            key={c}
            className="inline-flex max-w-full items-center gap-1.5 rounded-full bg-secondary/70 px-2.5 py-1 text-[11px] font-medium text-foreground/70"
            title={c}>
            <Icon className="size-3 shrink-0 text-muted-foreground" />
            <span className="truncate">{c}</span>
          </span>
        )
      })}
    </div>
  )
}

// The three axes — equal treatment, never merged into one number.
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
    <div className="grid gap-4 xl:grid-cols-3">
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
              <CitationChips citations={axis.citations} />
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}

const confidenceBar = {
  high: { filled: 3, cls: "bg-emerald-500", label: "high" },
  medium: { filled: 2, cls: "bg-amber-400", label: "medium" },
  low: { filled: 1, cls: "bg-red-400", label: "low" },
}

function ConfidenceMeter({ confidence }) {
  const meta = confidenceBar[confidence] ?? confidenceBar.medium
  return (
    <span className="inline-flex flex-col items-end gap-1" title={`${meta.label} confidence`}>
      <span className="flex gap-0.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className={cn("h-1.5 w-4 rounded-full", i < meta.filled ? meta.cls : "bg-slate-200")}
          />
        ))}
      </span>
      <span className="text-[10px] font-medium text-muted-foreground capitalize">{meta.label}</span>
    </span>
  )
}

// Per-claim trust — claim + evidence + confidence meter, never per-company.
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
                <span className="w-24 shrink-0 pt-0.5 text-sm font-medium capitalize">
                  {c.claim.replaceAll("_", " ")}
                </span>
                <p className="flex-1 text-sm leading-relaxed text-foreground/80">{c.evidence}</p>
                <ConfidenceMeter confidence={c.confidence} />
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

const swotMeta = {
  strengths: { icon: Plus, cls: "bg-emerald-50/80 text-emerald-900", chip: "text-emerald-600" },
  weaknesses: { icon: Minus, cls: "bg-red-50/70 text-red-900", chip: "text-red-500" },
  opportunities: { icon: Lightbulb, cls: "bg-sky-50/80 text-sky-900", chip: "text-sky-600" },
  threats: { icon: AlertTriangle, cls: "bg-amber-50/80 text-amber-900", chip: "text-amber-600" },
}

function Swot({ swot }) {
  const groups = Object.entries(swot ?? {})
  if (!groups.length) return <p className="text-sm text-muted-foreground">Not available.</p>
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {groups.map(([key, items]) => {
        const meta = swotMeta[key] ?? swotMeta.strengths
        const Icon = meta.icon
        return (
          <div key={key} className={cn("rounded-xl p-3.5", meta.cls)}>
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold capitalize">
              <Icon className={cn("size-3.5", meta.chip)} strokeWidth={2.4} />
              {key}
            </div>
            <ul className="space-y-1.5">
              {(items ?? []).map((it) => (
                <li key={it} className="text-[13px] leading-snug opacity-85">
                  {it}
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
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
          <ol className="space-y-2">
            {required.investment_hypotheses.map((h, i) => (
              <li key={h} className="flex gap-2.5 text-sm leading-relaxed text-foreground/80">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-secondary text-[11px] font-semibold text-secondary-foreground">
                  {i + 1}
                </span>
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
        "flex items-start gap-2 rounded-xl px-3.5 py-3 text-[13px] leading-snug",
        check.overlap ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"
      )}>
      <Icon className="mt-0.5 size-4 shrink-0" />
      <div>
        <div className="font-semibold">{check.overlap ? "Portfolio overlap" : "No portfolio overlap"}</div>
        <div className={check.overlap ? "text-red-600/80" : "text-emerald-700/70"}>{check.note}</div>
      </div>
    </div>
  )
}

function SummaryRail({ opp }) {
  const approved = opp.verdict === "approve"
  return (
    <div className="relative overflow-hidden rounded-2xl bg-card p-5 card-hairline">
      {approved && <BorderBeam size={70} duration={7} colorFrom="#10b981" colorTo="#2dd4bf" />}
      <div className="flex flex-col items-center text-center">
        <span
          className={cn(
            "mb-3 flex size-12 items-center justify-center rounded-xl bg-gradient-to-br text-base font-bold text-white shadow-sm",
            avatarGradient(opp.company_name)
          )}>
          {opp.company_name[0]}
        </span>
        <h1 className="text-lg font-semibold tracking-tight">{opp.company_name}</h1>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-1.5">
          <Badge variant={verdictMeta[opp.verdict].variant}>{verdictMeta[opp.verdict].label}</Badge>
          <ChannelBadge channel={opp.sourcing_channel} />
        </div>
        {opp.cold_start_flag && (
          <div className="mt-1.5">
            <ColdStartBadge />
          </div>
        )}
        <div className="my-4">
          <ScoreRing score={opp.founder_score} />
        </div>
        <div className="w-full space-y-3 text-left">
          <div>
            <div className="mb-1.5 text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">
              Public signals
            </div>
            <SignalChips signals={opp.public_signals} />
          </div>
          <PortfolioCheck check={opp.portfolio_check} />
          <Link
            to={`/founder/${opp.founder_id}`}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground">
            What the founder sees
            <ExternalLink className="size-3" />
          </Link>
        </div>
      </div>
    </div>
  )
}

function MemoSkeleton() {
  return (
    <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
      <Skeleton className="h-[420px] rounded-2xl" />
      <div className="space-y-4">
        <div className="grid gap-4 xl:grid-cols-3">
          <Skeleton className="h-48 rounded-2xl" />
          <Skeleton className="h-48 rounded-2xl" />
          <Skeleton className="h-48 rounded-2xl" />
        </div>
        <Skeleton className="h-64 rounded-2xl" />
      </div>
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
        <div className="grid items-start gap-5 lg:grid-cols-[300px_1fr]">
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="lg:sticky lg:top-8">
            <SummaryRail opp={opp} />
          </motion.div>

          <motion.div variants={stagger.container} initial="initial" animate="animate" className="min-w-0 space-y-4">
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
              <DecisionBar opportunity={opp} />
            </motion.div>
          </motion.div>
        </div>
      )}
    </Page>
  )
}
