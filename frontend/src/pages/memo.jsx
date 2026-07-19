import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { motion } from "motion/react"
import {
  ArrowLeft,
  Brain,
  ChartPie,
  Calculator,
  CircleCheck,
  ExternalLink,
  FileText,
  Flag,
  GitBranch,
  Gauge,
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
import { AgentPipeline } from "@/components/shared/agent-pipeline"
import { DecisionLandscape, EvidenceCoverageChart, MarketChart, ScoreFormulaBar } from "@/components/shared/charts"
import { ChannelBadge, ColdStartBadge, RatingPill } from "@/components/shared/chips"
import { DecisionBar } from "@/components/shared/decision-bar"
import { Page, stagger } from "@/components/shared/page"
import { ScoreRing } from "@/components/shared/score-ring"
import { Expandable, Section } from "@/components/shared/section"
import { fmtAmount, scoreDot, verdictMeta } from "@/components/shared/semantics"
import { SignalChips } from "@/components/shared/signal-chips"
import { CompanyMark, SourceMark } from "@/components/shared/company-mark"
import { useSources } from "@/components/shared/source-drawer"
import { ErrorBanner } from "@/components/shared/states"
import { TrendArrow } from "@/components/shared/trend"
import { assetUrl, getOpportunity } from "@/lib/api"
import { useAsync } from "@/lib/use-async"
import { cn } from "@/lib/utils"

// ── Clickable citations — every source leads somewhere ────────────────────
function CitationChips({ citations, opp }) {
  const { open } = useSources()
  if (!citations?.length) return null
  const sourceFor = (citation) => {
    const page = citation.match(/(?:deck[ _-]?slide|slide)[_\s-]*(\d+)/i)?.[1]
    if (page) return opp.sources?.find((source) => source.type === "deck" && String(source.page) === page)
    return opp.sources?.find((source) => source.title?.toLowerCase().includes(citation.toLowerCase()))
  }
  const metaFor = (citation) => {
    const record = sourceFor(citation)
    const slide = citation.match(/(?:deck[ _-]?slide|slide)[_\s-]*(\d+)/i)?.[1]
    if (slide) return { label: `Slide ${slide}`, Icon: FileText, record }
    if (/github/i.test(citation)) return { label: "GitHub", Icon: GitBranch, record }
    if (/arxiv|paper/i.test(citation)) return { label: "Research", Icon: FileText, record }
    return { label: record?.title || citation.replaceAll("_", " "), Icon: Quote, record }
  }
  return (
    <div className="mt-3 flex flex-wrap gap-1.5 border-t border-border pt-3">
      {citations.map((c) => (
        (() => {
          const { label, Icon, record } = metaFor(c)
          return <button
          key={c}
          type="button"
          onClick={() => open({ citation: c, opp, record })}
          className="inline-flex max-w-full cursor-pointer items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1 text-[10px] font-semibold text-foreground/70 transition-colors hover:bg-secondary hover:text-foreground"
          title={`Open source: ${c}`}>
          <Icon className="size-3 shrink-0 text-muted-foreground" />
          <span className="truncate">{label}</span>
        </button>
        })()
      ))}
    </div>
  )
}

// ── Rail ──────────────────────────────────────────────────────────────────
function SummaryRail({ opp }) {
  const e = opp.enrichment
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-col items-center text-center">
        <CompanyMark name={opp.company_name} sources={opp.sources} className="mb-3 size-12 rounded-lg text-base" imageClassName="mb-3 size-12 rounded-lg border border-border bg-white p-1.5 shadow-sm" />
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
          {e?.reference_profile && <Badge variant="outline" title={e.reference_label}>Public reference</Badge>}
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
            <div className="rounded-lg border border-border bg-slate-50/70 px-3.5 py-3">
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
        <div key={c.title} className="rounded-xl border border-border bg-card p-4">
          <div className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">{c.title}</div>
          <p className="mt-1.5 text-sm leading-relaxed">{c.body}</p>
        </div>
      ))}
      <div className="rounded-xl border border-border bg-card p-4">
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

function CalculationChecks({ checks, opp }) {
  const { open } = useSources()
  if (!checks?.length) return null
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {checks.map((check) => {
        const source = opp.sources?.find((item) => item.type === "deck" && String(item.page) === String(check.source_slide))
        const matches = check.status === "consistent"
        return (
          <button
            key={`${check.title}-${check.source_slide}`}
            type="button"
            onClick={() => open({ citation: `deck_slide_${check.source_slide}`, opp, record: source })}
            className="rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-slate-50">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">{check.title}</span>
              <Badge variant={matches ? "positive" : "negative"}>{matches ? "Arithmetic checks out" : "Needs reconciliation"}</Badge>
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg bg-secondary/65 p-2.5"><span className="block text-[10px] font-medium text-muted-foreground uppercase">Deck says</span><span className="mt-0.5 block text-xs font-semibold">{check.reported}</span></div>
              <div className="rounded-lg bg-sky-50/70 p-2.5"><span className="block text-[10px] font-medium text-sky-700 uppercase">Recomputed</span><span className="mt-0.5 block text-xs font-semibold text-sky-950">{check.recomputed}</span></div>
            </div>
            <p className="mt-2.5 text-[11px] leading-relaxed text-muted-foreground">{check.note}</p>
          </button>
        )
      })}
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
    <div className="flex gap-4 rounded-xl border border-border bg-card p-4">
      {founder.avatar ? (
        <img src={assetUrl(founder.avatar)} alt={founder.name} loading="lazy" className="size-16 shrink-0 rounded-xl object-cover shadow-sm" />
      ) : (
        <span className="flex size-16 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-xl font-semibold text-white shadow-sm">{founder.name?.[0] || "F"}</span>
      )}
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
        {founder.affiliations?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Public affiliations">
            {founder.affiliations.map((affiliation) => (
              <span key={affiliation} className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-medium text-slate-600">
                {affiliation}
              </span>
            ))}
          </div>
        )}
        {founder.ai_read && (
          <div className="mt-2 flex items-start gap-1.5 rounded-lg bg-violet-50/70 px-2.5 py-2">
            <ShieldCheck className="mt-0.5 size-3 shrink-0 text-violet-500" />
            <p className="text-[11px] leading-snug text-violet-900/80">
              <span className="font-semibold">Profile check: </span>
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
            <AxisVisual name={name} axis={axis} />
          </CardHeader>
          <CardContent>
            <Expandable lines={2}>
              <p className="text-sm leading-relaxed text-foreground/80">{axis.rationale}</p>
            </Expandable>
            <CitationChips citations={axis.citations} opp={opp} />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function AxisVisual({ name, axis }) {
  if (name === "Founder") {
    return <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className={cn("h-full rounded-full", scoreDot(axis.score).replace("bg-", "bg-"))} style={{ width: `${Math.max(6, axis.score)}%` }} /></div>
  }
  const active = axis.rating === "bullish" ? 2 : axis.rating === "neutral" ? 1 : 0
  const colors = ["bg-red-300", "bg-amber-300", "bg-emerald-400"]
  return <div className="mt-3 grid grid-cols-3 gap-1" aria-label={`${name}: ${axis.rating}`}>{colors.map((color, index) => <span key={color} className={cn("h-1.5 rounded-full", index === active ? color : "bg-slate-100")} />)}</div>
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
  const [showAll, setShowAll] = useState(false)
  const confidenceRank = { low: 0, medium: 1, high: 2 }
  const grouped = Object.values(
    (claims ?? []).reduce((groups, claim) => {
      const key = claim.claim || "other"
      const current = groups[key]
      if (!current) {
        groups[key] = { ...claim, count: 1 }
        return groups
      }
      current.count += 1
      // The investor-facing overview should lead with the weakest finding,
      // while the complete per-claim record remains in the persisted response.
      if ((confidenceRank[claim.confidence] ?? 1) < (confidenceRank[current.confidence] ?? 1)) {
        groups[key] = { ...claim, count: current.count }
      }
      return groups
    }, {}),
  ).sort((a, b) => (confidenceRank[a.confidence] ?? 1) - (confidenceRank[b.confidence] ?? 1))

  const evidencePreview = (evidence) => {
    const withoutUrls = String(evidence ?? "")
      .replace(/\s*Sources?:\s*https?:\/\/\S+(?:\s*[;,|]\s*https?:\/\/\S+)*/gi, "")
      .replace(/https?:\/\/\S+/g, "")
      .replace(/\s+/g, " ")
      .trim()
    return withoutUrls.length > 190 ? `${withoutUrls.slice(0, 187).trimEnd()}…` : withoutUrls
  }

  const sourceFor = (claim) => {
    const text = `${claim.claim} ${claim.evidence}`
    const slide = text.match(/(?:deck[ _-]?slide|slide)[ _-]*(\d+)/i)?.[1]
    if (slide) return opp.sources?.find((source) => source.type === "deck" && String(source.page) === slide)
    const url = text.match(/https?:\/\/[^\s,;)]+/i)?.[0]
    return url ? opp.sources?.find((source) => source.url === url) : undefined
  }

  return (
    <Card className="gap-0 py-0">
      <CardContent className="px-0">
        <ul>
          {(showAll ? grouped : grouped.slice(0, 4)).map((c, i) => (
            <li key={`${c.claim}-${i}`}>
              {i > 0 && <Separator />}
              <button
                type="button"
                onClick={() => open({ citation: `${c.claim}: ${c.evidence}`, opp, record: sourceFor(c) })}
                className="flex w-full cursor-pointer items-start gap-4 px-5 py-3.5 text-left transition-colors hover:bg-secondary/40">
                <span className="w-28 shrink-0 pt-0.5 text-sm font-medium capitalize">
                  {c.claim.replaceAll("_", " ")}
                  {c.count > 1 && <span className="mt-1 block text-[10px] font-normal text-muted-foreground">{c.count} checks</span>}
                </span>
                <p className="flex-1 text-sm leading-relaxed text-foreground/80">{evidencePreview(c.evidence)}</p>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <ConfidenceMeter confidence={c.confidence} />
                  {((String(c.evidence).match(/https?:\/\/[^\s,;)]+/g) ?? []).length > 0) && <span className="text-[10px] font-medium text-muted-foreground">{(String(c.evidence).match(/https?:\/\/[^\s,;)]+/g) ?? []).length} sources</span>}
                </div>
              </button>
            </li>
          ))}
        </ul>
        {grouped.length > 4 && <button type="button" onClick={() => setShowAll((value) => !value)} className="w-full border-t border-border px-5 py-3 text-left text-xs font-medium text-muted-foreground hover:bg-secondary/40 hover:text-foreground">{showAll ? "Show decision summary" : `Show ${grouped.length - 4} more evidence categories`}</button>}
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

function MemoBody({ memo, opp, expanded = false }) {
  const { required, optional_or_flagged } = memo
  const e = opp?.enrichment ?? {}
  const [full, setFull] = useState(false)
  const showFull = expanded || full
  return (
    <Card className="gap-4">
      <CardContent className="space-y-5 pt-5">
        <MemoTextSection number="01" title="Company snapshot" value={required.company_snapshot} />

        <div>
          <MemoHeading number="02" title="Investment hypotheses" />
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
          <MemoHeading number="03" title="SWOT" />
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
            <Separator />
            <MemoTextSection number="04" title="Team & history" value={optional_or_flagged?.team_and_history || "Not disclosed"} />
            <MemoTextSection number="05" title="Problem & product" value={required.problem_and_product} />
            <MemoTextSection number="06" title="Technology & defensibility" value="Technical architecture, proprietary components, data moat, and model choices are not disclosed in the current evidence package." />
            <MemoTextSection number="07" title="Market sizing" value={e.market?.basis || "TAM / SAM / SOM and their assumptions are not fully disclosed."} />
            <MemoListSection number="08" title="Competition" values={e.competitors?.length ? e.competitors : ["Named competitor set: not disclosed"]} />
            <MemoTextSection number="09" title="Traction & KPIs" value={required.traction_kpis} />
            <MemoTextSection number="10" title="Financials & round structure" value="Historical P&L, projections, runway, round structure, and next-round timing: not disclosed." />
            <MemoTextSection number="11" title="Cap table" value={optional_or_flagged?.cap_table || "Not disclosed"} />
            <MemoTextSection number="12" title="Due diligence log" value={`${opp?.claim_trust?.length || 0} claim categories checked across ${opp?.sources?.length || 0} retained sources; ${opp?.processing_trace?.length || 0} processing steps logged. Open low-confidence items remain visible in Evidence & trust.`} />
            <MemoTextSection number="13" title="Exit perspective" value="Plausible acquirers, category comparables, and premium drivers have not been assessed at this screening stage." />
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

function MemoHeading({ number, title }) {
  return <h3 className="mb-1.5 flex items-center gap-2 text-xs font-medium tracking-wide text-muted-foreground uppercase"><span className="font-semibold text-slate-400">{number}</span>{title}</h3>
}

function MemoTextSection({ number, title, value }) {
  const flagged = /not disclosed|not assessed|unavailable|not fully/i.test(String(value))
  return <div><MemoHeading number={number} title={title} /><p className={cn("flex items-start gap-1.5 text-sm leading-relaxed", flagged ? "text-amber-700" : "text-foreground/80")}>{flagged && <Flag className="mt-0.5 size-3.5 shrink-0" />}{value}</p></div>
}

function MemoListSection({ number, title, values }) {
  return <div><MemoHeading number={number} title={title} /><div className="flex flex-wrap gap-1.5">{values.map((value) => <Badge key={value} variant="outline">{value}</Badge>)}</div></div>
}

function AppendixMemo({ opp }) {
  const memo = opp.memo
  const e = opp.enrichment ?? {}
  const required = memo.required
  const optional = memo.optional_or_flagged ?? {}
  const logoSource = (opp.sources || []).find((source) => source.type === "company_website" && (source.image_url || source.favicon_url)) || (opp.sources || []).find((source) => source.favicon_url || (source.type !== "deck" && source.image_url))
  const logo = logoSource ? assetUrl(logoSource.image_url || logoSource.favicon_url) : null
  const founders = e.founders || []
  const deckEvidence = exportDeckEvidence(opp)
  const trust = (opp.claim_trust || []).reduce((counts, claim) => ({ ...counts, [claim.confidence]: (counts[claim.confidence] || 0) + 1 }), { high: 0, medium: 0, low: 0 })
  const sourceCount = new Set((opp.sources || []).map((source) => source.url).filter(Boolean)).size
  const sections = [
    ["04", "Team & history", optional.team_and_history || "Not disclosed"],
    ["05", "Problem & product", required.problem_and_product],
    ["06", "Technology & defensibility", "Technical architecture, proprietary components, data moat, and model choices are not disclosed in the current evidence package."],
    ["07", "Market sizing", e.market?.basis || "TAM / SAM / SOM and assumptions: not disclosed"],
    ["08", "Competition", e.competitors?.length ? e.competitors.join(" · ") : "Named competitor set: not disclosed"],
    ["09", "Traction & KPIs", required.traction_kpis],
    ["10", "Financials & round structure", "Historical P&L, projections, runway, round structure, and next-round timing: not disclosed."],
    ["11", "Cap table", optional.cap_table || "Not disclosed"],
    ["12", "Due diligence log", `${opp.claim_trust?.length || 0} claim categories checked · ${opp.sources?.length || 0} retained sources · ${opp.processing_trace?.length || 0} processing steps logged.`],
    ["13", "Exit perspective", "Plausible acquirers, category comparables, and premium drivers: not assessed at this screening stage."],
  ]
  return (
    <article className="memo-export-only">
      <section className="memo-export-cover">
        <div className="memo-export-cover-top"><span>FounderScore · Investment brief</span><span>Confidential</span></div>
        <div className="memo-export-cover-company">
          {logo ? <img src={logo} alt="" /> : <span className="memo-export-logo-fallback">{opp.company_name?.[0] || "F"}</span>}
          <div><div className="memo-export-kicker">{e.sector || "Sector not disclosed"} · {e.stage || "Stage not disclosed"} · {e.geography || "Geography not disclosed"}</div><h1>{opp.company_name}</h1><p>{e.one_liner || required.company_snapshot}</p></div>
        </div>
        <div className="memo-export-cover-decision"><div><span>Recommendation</span><strong className={`is-${opp.verdict}`}>{verdictMeta[opp.verdict].label}</strong></div><div><span>Founder Score</span><strong>{opp.founder_score.value}<small> ± {opp.founder_score.confidence_interval}</small></strong></div><div><span>Proposed check</span><strong>{opp.amount_recommended > 0 ? fmtAmount(opp.amount_recommended) : "No check"}</strong></div><div><span>Thesis</span><strong>{opp.thesis?.thesis_match ? "Match" : "Miss"}</strong></div></div>
        <div className="memo-export-cover-context"><div><strong>Decision context</strong><p>{required.company_snapshot}</p></div><div><strong>Evidence retained</strong><p>{opp.claim_trust?.length || 0} claims · {sourceCount} unique links · {deckEvidence.length} visual slides selected</p></div></div>
        <div className="memo-export-cover-footer"><span>Prepared for Maschmeyer Group</span><span>{new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}</span></div>
      </section>

      <section className="memo-export-report-page">
        <ExportPageHeading number="01" title="Executive decision summary" subtitle="The shortest path to the investment decision" />
        <div className="memo-export-snapshot-grid"><ExportFact title="Problem" value={e.problem || "Not disclosed"}/><ExportFact title="Solution" value={e.solution || "Not disclosed"}/><ExportFact title="Product-market fit" value={e.pmf?.note || required.traction_kpis} eyebrow={e.pmf?.signal}/></div>
        <div className="memo-export-callout"><span>{opp.thesis?.thesis_match ? "Thesis match" : "Thesis miss"}</span><p>{opp.thesis?.rationale || "Thesis rationale unavailable."}</p></div>
        <AppendixVisualSummary opp={opp} />
        <div className="memo-export-metrics"><ExportMetric label="High-trust claims" value={`${trust.high}/${opp.claim_trust?.length || 0}`}/><ExportMetric label="Public sources" value={sourceCount}/><ExportMetric label="Founder trend" value={opp.founder_score.trend}/><ExportMetric label="Portfolio" value={opp.portfolio_check?.overlap ? "Overlap" : "Clear"}/></div>
      </section>

      <section className="memo-export-report-page">
        <ExportPageHeading number="02" title="Investment case" subtitle="Why invest, what could work, and what must be true" />
        <section className="memo-export-section"><h2>Investment hypotheses</h2><ol className="memo-export-hypotheses">{required.investment_hypotheses.map((item, index) => <li key={item}><span>{index + 1}</span>{item}</li>)}</ol></section>
        <section className="memo-export-section"><h2>SWOT · evidence-backed summary</h2><div className="memo-export-swot">{Object.entries(required.swot || {}).map(([key, values]) => <div key={key} className={`is-${key}`}><h3>{key}</h3><ul>{(values || []).map((value) => <li key={value}>{value}</li>)}</ul></div>)}</div></section>
        <section className="memo-export-section"><h2>Adversarial view · strongest case against</h2><ul className="memo-export-risks">{exportDecisionRisks(opp.adversarial_view?.challenges).map((challenge) => <li key={challenge}>{challenge}</li>)}</ul></section>
      </section>

      <section className="memo-export-report-page">
        <ExportPageHeading number="03" title="Team and market" subtitle="Who is building, market scope, and competitive context" />
        <div className="memo-export-team">{founders.length ? founders.map((founder) => <div key={founder.name} className="memo-export-founder">{founder.avatar ? <img src={assetUrl(founder.avatar)} alt=""/> : <span>{founder.name?.[0] || "F"}</span>}<div><h3>{founder.name}</h3><strong>{founder.role}</strong><p>{founder.background || founder.ai_read || "Background not independently established."}</p>{founder.affiliations?.length > 0 && <small>{founder.affiliations.join(" · ")}</small>}</div></div>) : <p className="memo-export-flag">Team details not disclosed.</p>}</div>
        <ExportMarket market={e.market} method={e.market_method}/>
        <section className="memo-export-section"><h2>Competition</h2>{e.competitors?.length ? <div className="memo-export-competitors">{e.competitors.map((competitor) => <span key={competitor}>{competitor}</span>)}</div> : <p className="memo-export-flag">Named competitor set not disclosed.</p>}</section>
      </section>

      <section className="memo-export-report-page">
        <ExportPageHeading number="04" title="Evidence and diligence" subtitle="Claims, independent checks, and exact deck evidence" />
        {e.calculation_checks?.length > 0 && <div className="memo-export-checks">{e.calculation_checks.map((check) => <div key={`${check.title}-${check.source_slide}`}><h3>{check.title}<span>{check.status}</span></h3><dl><dt>Deck</dt><dd>{check.reported}</dd><dt>Recomputed</dt><dd>{check.recomputed}</dd></dl><p>{check.note}</p></div>)}</div>}
        <div className="memo-export-claims">{(opp.claim_trust || []).slice(0, 8).map((claim, index) => <div key={`${claim.claim}-${index}`}><span className={`is-${claim.confidence}`}>{claim.confidence}</span><h3>{claim.claim.replaceAll("_", " ")}</h3><p>{exportEvidencePreview(claim.evidence)}</p></div>)}</div>
        {deckEvidence.length > 0 && <><h2 className="memo-export-gallery-title">Cited deck evidence</h2><div className="memo-export-gallery">{deckEvidence.map((source) => <figure key={`${source.page}-${source.preview_url}`}><img src={assetUrl(source.preview_url || source.image_url)} alt={`Deck slide ${source.page}`}/><figcaption><strong>Slide {source.page}</strong><span>{shortExportText(source.excerpt, 120)}</span></figcaption></figure>)}</div></>}
      </section>

      <section className="memo-export-report-page memo-export-appendix">
        <ExportPageHeading number="05" title="Appendix 1 investment memo" subtitle="Complete challenge-checklist order; gaps explicitly flagged" />
        <section className="memo-export-section"><h2>01 · Company snapshot</h2><p>{required.company_snapshot}</p></section>
        <section className="memo-export-section"><h2>02 · Investment hypotheses</h2><ol>{required.investment_hypotheses.map((item) => <li key={item}>{item}</li>)}</ol></section>
        <section className="memo-export-section"><h2>03 · SWOT</h2><div className="memo-export-swot compact">{Object.entries(required.swot || {}).map(([key, values]) => <div key={key}><h3>{key}</h3><ul>{(values || []).map((value) => <li key={value}>{value}</li>)}</ul></div>)}</div></section>
        {sections.map(([number, title, value]) => <section key={number} className="memo-export-section"><h2>{number} · {title}</h2><p className={/not disclosed|not assessed|unavailable/i.test(value) ? "memo-export-flag" : ""}>{value}</p></section>)}
      </section>

      <section className="memo-export-report-page">
        <ExportPageHeading number="06" title="Source index and open diligence" subtitle="Bounded references retained with the analysis" />
        <div className="memo-export-open-items"><div><strong>Low-confidence claims</strong><span>{trust.low}</span></div><div><strong>Medium-confidence claims</strong><span>{trust.medium}</span></div><div><strong>Processing steps logged</strong><span>{opp.processing_trace?.length || 0}</span></div></div>
        <ol className="memo-export-source-index">{exportSources(opp.sources).map((source, index) => <li key={`${source.url}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{source.title}</strong><small>{source.source || source.type}{source.page ? ` · slide ${source.page}` : ""}</small><em>{source.url}</em></div></li>)}</ol>
        <div className="memo-export-final-note"><strong>Investment discipline</strong><p>This brief distinguishes founder-provided claims, externally corroborated evidence, and unavailable information. A recommendation is not a substitute for legal, financial, technical, or reference diligence.</p></div>
      </section>
    </article>
  )
}

function ExportPageHeading({ number, title, subtitle }) {
  return <div className="memo-export-page-heading"><span>{number}</span><div><h1>{title}</h1><p>{subtitle}</p></div><strong>FounderScore</strong></div>
}

function ExportFact({ title, value, eyebrow }) {
  return <div><span>{title}{eyebrow ? ` · ${eyebrow}` : ""}</span><p>{value}</p></div>
}

function ExportMetric({ label, value }) {
  return <div><strong>{value}</strong><span>{label}</span></div>
}

function ExportMarket({ market, method }) {
  if (![market?.tam, market?.sam, market?.som].every((value) => Number.isFinite(value) && value > 0)) return <section className="memo-export-section"><h2>Market sizing</h2><p className="memo-export-flag">{market?.basis || "TAM / SAM / SOM not fully disclosed."}</p></section>
  const display = (key) => market.display?.[key] || `${market.unit?.startsWith("$") === false ? "" : "$"}${market[key]}${market.unit || "B"}`
  return <section className="memo-export-market"><div className="memo-export-market-rings"><span><b>TAM</b><strong>{display("tam")}</strong><i><b>SAM</b><strong>{display("sam")}</strong><em><b>SOM</b><strong>{display("som")}</strong></em></i></span></div><div><h2>Market sizing</h2><p>{market.basis}</p>{method && <small>{method}</small>}</div></section>
}

function exportDeckEvidence(opp) {
  const citedPages = new Set([...(opp.founder_axis?.citations || []), ...(opp.market_axis?.citations || []), ...(opp.idea_vs_market_axis?.citations || [])].map((citation) => citation.match(/(?:deck[ _-]?slide|slide)[_\s-]*(\d+)/i)?.[1]).filter(Boolean))
  const deck = (opp.sources || []).filter((source) => source.type === "deck" && (source.preview_url || source.image_url))
  return [...deck.filter((source) => citedPages.has(String(source.page))), ...deck.filter((source) => !citedPages.has(String(source.page)))].slice(0, 6)
}

function exportSources(sources = []) {
  const nonDeck = sources.filter((source, index) => source.type !== "deck" && sources.findIndex((candidate) => candidate.url === source.url) === index)
  const deck = sources.filter((source) => source.type === "deck")
  return [...nonDeck.slice(0, 20), ...(deck.length ? [{ ...deck[0], title: `Pitch deck · ${deck.length} slides`, source: "Founder-uploaded document" }] : [])]
}

function shortExportText(value, length = 160) {
  const text = String(value || "").replace(/\s+/g, " ").trim()
  return text.length > length ? `${text.slice(0, length).trim()}…` : text
}

function exportEvidencePreview(evidence) {
  return shortExportText(String(evidence || "").replace(/\s*Sources?:\s*https?:\/\/\S+(?:\s*[;,|]\s*https?:\/\/\S+)*/gi, "").replace(/https?:\/\/\S+/g, ""), 260)
}

function exportDecisionRisks(challenges = []) {
  const seen = new Set()
  return challenges.reduce((risks, challenge) => {
    const category = String(challenge).match(/^The\s+([a-z_ ]+?)\s+claim\s+may/i)?.[1]?.trim() || String(challenge).split(":", 1)[0]
    if (seen.has(category) || risks.length >= 3) return risks
    seen.add(category)
    risks.push(shortExportText(challenge, 300))
    return risks
  }, [])
}

function AppendixVisualSummary({ opp }) {
  const trust = (opp.claim_trust || []).reduce((counts, claim) => ({ ...counts, [claim.confidence]: (counts[claim.confidence] || 0) + 1 }), { high: 0, medium: 0, low: 0 })
  const total = Math.max(opp.claim_trust?.length || 0, 1)
  const axes = [
    ["Founder", `${opp.founder_axis.score} / 100`, opp.founder_axis.score, opp.founder_axis.trend],
    ["Market", opp.market_axis.rating, ({ bear: 14, neutral: 50, bullish: 86 }[opp.market_axis.rating] ?? 50), opp.market_axis.trend],
    ["Idea vs Market", opp.idea_vs_market_axis.rating, ({ bear: 14, neutral: 50, bullish: 86 }[opp.idea_vs_market_axis.rating] ?? 50), opp.idea_vs_market_axis.trend],
  ]
  return <section className="memo-export-visuals"><div><h2>Decision landscape <small>never averaged</small></h2>{axes.map(([label, display, percent, trend]) => <div key={label} className="memo-export-axis"><span>{label}<small>{trend}</small></span><i><b style={{ width: `${percent}%` }}/></i><strong>{display}</strong></div>)}</div><div><h2>Per-claim trust <small>{opp.claim_trust?.length || 0} checked</small></h2><div className="memo-export-trust-bar"><span style={{ width: `${(trust.high / total) * 100}%` }}/><span style={{ width: `${(trust.medium / total) * 100}%` }}/><span style={{ width: `${(trust.low / total) * 100}%` }}/></div><div className="memo-export-trust-legend"><span>High <strong>{trust.high}</strong></span><span>Medium <strong>{trust.medium}</strong></span><span>Low <strong>{trust.low}</strong></span></div><p>{new Set((opp.sources || []).map((source) => source.url).filter(Boolean)).size} unique evidence links retained.</p></div></section>
}

function AdversarialPanel({ challenges }) {
  if (!challenges?.length) return null
  return (
    <div className="rounded-xl border border-amber-200/80 bg-amber-50/70 p-5">
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
            onClick={() => open({ type: "news", title: n.title, newsSource: n.source, date: n.date, opp, record: opp.sources?.find((source) => source.url === n.url) })}
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

function hasFullMarketSizing(market) {
  return [market?.tam, market?.sam, market?.som].every((value) => Number.isFinite(value) && value > 0)
}

function SourceLedger({ sources, opp }) {
  const { open } = useSources()
  if (!sources?.length) return null
  const deckSources = sources.filter((source) => source.type === "deck")
  const uniqueSources = sources.filter((source, index) => source.type !== "deck" && sources.findIndex((candidate) => candidate.type === source.type && candidate.url === source.url) === index)
  const rows = [
    ...uniqueSources,
    ...(deckSources.length ? [{ type: "deck", title: `Pitch deck · ${deckSources.length} slides`, url: deckSources[0].url, source: "Founder-uploaded document", excerpt: "Open individual slides from citations, or browse deck previews here.", slides: deckSources }] : []),
  ]
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      {rows.map((source, index) => (
        <button key={`${source.url}-${source.title}-${index}`} type="button" onClick={() => open({ type: source.type, citation: source.title, opp, record: source })} className="flex w-full items-center gap-3 border-b border-border px-4 py-3 text-left last:border-b-0 hover:bg-slate-50">
          <SourceMark source={source} className="size-7 shrink-0" />
          <span className="min-w-0 flex-1"><span className="block truncate text-xs font-medium">{source.title}</span><span className="block truncate text-[11px] text-muted-foreground">{source.source}{source.page ? ` · slide ${source.page}` : ""}</span></span>
          <ExternalLink className="size-3.5 shrink-0 text-muted-foreground" />
        </button>
      ))}
    </div>
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
    let cancelled = false
    const prepareAndPrint = async () => {
      await document.fonts?.ready
      const images = [...document.querySelectorAll(".memo-export-only img")]
      await Promise.all(images.map((image) => image.complete ? Promise.resolve() : new Promise((resolve) => { image.addEventListener("load", resolve, { once: true }); image.addEventListener("error", resolve, { once: true }) })))
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
      if (cancelled) return
      window.print()
      document.title = originalTitle
      setPrinting(false)
    }
    prepareAndPrint()
    return () => { cancelled = true; document.title = originalTitle }
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
          <AppendixMemo opp={opp} />
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="memo-summary-rail lg:sticky lg:top-8">
            <SummaryRail opp={opp} />
          </motion.div>

          <motion.div variants={stagger.container} initial="initial" animate="animate" className="memo-screen-content min-w-0 space-y-7">
            <motion.div variants={stagger.item}>
              <Section icon={Lightbulb} title="At a glance">
                <Snapshot e={e} />
              </Section>
            </motion.div>

            {e?.calculation_checks?.length > 0 && (
              <motion.div variants={stagger.item}>
                <Section icon={Calculator} title="Model checks" sub="Deck arithmetic recomputed separately from external validation">
                  <CalculationChecks checks={e.calculation_checks} opp={opp} />
                </Section>
              </motion.div>
            )}

            {e?.agent_trace && (
              <motion.div variants={stagger.item}>
                <Section
                  icon={Workflow}
                  title="How this was produced"
                  sub="Six agents, in order — deterministic gates vs. AI reasoning, labeled honestly">
                  <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_250px]">
                    <AgentPipeline trace={e.agent_trace} />
                    <div className="rounded-xl border border-border bg-card p-4">
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

            <motion.div id="decision-dashboard" variants={stagger.item}>
              <Section icon={Gauge} title="Decision dashboard" sub="Conviction and evidence coverage at a glance">
                <div className="grid gap-3 xl:grid-cols-2">
                  <DecisionLandscape opportunity={opp} />
                  <EvidenceCoverageChart claims={opp.claim_trust} sources={opp.sources} />
                </div>
              </Section>
            </motion.div>

            {e && (
              <motion.div variants={stagger.item}>
                <Section
                  icon={ChartPie}
                  title="Market"
                  sub={e.reference_profile ? "External benchmark with SAM / SOM assumptions labeled explicitly" : hasFullMarketSizing(e.market) ? "Founder-declared sizing, with independent evidence kept separate" : "No complete investable sizing was disclosed in the submitted materials"}
                  right={<RatingPill rating={opp.market_axis.rating} />}>
                  <div className="rounded-xl border border-border bg-card p-5">
                    {hasFullMarketSizing(e.market) ? <><MarketChart market={e.market} /><Separator className="my-4" /></> : <div className="flex items-start gap-3 rounded-lg bg-slate-50 p-3.5"><ChartPie className="mt-0.5 size-4 shrink-0 text-slate-400" /><div><p className="text-sm font-medium">TAM / SAM / SOM not provided</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">The system will not invent a market model. Ask for a defined customer segment, pricing basis, and bottom-up revenue bridge before underwriting the opportunity.</p></div></div>}
                    {e.competitors?.length > 0 && (
                      <div className="mb-4 grid gap-3 rounded-lg bg-slate-50/80 p-3.5 sm:grid-cols-[1fr_1.5fr]">
                        <div>
                          <div className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">Competitive set</div>
                          <div className="mt-2 flex flex-wrap gap-1.5">{e.competitors.map((name) => <Badge key={name} variant="outline">{name}</Badge>)}</div>
                        </div>
                        <div>
                          <div className="text-[10px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">Sizing method</div>
                          <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">{e.market_method}</p>
                        </div>
                      </div>
                    )}
                    <div className="mb-1.5 text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">Relevant coverage</div>
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

            {opp.sources?.length > 0 && (
              <motion.div variants={stagger.item}>
                <Section icon={FileText} title="Source ledger" sub="Submitted files and bounded public references retained with the analysis">
                  <SourceLedger sources={opp.sources} opp={opp} />
                </Section>
              </motion.div>
            )}

            <motion.div variants={stagger.item}>
              <Section icon={FileText} title="Investment memo" sub="Appendix-1 structure — flagged fields never fabricated">
                <MemoBody memo={opp.memo} opp={opp} expanded={printing} />
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
