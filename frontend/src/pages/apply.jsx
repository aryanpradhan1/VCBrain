import { useRef, useState } from "react"
import { Link } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, Check, CloudUpload, FileText, Sparkles, X } from "lucide-react"
import confetti from "canvas-confetti"

import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Inbound sourcing entry: deck + name, per the pipeline contract. Mocked client-side;
// wiring to A's signal-intake endpoint is a swap inside submit().
export default function Apply() {
  const [name, setName] = useState("")
  const [company, setCompany] = useState("")
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const inputRef = useRef(null)

  const canSubmit = name.trim() && company.trim() && file

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) setFile(dropped)
  }

  const submit = (e) => {
    e.preventDefault()
    if (!canSubmit) return
    setSubmitted(true)
    setTimeout(() => {
      confetti({
        particleCount: 70,
        spread: 60,
        startVelocity: 28,
        origin: { y: 0.6 },
        colors: ["#10b981", "#0ea5e9", "#a78bfa"],
        disableForReducedMotion: true,
      })
    }, 400)
  }

  return (
    <div className="min-h-dvh bg-slate-50/60">
      <div className="relative mx-auto flex min-h-dvh max-w-lg flex-col items-center justify-center px-6 py-16">
        <Link
          to="/"
          className="absolute top-6 left-6 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
          <ArrowLeft className="size-3.5" />
          Fund workspace
        </Link>

        <AnimatePresence mode="wait">
          {!submitted ? (
            <motion.div
              key="form"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="w-full text-center">
              <div className="mb-3 inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-card px-2.5 py-1">
                <Sparkles className="size-3 text-amber-500" />
                <span className="text-xs font-medium text-slate-700">
                  A real $100K decision within 24 hours
                </span>
              </div>
              <h1 className="text-3xl font-semibold tracking-tight">
                Get seen. Get scored.
                <br />
                Get an answer.
              </h1>
              <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-muted-foreground">
                No warm intro needed. Every founder gets a persistent Founder Score —
                funded or not, it never resets and sharpens with every milestone.
              </p>

              <form onSubmit={submit} className="mt-8 space-y-3 text-left">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your name"
                    className="h-11 rounded-xl"
                  />
                  <Input
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    placeholder="Company"
                    className="h-11 rounded-xl"
                  />
                </div>

                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault()
                    setDragging(true)
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                  className={cn(
                    "flex w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-6 py-9 transition-colors",
                    dragging
                      ? "scale-[1.01] border-slate-400 bg-slate-50"
                      : file
                        ? "border-emerald-300 bg-emerald-50/50"
                        : "border-slate-200 bg-card/60 hover:border-slate-300 hover:bg-card"
                  )}>
                  {file ? (
                    <>
                      <span className="flex size-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600">
                        <FileText className="size-4.5" />
                      </span>
                      <span className="max-w-full truncate text-sm font-medium">{file.name}</span>
                      <span
                        role="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          setFile(null)
                        }}
                        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
                        <X className="size-3" />
                        Remove
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="flex size-9 items-center justify-center rounded-xl bg-secondary text-muted-foreground">
                        <CloudUpload className="size-4.5" />
                      </span>
                      <span className="text-sm font-medium">
                        {dragging ? "Drop it" : "Drop your deck here"}
                      </span>
                      <span className="text-xs text-muted-foreground">PDF, up to 25MB — or click to browse</span>
                    </>
                  )}
                  <input
                    ref={inputRef}
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </button>

                <div className="flex justify-center pt-2">
                  <Button
                    type="submit"
                    disabled={!canSubmit}
                    className={cn(
                      "h-11 rounded-lg px-6 text-sm font-semibold shadow-sm transition-opacity",
                      !canSubmit && "pointer-events-none opacity-40"
                    )}>
                    Submit for scoring
                  </Button>
                </div>
                <p className="text-center text-[11px] text-muted-foreground">
                  We also read public signals — GitHub, Devpost, arXiv — so thin decks still get a fair look.
                </p>
              </form>
            </motion.div>
          ) : (
            <motion.div
              key="done"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col items-center text-center">
              <motion.span
                initial={{ scale: 0.4 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 400, damping: 16, delay: 0.15 }}
                className="flex size-12 items-center justify-center rounded-full bg-emerald-600 text-white shadow-lg">
                <Check className="size-6" strokeWidth={3} />
              </motion.span>
              <h2 className="mt-4 text-2xl font-semibold tracking-tight">You're in the pipeline.</h2>
              <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
                {company.trim()} is being scored now — deck claims cross-checked against your public
                footprint. You'll hear back with a real decision within 24 hours.
              </p>
              <Link
                to="/founder/f002"
                className="mt-6 text-sm font-medium underline underline-offset-4 transition-opacity hover:opacity-70">
                See what your score page will look like
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
