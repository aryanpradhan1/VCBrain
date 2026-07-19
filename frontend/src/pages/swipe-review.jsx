import { useCallback, useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { AnimatePresence, motion, useMotionValue, useTransform } from "motion/react"
import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Bookmark,
  Check,
  ChevronRight,
  CircleAlert,
  ExternalLink,
  Flame,
  Keyboard,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { AxisDots, ChannelBadge, RatingPill } from "@/components/shared/chips"
import { CompanyMark } from "@/components/shared/company-mark"
import { Page } from "@/components/shared/page"
import { ScoreRing } from "@/components/shared/score-ring"
import { SignalIcons } from "@/components/shared/signal-chips"
import { ErrorBanner } from "@/components/shared/states"
import { assetUrl, listOpportunities, postDecision } from "@/lib/api"
import { useAsync } from "@/lib/use-async"
import { cn } from "@/lib/utils"
import { fmtAmount, trustTally } from "@/components/shared/semantics"
import { pitchOf } from "@/fixtures/opportunities"

const actions = {
  decline: { label: "Decline", Icon: X, tone: "red", exitX: -900, exitY: 20, rotate: -18 },
  review: { label: "Review", Icon: Bookmark, tone: "amber", exitX: 0, exitY: -760, rotate: 0 },
  approve: { label: "Approve", Icon: Check, tone: "emerald", exitX: 900, exitY: 20, rotate: 18 },
}

export default function SwipeReview() {
  const { data, error, loading, retry } = useAsync(() => listOpportunities(), [])
  const [channel, setChannel] = useState("all")
  const [removed, setRemoved] = useState([])
  const [history, setHistory] = useState([])
  const [pending, setPending] = useState(false)
  const [leaving, setLeaving] = useState(null)
  const [notice, setNotice] = useState(null)
  const navigate = useNavigate()

  const queue = useMemo(() => (data || []).filter((item) => !removed.includes(item.company_id) && (channel === "all" || item.sourcing_channel === channel)), [data, removed, channel])
  const current = queue[0]

  const decide = useCallback(async (decision) => {
    if (!current || pending) return
    setPending(true)
    setLeaving(decision)
    try {
      await postDecision(current.company_id, decision)
      await new Promise((resolve) => setTimeout(resolve, 230))
      setHistory((items) => [...items, { opportunity: current, decision, previous: current.verdict }])
      setRemoved((items) => [...items, current.company_id])
      setNotice({ type: "success", text: `${current.company_name} · ${actions[decision].label}` })
    } catch {
      setNotice({ type: "error", text: "Decision was not saved. The card stayed in your queue." })
    } finally {
      setLeaving(null)
      setPending(false)
    }
  }, [current, pending])

  const undo = useCallback(async () => {
    const last = history.at(-1)
    if (!last || pending) return
    setPending(true)
    try {
      await postDecision(last.opportunity.company_id, last.previous)
      setRemoved((items) => items.filter((id) => id !== last.opportunity.company_id))
      setHistory((items) => items.slice(0, -1))
      setNotice({ type: "success", text: `Restored ${last.opportunity.company_name}` })
    } catch {
      setNotice({ type: "error", text: "Undo could not be saved." })
    } finally {
      setPending(false)
    }
  }, [history, pending])

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return
      if (event.key === "ArrowLeft") decide("decline")
      if (event.key === "ArrowUp") decide("review")
      if (event.key === "ArrowRight") decide("approve")
      if (event.key === "Enter" && current) navigate(`/opportunities/${current.company_id}`)
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z") undo()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [current, decide, navigate, undo])

  return (
    <Page className="min-w-0 overflow-x-hidden">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.12em] text-rose-500 uppercase"><Flame className="size-3"/> Fast review</div>
          <h1 className="text-[28px] font-semibold tracking-[-0.035em]">Swipe the pipeline</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">Triage quickly; open full diligence whenever the decision needs depth.</p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" disabled={!history.length || pending} onClick={undo} className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-muted-foreground disabled:opacity-35"><RotateCcw className="size-3.5"/> Undo</button>
          <Link to="/" className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium">List view <ChevronRight className="size-3.5"/></Link>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-lg border border-border bg-card p-0.5 text-xs font-medium">
          {["all", "inbound", "outbound"].map((value) => <button key={value} type="button" onClick={() => setChannel(value)} className={cn("rounded-md px-3 py-1.5 capitalize", channel === value ? "bg-slate-950 text-white" : "text-muted-foreground")}>{value}</button>)}
        </div>
        <div className="flex items-center gap-4 text-[10px] text-muted-foreground"><span>{queue.length} remaining</span><span className="hidden items-center gap-1.5 sm:flex"><Keyboard className="size-3.5"/> ← decline · ↑ review · → approve · Enter details</span></div>
      </div>

      {notice && <div className={cn("mx-auto mb-3 flex max-w-[720px] items-center gap-2 rounded-lg px-3 py-2 text-xs", notice.type === "error" ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700")}>{notice.type === "error" ? <CircleAlert className="size-3.5"/> : <ShieldCheck className="size-3.5"/>}{notice.text}</div>}
      {error && <ErrorBanner message="Couldn't load the review queue." onRetry={retry}/>} 
      {loading && <SwipeSkeleton/>}

      {!loading && !error && (
        <div className="mx-auto max-w-[920px]">
          <div className="relative mx-auto h-[590px] max-w-[720px] sm:h-[610px]">
            {queue.slice(1, 3).reverse().map((opportunity, index) => <div key={opportunity.company_id} className="absolute inset-x-3 top-0 h-[560px] rounded-[24px] border border-border bg-card shadow-lg sm:h-[580px]" style={{ transform: `translateY(${20 - index * 9}px) scale(${0.96 + index * 0.018})`, opacity: 0.55 + index * 0.18 }}/>) }
            <AnimatePresence mode="popLayout">
              {current ? <SwipeCard key={current.company_id} opportunity={current} leaving={leaving} pending={pending} onDecide={decide}/> : <FinishedCard key="finished" onReset={() => { setRemoved([]); setHistory([]); setNotice(null) }}/>} 
            </AnimatePresence>
          </div>
          {current && <ActionDock pending={pending} onDecide={decide}/>} 
        </div>
      )}
    </Page>
  )
}

function SwipeCard({ opportunity, leaving, pending, onDecide }) {
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const rotate = useTransform(x, [-260, 260], [-9, 9])
  const approveOpacity = useTransform(x, [35, 145], [0, 1])
  const declineOpacity = useTransform(x, [-145, -35], [1, 0])
  const reviewOpacity = useTransform(y, [-140, -45], [1, 0])
  const trust = trustTally(opportunity.claim_trust)
  const founders = opportunity.enrichment?.founders || []
  const exit = leaving ? actions[leaving] : null

  const onDragEnd = (_, info) => {
    if (pending) return
    if (info.offset.y < -105 && Math.abs(info.offset.y) > Math.abs(info.offset.x)) onDecide("review")
    else if (info.offset.x > 120) onDecide("approve")
    else if (info.offset.x < -120) onDecide("decline")
  }

  return (
    <motion.article
      drag={!pending}
      dragElastic={0.72}
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      onDragEnd={onDragEnd}
      style={{ x, y, rotate }}
      animate={exit ? { x: exit.exitX, y: exit.exitY, rotate: exit.rotate, opacity: 0 } : { opacity: 1 }}
      exit={{ opacity: 0, scale: .96 }}
      transition={exit ? { duration: .28, ease: "easeIn" } : { type: "spring", stiffness: 360, damping: 28 }}
      className="absolute inset-x-0 top-0 z-10 h-[560px] cursor-grab touch-none overflow-hidden rounded-[24px] border border-slate-200 bg-card shadow-[0_24px_70px_rgb(15_23_42/0.16)] active:cursor-grabbing sm:h-[580px]">
      <DecisionStamp style={{ opacity: declineOpacity }} label="DECLINE" className="left-6 -rotate-12 border-red-500 text-red-500"/>
      <DecisionStamp style={{ opacity: approveOpacity }} label="APPROVE" className="right-6 rotate-12 border-emerald-500 text-emerald-600"/>
      <DecisionStamp style={{ opacity: reviewOpacity }} label="REVIEW" className="left-1/2 -translate-x-1/2 border-amber-500 text-amber-600"/>

      <div className="grid h-full sm:grid-cols-[230px_minmax(0,1fr)]">
        <div className="hidden flex-col bg-slate-950 p-6 text-white sm:flex">
          <div className="flex items-start justify-between gap-3">
            <CompanyMark name={opportunity.company_name} sources={opportunity.sources} className="size-12 rounded-xl text-base" imageClassName="size-12 rounded-xl bg-white object-contain p-1.5"/>
            <ChannelBadge channel={opportunity.sourcing_channel}/>
          </div>
          <div className="mt-5"><div className="text-2xl font-semibold tracking-[-0.035em]">{opportunity.company_name}</div><div className="mt-2 flex flex-wrap gap-1.5">{opportunity.enrichment?.sector && <Badge variant="outline" className="border-white/15 bg-white/5 text-slate-200">{opportunity.enrichment.sector}</Badge>}{opportunity.enrichment?.stage && <Badge variant="outline" className="border-white/15 bg-white/5 text-slate-200">{opportunity.enrichment.stage}</Badge>}</div></div>
          <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-slate-300 sm:mt-4 sm:line-clamp-4">{pitchOf(opportunity)}</p>
          <div className="mt-auto">
            <div className="text-[9px] font-semibold tracking-[.1em] text-slate-500 uppercase">Recommended check</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">{opportunity.amount_recommended ? fmtAmount(opportunity.amount_recommended) : "No check"}</div>
            <div className="mt-4 hidden items-center justify-between border-t border-slate-800 pt-4 sm:flex"><AxisDots founder_axis={opportunity.founder_axis} market_axis={opportunity.market_axis} idea_vs_market_axis={opportunity.idea_vs_market_axis}/><span className="text-[10px] text-slate-400">3 axes · never averaged</span></div>
          </div>
        </div>

        <div className="min-w-0 overflow-y-auto p-5 sm:overflow-hidden sm:p-6">
          <div className="mb-4 flex items-center gap-3 sm:hidden">
            <CompanyMark name={opportunity.company_name} sources={opportunity.sources} className="size-11 rounded-xl text-sm" imageClassName="size-11 rounded-xl border border-border bg-white object-contain p-1"/>
            <div className="min-w-0 flex-1"><div className="truncate text-lg font-semibold tracking-tight">{opportunity.company_name}</div><div className="mt-1 flex items-center gap-1.5"><ChannelBadge channel={opportunity.sourcing_channel}/>{opportunity.enrichment?.sector && <span className="truncate text-[10px] text-muted-foreground">{opportunity.enrichment.sector} · {opportunity.enrichment?.stage}</span>}</div></div>
          </div>
          <div className="flex items-start justify-between gap-5">
            <div><div className="text-[9px] font-semibold tracking-[.1em] text-muted-foreground uppercase">Founder Score · persistent</div><div className="mt-1 flex items-baseline gap-2"><strong className="text-4xl tracking-[-.04em] tabular-nums">{opportunity.founder_score.value}</strong><span className="text-sm text-muted-foreground">± {opportunity.founder_score.confidence_interval}</span><span className="text-xs font-semibold text-emerald-600">↗ {opportunity.founder_score.trend}</span></div></div>
            <ScoreRing score={opportunity.founder_score} size={92} className="hidden [&_.text-4xl]:text-2xl sm:inline-flex"/>
          </div>

          {founders.length > 0 && <div className="mt-4 flex items-center gap-2.5 overflow-hidden rounded-xl bg-slate-50 p-3">{founders.slice(0, 3).map((founder) => founder.avatar ? <img key={founder.name} src={assetUrl(founder.avatar)} alt={founder.name} className="size-9 rounded-lg object-cover"/> : <span key={founder.name} className="flex size-9 items-center justify-center rounded-lg bg-slate-800 text-xs font-bold text-white">{founder.name?.[0]}</span>)}<div className="min-w-0"><div className="truncate text-xs font-semibold">{founders.map((founder) => founder.name).join(" · ")}</div><div className="truncate text-[10px] text-muted-foreground">{founders.map((founder) => founder.role).join(" · ")}</div></div></div>}

          <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
            <AxisMini label="Founder" value={opportunity.founder_axis.score} trend={opportunity.founder_axis.trend}/>
            <AxisMini label="Market" rating={opportunity.market_axis.rating} trend={opportunity.market_axis.trend}/>
            <AxisMini label="Idea / market" rating={opportunity.idea_vs_market_axis.rating} trend={opportunity.idea_vs_market_axis.trend}/>
          </div>

          <p className="mt-4 line-clamp-3 text-xs leading-relaxed text-foreground/75">{opportunity.idea_vs_market_axis.rationale}</p>
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-4"><SignalIcons signals={opportunity.public_signals}/><span className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border px-2 text-[10px] font-medium"><ShieldCheck className="size-3.5 text-emerald-600"/>{trust.high} high · {trust.medium} medium · {trust.low} low trust</span></div>

          <Link to={`/opportunities/${opportunity.company_id}`} onPointerDown={(event) => event.stopPropagation()} className="mt-4 flex h-10 items-center justify-center gap-2 rounded-xl border border-border bg-white text-xs font-semibold shadow-sm transition-colors hover:bg-slate-50">Open full diligence <ExternalLink className="size-3.5"/></Link>
        </div>
      </div>
    </motion.article>
  )
}

function DecisionStamp({ label, className, style }) { return <motion.div style={style} className={cn("pointer-events-none absolute top-6 z-30 rounded-lg border-[3px] px-3 py-1.5 text-xl font-black tracking-wider", className)}>{label}</motion.div> }

function AxisMini({ label, value, rating, trend }) { return <div className="min-w-0 rounded-xl border border-border p-2.5"><div className="truncate text-[9px] font-semibold text-muted-foreground uppercase">{label}</div><div className="mt-1 flex items-center justify-between gap-1">{rating ? <RatingPill rating={rating}/> : <strong className="text-lg tabular-nums">{value}</strong>}<span className="text-[10px] text-emerald-600">{trend === "improving" ? "↗" : trend === "declining" ? "↘" : "→"}</span></div></div> }

function ActionDock({ pending, onDecide }) {
  return <div className="mt-2 flex items-center justify-center gap-4"><ActionButton action="decline" disabled={pending} onClick={() => onDecide("decline")}/><ActionButton action="review" disabled={pending} onClick={() => onDecide("review")}/><ActionButton action="approve" disabled={pending} onClick={() => onDecide("approve")}/></div>
}

function ActionButton({ action, disabled, onClick }) {
  const item = actions[action]
  const Icon = item.Icon
  const styles = { red: "border-red-200 text-red-500 hover:bg-red-50", amber: "border-amber-200 text-amber-600 hover:bg-amber-50", emerald: "border-emerald-200 text-emerald-600 hover:bg-emerald-50" }
  const Hint = action === "decline" ? ArrowLeft : action === "review" ? ArrowUp : ArrowRight
  return <Button type="button" variant="outline" disabled={disabled} onClick={onClick} className={cn("h-12 rounded-full border-2 px-5 shadow-sm", styles[item.tone])}><Icon className="size-5"/><span className="hidden sm:inline">{item.label}</span><Hint className="size-3 opacity-45"/></Button>
}

function FinishedCard({ onReset }) { return <motion.div initial={{ opacity: 0, scale: .96 }} animate={{ opacity: 1, scale: 1 }} className="absolute inset-x-0 top-0 flex h-[560px] flex-col items-center justify-center rounded-[24px] border border-border bg-card text-center shadow-lg sm:h-[580px]"><span className="flex size-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600"><Sparkles className="size-6"/></span><h2 className="mt-5 text-xl font-semibold">Queue reviewed</h2><p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">Every visible opportunity has a recorded decision. Return to the list for portfolio-level context or review the deck again.</p><button type="button" onClick={onReset} className="mt-5 inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-xs font-semibold text-white"><RotateCcw className="size-3.5"/> Review again</button></motion.div> }

function SwipeSkeleton() { return <div className="mx-auto max-w-[720px]"><Skeleton className="h-[580px] rounded-[24px]"/><div className="mt-4 flex justify-center gap-4"><Skeleton className="size-12 rounded-full"/><Skeleton className="size-12 rounded-full"/><Skeleton className="size-12 rounded-full"/></div></div> }
