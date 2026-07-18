import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { motion } from "motion/react"
import {
  ArrowLeft,
  Brain,
  ChartPie,
  CircleCheck,
  ExternalLink,
  FileText,
  Flag,
  Lightbulb,
  MapPin,
  Newspaper,
  Quote,
  Printer,
  ShieldAlert,
  ShieldCheck,
  Users,
  Workflow,
} from "lucide-react"
import { FaGithub, FaGlobe, FaLinkedinIn, FaXTwitter } from "react-icons/fa6"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { BorderBeam } from "@/components/magicui/border-beam"
import { AgentPipeline } from "@/components/shared/agent-pipeline"
import { MarketChart, ScoreFormulaBar } from "@/components/shared/charts"
import { ChannelBadge, ColdStartBadge, RatingPill } from "@/components/shared/chips"
import { DecisionBar } from "@/components/shared/decision-bar"
import { Page, stagger } from "@/components/shared/page"
import { ScoreRing } from "@/components/shared/score-ring"
import { Expandable, Section } from "@/components/shared/section"
import { avatarGradient, scoreDot, verdictMeta } from "@/components/shared/semantics"
import { SignalChips } from "@/components/shared/signal-chips"
import { useSources } from "@/components/shared/source-drawer"
import { ErrorBanner } from "@/components/shared/states"
import { TrendArrow } from "@/components/shared/trend"
import { getOpportunity } from "@/lib/api"
import { useAsync } from "@/lib/use-async"
import { cn } from "@/lib/utils"

// ── Clickable citations — every source leads somewhere ────────────────────
function CitationChips({ citations, opp }) {
  const { open } = useSources()
  if (!citations?.length) return null
  return (
    <div className="mt-3 flex flex-wrap gap-1.5 border-t border-border pt-3">
      {citations.map((c) => (
        <button
          key={c}
          type="button"
          onClick={() => open({ citation: c, opp })}
          className="inline-flex max-w-full cursor-pointer items-center gap-1.5 rounded-full bg-secondary/70 px-2.5 py-1 text-[11px] font-medium text-foreground/70 transition-colors hover:bg-secondary hover:text-foreground"
          title={`Open source: ${c}`}>
          <Quote className="size-3 shrink-0 text-muted-foreground" />
          <span className="truncate">{c}</span>
        </button>
      ))}
    </div>
  )
}

// ── Rail ──────────────────────────────────────────────────────────────────
function SummaryRail({ opp }) {
  const e = opp.enrichment
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
        {e && <p className="mt-1 text-[13px] leading-snug text-muted-foreground">{e.one_liner}</p>}

        {e && (
          <div className="mt-2.5 flex flex-wrap items-center justify-center gap-1.5 text-[11px] font-medium text-muted-foreground">
            <Badge variant="outline">{e.sector}</Badge>
            <Badge variant="outline">{e.stage}</Badge>
            <span className="inline-flex items-center gap-0.5">
              <MapPin className="size-3" />
              {e.geography}
            </span>
          </div>
        )}

        <div className="mt-2 flex flex-wrap items-center justify-center gap-1.5">
          <Badge variant={verdictMeta[opp.verdict].variant}>{verdictMeta[opp.verdict].label}</Badge>
          <ChannelBadge channel={opp.sourcing_channel} />
          {opp.cold_start_flag && <ColdStartBadge />}
        </div>

        <div className="my-4 flex flex-col items-center">
          <div className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">
            Founder Score
          </div>
          <span title="Reported as value ± confidence interval — the band narrows as independent evidence corroborates. Never resets across applications.">
            <ScoreRing score={opp.founder_score} />
          </span>
          <div className="text-[10px] text-muted-foreground">
            <TrendArrow trend={opp.founder_score.trend} withLabel /> · persistent, cross-application
          </div>
        </div>

        <div className="w-full space-y-3 text-left">
          {opp.thesis && (
            <div className="rounded-xl bg-secondary/60 px-3.5 py-3">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold">
                <CircleCheck className={cn("size-3.5", opp.thesis.thesis_match ? "text-emerald-500" : "text-red-400")} />
                Thesis {opp.thesis.thesis_match ? "match" : "miss"}
                <span className="ml-auto rounded-full bg-card px-1.5 py-px text-[9px] font-semibold text-muted-foreground uppercase">
                  {opp.thesis.match_type === "exact" ? "rule gate" : "LLM judged"}
                </span>
              </div>
              <p className="mt-1 text-[11px] leading-snug text-muted-foreground">{opp.thesis.rationale}</p>
            </div>
          )}

          <div>
            <div className="mb-1.5 text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">
              Public signals
            </div>
            <SignalChips signals={opp.public_signals} />
          </div>

          <PortfolioCheck check={opp.portfolio_check} />

          <div className="flex items-center justify-between border-t border-border pt-3">
            {e?.website && (
              <a
                href={e.website}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-sky-700 hover:underline">
                <FaGlobe className="size-3" />
                {e.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
              </a>
            )}
            <Link
              to={`/founder/${opp.founder_id}`}
              className="inline-flex items-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground">
              Founder view
              <ExternalLink className="size-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Snapshot: problem / solution / PMF ────────────────────────────────────
const pmfMeta = {
  strong: { label: "Strong signal", variant: "positive" },
  early: { label: "Early / unproven", variant: "caution" },
  weak: { label: "Weak signal", variant: "negative" },
}

function Snapshot({ e }) {
  if (!e) return null
  const pmf = pmfMeta[e.pmf?.signal] ?? pmfMeta.early
  const cards = [
    { title: "Problem", body: e.problem },
    { title: "Solution", body: e.solution },
  ]
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {cards.map((c) => (
        <div key={c.title} className="rounded-2xl bg-card p-4 card-hairline">
          <div className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">{c.title}</div>
          <p className="mt-1.5 text-sm leading-relaxed">{c.body}</p>
        </div>
      ))}
      <div className="rounded-2xl bg-card p-4 card-hairline">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">
            Product-market fit
          </span>
          <Badge variant={pmf.variant}>{pmf.label}</Badge>
        </div>
        <p className="mt-1.5 text-sm leading-relaxed">{e.pmf?.note}</p>
      </div>
    </div>
  )
}

// ── Founders ──────────────────────────────────────────────────────────────
function SocialIcon({ href, icon: Icon, label }) {
  if (!href) return null
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      title={label}
      className="flex size-7 items-center justify-center rounded-full bg-secondary text-muted-foreground transition-all hover:scale-110 hover:bg-slate-900 hover:text-white">
      <Icon className="size-3.5" />
    </a>
  )
}

function FounderCard({ founder }) {
  return (
    <div className="flex gap-4 rounded-2xl bg-card p-4 card-hairline">
      <img
        src={founder.avatar}
        alt={founder.name}
        loading="lazy"
        className="size-16 shrink-0 rounded-xl object-cover shadow-sm"
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span className="text-sm font-semibold tracking-tight">{founder.name}</span>
          <span className="text-[11px] font-medium text-muted-foreground">{founder.role}</span>
          <div className="ml-auto flex gap-1">
            <SocialIcon href={founder.linkedin} icon={FaLinkedinIn} label="LinkedIn" />
            <SocialIcon href={founder.github} icon={FaGithub} label="GitHub" />
            <SocialIcon href={founder.x} icon={FaXTwitter} label="X" />
          </div>
        </div>
        <p className="mt-1 text-[13px] leading-relaxed text-foreground/75">{founder.background}</p>
        {founder.ai_read && (
          <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-violet-50/70 px-2.5 py-2">
            <ShieldCheck className="mt-0.5 size-3 shrink-0 text-violet-500" />
            <p className="text-[11px] leading-snug text-violet-900/80">
              <span className="font-semibold">AI verified: </span>
              {founder.ai_read}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Axes ──────────────────────────────────────────────────────────────────
function AxisCards({ opp }) {
  const axes = [
    {
      name: "Founder",
      head: (
        <span className="inline-flex items-baseline gap-1.5 tabular-nums" title="0–100, AI-scored from verified track record and fit">
          <span className={cn("self-center size-2 rounded-full", scoreDot(opp.founder_axis.score))} />
          <span className="text-xl font-semibold tracking-tight">{opp.founder_axis.score}</span>
          <span className="text-[10px] text-muted-foreground">/ 100</span>
        </span>
      ),
      axis: opp.founder_axis,
    },
    { name: "Market", head: <RatingPill rating={opp.market_axis.rating} />, axis: opp.market_axis },
    { name: "Idea vs Market", head: <RatingPill rating={opp.idea_vs_market_axis.rating} />, axis: opp.idea_vs_market_axis },
  ]
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      {axes.map(({ name, head, axis }) => (
        <Card key={name} className="h-full gap-3">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{name}</CardTitle>
              <TrendArrow trend={axis.trend} withLabel />
            </div>
            <div className="pt-1">{head}</div>
          </CardHeader>
          <CardContent>
            <Expandable lines={3}>
              <p className="text-sm leading-relaxed text-foreground/80">{axis.rationale}</p>
            </Expandable>
            <CitationChips citations={axis.citations} opp={opp} />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ── Trust ─────────────────────────────────────────────────────────────────
const confidenceBar = {
  high: { filled: 3, cls: "bg-emerald-500", label: "high" },
  medium: { filled: 2, cls: "bg-amber-400", label: "medium" },
  low: { filled: 1, cls: "bg-red-400", label: "low" },
}

function ConfidenceMeter({ confidence }) {
  const meta = confidenceBar[confidence] ?? confidenceBar.medium
  return (
    <span
      className="inline-flex flex-col items-end gap-1"
      title={`${meta.label} confidence — how well this claim held up against independent evidence`}>
      <span className="flex gap-0.5">
        {[0, 1, 2].map((i) => (
          <span key={i} className={cn("h-1.5 w-4 rounded-full", i < meta.filled ? meta.cls : "bg-slate-200")} />
        ))}
      </span>
      <span className="text-[10px] font-medium text-muted-foreground capitalize">{meta.label}</span>
    </span>
  )
}

function TrustList({ claims, opp }) {
  const { open } = useSources()
  return (
    <Card className="gap-0 py-0">
      <CardContent className="px-0">
        <ul>
          {claims.map((c, i) => (
            <li key={c.claim}>
              {i > 0 && <Separator />}
              <button
                type="button"
                onClick={() => open({ citation: `${c.claim}: ${c.evidence}`, opp })}
                className="flex w-full cursor-pointer items-start gap-4 px-5 py-3.5 text-left transition-colors hover:bg-secondary/40">
                <span className="w-24 shrink-0 pt-0.5 text-sm font-medium capitalize">{c.claim.replaceAll("_", " ")}</span>
                <p className="flex-1 text-sm leading-relaxed text-foreground/80">{c.evidence}</p>
                <ConfidenceMeter confidence={c.confidence} />
              </button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

// ── Memo (collapsed by default) ───────────────────────────────────────────
const swotMeta = {
  strengths: { cls: "bg-emerald-50/80 text-emerald-900" },
  weaknesses: { cls: "bg-red-50/70 text-red-900" },
  opportunities: { cls: "bg-sky-50/80 text-sky-900" },
  threats: { cls: "bg-amber-50/80 text-amber-900" },
}

function MemoBody({ memo, expanded = false }) {
  const { required, optional_or_flagged } = memo
  const [full, setFull] = useState(false)
  const showFull = expanded || full
  return (
    <Card className="gap-4">
      <CardContent className="space-y-5 pt-5">
        <div>
          <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">Investment hypotheses</h3>
          <ol className="space-y-2">
            {required.investment_hypotheses.map((h, i) => (
              <li key={h} className="flex gap-2.5 text-sm leading-relaxed text-foreground/80">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-secondary text-[11px] font-semibold">
                  {i + 1}
                </span>
                {h}
              </li>
            ))}
          </ol>
        </div>

        <div>
          <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">SWOT</h3>
          <div className="grid gap-2.5 sm:grid-cols-2">
            {Object.entries(required.swot ?? {}).map(([key, items]) => (
              <div key={key} className={cn("rounded-xl p-3", (swotMeta[key] ?? swotMeta.strengths).cls)}>
                <div className="mb-1 text-[11px] font-semibold capitalize">{key}</div>
                <ul className="space-y-1">
                  {(items ?? []).map((it) => (
                    <li key={it} className="text-[12px] leading-snug opacity-85">{it}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {showFull && (
          <>
            <div>
              <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">Company snapshot</h3>
              <p className="text-sm leading-relaxed text-foreground/80">{required.company_snapshot}</p>
            </div>
            <div>
              <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">Problem & product</h3>
              <p className="text-sm leading-relaxed text-foreground/80">{required.problem_and_product}</p>
            </div>
            <div>
              <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">Traction & KPIs</h3>
              <p className="text-sm leading-relaxed text-foreground/80">{required.traction_kpis}</p>
            </div>
            <Separator />
            {Object.entries(optional_or_flagged ?? {}).map(([key, value]) => {
              const flagged = /not disclosed|flagged|unavailable/i.test(value)
              return (
                <div key={key}>
                  <h3 className="mb-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                    {key.replaceAll("_", " ")}
                  </h3>
                  <p className={cn("flex items-start gap-1.5 text-sm leading-relaxed", flagged ? "text-amber-700" : "text-foreground/80")}>
                    {flagged && <Flag className="mt-0.5 size-3.5 shrink-0" />}
                    {value}
                  </p>
                </div>
              )
            })}
          </>
        )}

        <button
          type="button"
          onClick={() => setFull((f) => !f)}
          className="memo-expand-control text-xs font-medium text-muted-foreground underline underline-offset-4 transition-colors hover:text-foreground">
          {showFull ? "Collapse memo" : "Read the full Appendix-1 memo"}
        </button>
      </CardContent>
    </Card>
  )
}

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
        "flex items-start gap-2 rounded-xl px-3.5 py-3 text-[12px] leading-snug",
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

function NewsList({ news, opp }) {
  const { open } = useSources()
  if (!news?.length)
    return <p className="text-[11px] text-muted-foreground">No press coverage found — noted honestly, not padded.</p>
  return (
    <ul className="space-y-1.5">
      {news.map((n) => (
        <li key={n.title}>
          <button
            type="button"
            onClick={() => open({ type: "news", title: n.title, newsSource: n.source, date: n.date, opp })}
            className="group flex w-full cursor-pointer items-center gap-2 text-left">
            <Newspaper className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate text-[13px] font-medium group-hover:underline">{n.title}</span>
            <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">
              {n.source} · {n.date}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function MemoSkeleton() {
  return (
    <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
      <Skeleton className="h-[480px] rounded-2xl" />
      <div className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
          <Skeleton className="h-28 rounded-2xl" />
        </div>
        <Skeleton className="h-48 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    </div>
  )
}

export default function Memo() {
  const { id } = useParams()
  const { data: opp, error, loading, retry } = useAsync(() => getOpportunity(id), [id])
  const e = opp?.enrichment
  const [printing, setPrinting] = useState(false)

  useEffect(() => {
    if (!printing || !opp) return undefined

    const originalTitle = document.title
    document.title = `${opp.company_name} — FounderScore investment brief`
    const openPrintDialog = () => {
      window.print()
      document.title = originalTitle
      setPrinting(false)
    }
    const frame = requestAnimationFrame(() => requestAnimationFrame(openPrintDialog))
    return () => cancelAnimationFrame(frame)
  }, [printing, opp])

  return (
    <Page>
      <div className="print-hidden mb-4 flex flex-wrap items-center justify-between gap-3">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
        <ArrowLeft className="size-4" />
        Pipeline
      </Link>
      {opp && (
        <Button variant="outline" size="sm" onClick={() => setPrinting(true)} className="rounded-full px-3 shadow-sm">
          <Printer data-icon="inline-start" />
          Export investment brief
        </Button>
      )}
      </div>

      {error && <ErrorBanner message="Couldn't load this opportunity." onRetry={retry} />}
      {loading && <MemoSkeleton />}

      {opp && (
        <div className="memo-document grid items-start gap-5 lg:grid-cols-[300px_1fr]">
          <header className="memo-print-heading">
            <div className="memo-print-brand">FounderScore <span>· Investment brief</span></div>
            <div className="memo-print-company">{opp.company_name}</div>
            <div className="memo-print-meta">Prepared for Maschmeyer Group · Confidential</div>
          </header>
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="memo-summary-rail lg:sticky lg:top-8">
            <SummaryRail opp={opp} />
          </motion.div>

          <motion.div variants={stagger.container} initial="initial" animate="animate" className="min-w-0 space-y-7">
            <motion.div variants={stagger.item}>
              <Section icon={Lightbulb} title="At a glance">
                <Snapshot e={e} />
              </Section>
            </motion.div>

            {e?.agent_trace && (
              <motion.div variants={stagger.item}>
                <Section
                  icon={Workflow}
                  title="How this was produced"
                  sub="Six agents, in order — deterministic gates vs. AI reasoning, labeled honestly">
                  <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
                    <div className="rounded-2xl bg-card p-5 card-hairline">
                      <AgentPipeline trace={e.agent_trace} />
                    </div>
                    <div className="rounded-2xl bg-card p-4 card-hairline">
                      <div className="mb-2 text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">
                        The Founder Score formula
                      </div>
                      <ScoreFormulaBar />
                    </div>
                  </div>
                </Section>
              </motion.div>
            )}

            {e?.founders && (
              <motion.div variants={stagger.item}>
                <Section
                  icon={Users}
                  title="Founders"
                  sub="Backgrounds cross-referenced against LinkedIn, GitHub, press and registries">
                  <div className={cn("grid gap-3", e.founders.length > 1 && "md:grid-cols-2")}>
                    {e.founders.map((f) => (
                      <FounderCard key={f.name} founder={f} />
                    ))}
                  </div>
                </Section>
              </motion.div>
            )}

            <motion.div variants={stagger.item}>
              <Section
                icon={Brain}
                title="AI assessment"
                sub="Three independent axes — never averaged into one number"
                right={<Badge variant={verdictMeta[opp.verdict].variant}>Recommendation: {verdictMeta[opp.verdict].label}</Badge>}>
                <AxisCards opp={opp} />
              </Section>
            </motion.div>

            {e?.market && (
              <motion.div variants={stagger.item}>
                <Section
                  icon={ChartPie}
                  title="Market"
                  sub="Sizing re-derived by Diligence — not taken from the deck at face value"
                  right={<RatingPill rating={opp.market_axis.rating} />}>
                  <div className="rounded-2xl bg-card p-5 card-hairline">
                    <MarketChart market={e.market} />
                    <Separator className="my-4" />
                    <div className="mb-1.5 text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">
                      Coverage
                    </div>
                    <NewsList news={e.news} opp={opp} />
                  </div>
                </Section>
              </motion.div>
            )}

            <motion.div variants={stagger.item}>
              <Section
                icon={ShieldCheck}
                title="Evidence & trust"
                sub="Per-claim confidence — click any row to open its evidence trail">
                <TrustList claims={opp.claim_trust} opp={opp} />
              </Section>
            </motion.div>

            <motion.div variants={stagger.item}>
              <Section icon={FileText} title="Investment memo" sub="Appendix-1 structure — flagged fields never fabricated">
                <MemoBody memo={opp.memo} expanded={printing} />
              </Section>
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
