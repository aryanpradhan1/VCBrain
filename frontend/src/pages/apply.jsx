import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, Check, ChevronDown, CloudUpload, FileText, Link2, LoaderCircle, ShieldCheck, Sparkles, UserRound, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { getApplicationStatus, submitApplication } from "@/lib/api"

const progressCopy = {
  queued: "Your application is queued for intake.",
  processing: "Reading your document, checking the links you supplied, and building your evidence trail.",
  ready: "Your Founder Score and private review are ready.",
  failed: "We couldn’t complete processing. You can correct the document and resubmit.",
}

const processingStages = [
  ["reading_deck", "Reading your deck"],
  ["extracting_claims", "Extracting claims"],
  ["checking_sources", "Checking supplied links"],
  ["scoring", "Scoring and diligence"],
]

function OptionalLink({ name, label, placeholder }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-foreground/80">{label}</span>
      <Input name={name} placeholder={placeholder} className="h-10 rounded-lg" />
    </label>
  )
}

export default function Apply() {
  const [file, setFile] = useState(null)
  const [photo, setPhoto] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [submission, setSubmission] = useState(null)
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const fileRef = useRef(null)
  const photoRef = useRef(null)

  useEffect(() => {
    if (!submission?.company_id || ["ready", "failed"].includes(submission.status)) return undefined
    const timer = window.setInterval(async () => {
      try {
        setSubmission(await getApplicationStatus(submission.company_id))
      } catch {
        // Keep the last honest state and retry—analysis can take minutes on a real deck.
      }
    }, 2500)
    return () => window.clearInterval(timer)
  }, [submission?.company_id, submission?.status])

  const onDrop = (event) => {
    event.preventDefault()
    setDragging(false)
    const dropped = event.dataTransfer.files?.[0]
    if (dropped) setFile(dropped)
  }

  const activeStage = Math.max(0, processingStages.findIndex(([key]) => key === submission?.stage))

  const submit = async (event) => {
    event.preventDefault()
    if (!file || submitting) return
    setError("")
    setSubmitting(true)
    try {
      const form = new FormData(event.currentTarget)
      form.set("deck", file)
      if (photo) form.set("founder_photo", photo)
      setSubmission(await submitApplication(form))
    } catch (err) {
      setError(err.message || "We couldn’t submit your application.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-dvh bg-slate-50/60">
      <div className="relative mx-auto flex min-h-dvh max-w-2xl flex-col px-6 py-10 sm:py-14">
        <Link to="/" className="inline-flex items-center gap-1 self-start text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
          <ArrowLeft className="size-3.5" /> Fund workspace
        </Link>

        <AnimatePresence mode="wait">
          {!submission ? (
            <motion.main key="form" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.35 }} className="mx-auto w-full max-w-xl pt-12">
              <div className="mb-3 inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-card px-2.5 py-1">
                <Sparkles className="size-3 text-amber-500" />
                <span className="text-xs font-medium text-slate-700">A decision process grounded in evidence</span>
              </div>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Apply without a warm intro.</h1>
              <p className="mt-3 max-w-lg text-sm leading-relaxed text-muted-foreground">
                Share the essentials and a deck or supporting document. We only look at the public links you choose to provide, and we show the fund exactly which sources informed the review.
              </p>

              <form onSubmit={submit} className="mt-8 space-y-6">
                <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
                  <div className="mb-4 flex items-center gap-2"><UserRound className="size-4 text-slate-500" /><h2 className="text-sm font-semibold">The essentials</h2></div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label><span className="mb-1.5 block text-xs font-medium">Your full name</span><Input required name="founder_name" placeholder="Maya Okonkwo" className="h-11 rounded-lg" /></label>
                    <label><span className="mb-1.5 block text-xs font-medium">Role</span><Input name="founder_role" defaultValue="Founder & CEO" className="h-11 rounded-lg" /></label>
                    <label><span className="mb-1.5 block text-xs font-medium">Company name</span><Input required name="company_name" placeholder="Relay Robotics" className="h-11 rounded-lg" /></label>
                    <label><span className="mb-1.5 block text-xs font-medium">Email</span><Input required type="email" name="email" placeholder="you@company.com" className="h-11 rounded-lg" /></label>
                    <label><span className="mb-1.5 block text-xs font-medium">Sector <em className="font-normal text-muted-foreground">optional</em></span><Input name="sector" placeholder="Robotics, health, infra…" className="h-11 rounded-lg" /></label>
                    <label><span className="mb-1.5 block text-xs font-medium">Location <em className="font-normal text-muted-foreground">optional</em></span><Input name="geography" placeholder="Austin, US" className="h-11 rounded-lg" /></label>
                  </div>
                </section>

                <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
                  <div className="mb-2 flex items-center gap-2"><FileText className="size-4 text-slate-500" /><h2 className="text-sm font-semibold">Deck or supporting document</h2></div>
                  <p className="mb-4 text-xs leading-relaxed text-muted-foreground">PDF is ideal. PPTX, DOCX, Markdown, and TXT also work. Slide text, charts/images, and source references are extracted from your upload.</p>
                  <button type="button" onClick={() => fileRef.current?.click()} onDragOver={(e) => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={onDrop} className={cn("flex w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-6 py-8 transition-colors", dragging ? "border-slate-400 bg-slate-50" : file ? "border-emerald-300 bg-emerald-50/50" : "border-slate-200 bg-slate-50/50 hover:border-slate-300 hover:bg-slate-50")}>
                    {file ? <><span className="flex size-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600"><FileText className="size-4.5" /></span><span className="max-w-full truncate text-sm font-medium">{file.name}</span><span role="button" onClick={(e) => { e.stopPropagation(); setFile(null) }} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"><X className="size-3" /> Remove</span></> : <><span className="flex size-9 items-center justify-center rounded-xl bg-secondary text-muted-foreground"><CloudUpload className="size-4.5" /></span><span className="text-sm font-medium">{dragging ? "Drop it here" : "Drop your document here"}</span><span className="text-xs text-muted-foreground">Up to 25 MB</span></>}
                    <input ref={fileRef} type="file" accept=".pdf,.pptx,.docx,.txt,.md" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                  </button>
                </section>

                <section className="rounded-2xl border border-border bg-card shadow-sm">
                  <button type="button" onClick={() => setExpanded((value) => !value)} className="flex w-full items-center justify-between px-5 py-4 text-left"><span className="flex items-center gap-2 text-sm font-semibold"><Link2 className="size-4 text-slate-500" /> Optional public links</span><ChevronDown className={cn("size-4 text-muted-foreground transition-transform", expanded && "rotate-180")} /></button>
                  {expanded && <div className="grid gap-3 border-t border-border px-5 py-5 sm:grid-cols-2"><OptionalLink name="website" label="Company website" placeholder="company.com" /><OptionalLink name="github" label="GitHub profile or org" placeholder="github.com/you" /><OptionalLink name="linkedin" label="LinkedIn" placeholder="linkedin.com/in/you" /><OptionalLink name="product_hunt" label="Product Hunt" placeholder="producthunt.com/products/..." /><OptionalLink name="devpost" label="Devpost" placeholder="devpost.com/..." /><OptionalLink name="arxiv" label="arXiv profile or paper" placeholder="arxiv.org/..." /><OptionalLink name="x" label="X profile" placeholder="x.com/you" /><label className="block"><span className="mb-1.5 block text-xs font-medium">Optional headshot</span><button type="button" onClick={() => photoRef.current?.click()} className="flex h-10 w-full items-center gap-2 rounded-lg border border-input px-3 text-left text-xs text-muted-foreground hover:bg-slate-50"><UserRound className="size-3.5" />{photo ? photo.name : "Upload image"}</button><input ref={photoRef} type="file" accept="image/*" className="hidden" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} /></label></div>}
                </section>

                <label className="flex cursor-pointer items-start gap-2.5 text-xs leading-relaxed text-muted-foreground"><input required type="checkbox" className="mt-0.5 size-3.5 rounded border-slate-300" /><span>I consent to analysis of my submitted materials and the public links I supplied. Public web pages are stored only as source references and short evidence excerpts.</span></label>
                {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>}
                <Button type="submit" disabled={!file || submitting} className="h-11 w-full rounded-lg text-sm font-semibold shadow-sm">{submitting && <LoaderCircle className="size-4 animate-spin" />} {submitting ? "Submitting…" : "Submit for scoring"}</Button>
              </form>
            </motion.main>
          ) : (
            <motion.main key="status" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center text-center">
              <span className={cn("flex size-12 items-center justify-center rounded-full text-white shadow-lg", submission.status === "ready" ? "bg-emerald-600" : submission.status === "failed" ? "bg-red-500" : "bg-slate-800")}>
                {submission.status === "ready" ? <Check className="size-6" strokeWidth={3} /> : submission.status === "failed" ? <X className="size-6" strokeWidth={3} /> : <LoaderCircle className="size-5 animate-spin" />}
              </span>
              <h2 className="mt-5 text-2xl font-semibold tracking-tight">{submission.status === "ready" ? "Your score is ready." : submission.status === "failed" ? "We need another file." : "Your application is in motion."}</h2>
              <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">{submission.error_message || (submission.status === "processing" ? processingStages[activeStage]?.[1] : progressCopy[submission.status]) || progressCopy.queued}</p>
              {submission.status === "processing" && <ol className="mt-6 w-full max-w-xs space-y-2 text-left">{processingStages.map(([key, label], index) => <li key={key} className={cn("flex items-center gap-2 text-xs", index < activeStage ? "text-emerald-700" : index === activeStage ? "font-semibold text-foreground" : "text-muted-foreground")}><span className={cn("flex size-4 items-center justify-center rounded-full border text-[9px]", index < activeStage ? "border-emerald-500 bg-emerald-500 text-white" : index === activeStage ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white")}>{index < activeStage ? "✓" : index + 1}</span>{label}</li>)}</ol>}
              {submission.status === "ready" && <Link to={`/founder/${submission.founder_id}`} className="mt-7"><Button className="rounded-lg px-5"><ShieldCheck className="size-4" /> View your Founder Score</Button></Link>}
              {submission.status === "failed" && <Button variant="outline" onClick={() => setSubmission(null)} className="mt-7 rounded-lg">Return to application</Button>}
              {!["ready", "failed"].includes(submission.status) && <p className="mt-7 text-[11px] text-muted-foreground">This page updates automatically. Deep diligence can take a few minutes.</p>}
            </motion.main>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
