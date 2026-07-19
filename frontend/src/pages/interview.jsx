import { useEffect, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, ArrowUp, Check } from "lucide-react"
import confetti from "canvas-confetti"

import { ErrorBanner } from "@/components/shared/states"
import { Button } from "@/components/ui/button"
import { respondToFounderInterview, startFounderInterview } from "@/lib/api"
import { cn } from "@/lib/utils"

// Founder-facing live interview. 4–5 adaptive questions; the resulting
// response_pattern / resilience_score feed the backend and are NEVER shown here.

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-1.5">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          animate={{ opacity: [0.25, 1, 0.25] }}
          transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.18 }}
          className="size-1.5 rounded-full bg-slate-400"
        />
      ))}
    </div>
  )
}

function Bubble({ from, children }) {
  const mine = from === "founder"
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={cn("flex", mine ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-3xl px-4 py-2.5 text-[15px] leading-relaxed",
          mine
            ? "rounded-br-lg bg-primary text-primary-foreground"
            : "rounded-bl-lg bg-card text-foreground card-hairline"
        )}>
        {children}
      </div>
    </motion.div>
  )
}

export default function Interview() {
  const { id } = useParams()
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState("")
  const [typing, setTyping] = useState(true)
  const [progress, setProgress] = useState(null)
  const [done, setDone] = useState(false)
  const [error, setError] = useState(null)
  const endRef = useRef(null)

  // Start C's interview session and render its first claim-specific question.
  useEffect(() => {
    let active = true
    startFounderInterview(id)
      .then((next) => {
        if (!active) return
        setProgress(next)
        setMessages(next.question ? [{ from: "agent", text: next.question }] : [])
        setTyping(false)
      })
      .catch(() => {
        if (!active) return
        setError("Couldn't start the interview just now.")
        setTyping(false)
      })
    return () => { active = false }
  }, [id])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, typing, done])

  // A brief, tasteful burst when the interview completes.
  useEffect(() => {
    if (!done) return
    const t = setTimeout(() => {
      confetti({
        particleCount: 90,
        spread: 70,
        startVelocity: 32,
        origin: { y: 0.7 },
        colors: ["#10b981", "#2dd4bf", "#0ea5e9", "#a78bfa"],
        disableForReducedMotion: true,
      })
    }, 350)
    return () => clearTimeout(t)
  }, [done])

  const send = async (e) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text || typing || done) return
    setMessages((m) => [...m, { from: "founder", text }])
    setDraft("")
    setTyping(true)
    setError(null)
    try {
      const next = await respondToFounderInterview(id, text)
      setProgress(next)
      if (next.complete) {
        setDone(true)
      } else if (next.question) {
        setMessages((m) => [...m, { from: "agent", text: next.question }])
      }
    } catch {
      setError("Your answer couldn't be saved. Please try again.")
      setDraft(text)
    } finally {
      setTyping(false)
    }
  }

  return (
    <div className="mx-auto flex h-dvh max-w-lg flex-col px-5">
      <header className="glass sticky top-0 z-10 -mx-5 flex items-center gap-3 border-b border-black/5 px-5 py-3.5">
        <Link
          to={`/founder/${id}`}
          className="flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" />
        </Link>
        <div className="flex-1">
          <div className="text-sm font-semibold tracking-tight">Founder interview</div>
          <div className="text-xs text-muted-foreground">
            {done ? "Complete" : progress ? `Question ${progress.question_number} of ${progress.total_questions}` : "Starting…"}
          </div>
        </div>
        <div className="flex gap-1">
          {Array.from({ length: progress?.total_questions ?? 5 }, (_, i) => (
            <span
              key={i}
              className={cn(
                "h-1 w-5 rounded-full transition-colors duration-300",
                done || i < (progress?.question_number ?? 1) - 1
                  ? "bg-primary"
                  : i === (progress?.question_number ?? 1) - 1
                    ? "bg-primary/40"
                    : "bg-border"
              )}
            />
          ))}
        </div>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto py-6">
        {error && <ErrorBanner message={error} />}
        {messages.map((m, i) => (
          <Bubble key={i} from={m.from}>
            {m.text}
          </Bubble>
        ))}
        {typing && !done && (
          <div className="flex justify-start">
            <div className="rounded-3xl rounded-bl-lg bg-card px-3 card-hairline">
              <TypingDots />
            </div>
          </div>
        )}
        <AnimatePresence>
          {done && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col items-center gap-3 py-8 text-center">
              <motion.span
                initial={{ scale: 0.4 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 400, damping: 16, delay: 0.1 }}
                className="flex size-10 items-center justify-center rounded-full bg-emerald-600 text-white">
                <Check className="size-5" strokeWidth={3} />
              </motion.span>
              <div>
                <div className="text-sm font-semibold">That's everything — thank you.</div>
                <p className="mx-auto mt-1 max-w-xs text-sm text-muted-foreground">
                  Your answers are being reviewed and your Founder Score will update shortly.
                </p>
              </div>
              <Button asChild variant="outline" className="mt-1 rounded-full">
                <Link to={`/founder/${id}`}>Back to your score</Link>
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={endRef} />
      </div>

      {!done && (
        <form onSubmit={send} className="sticky bottom-0 -mx-5 border-t border-black/5 bg-background/80 px-5 py-3 backdrop-blur-lg">
          <div className="flex items-end gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={typing ? "…" : "Type your answer"}
              disabled={typing}
              autoFocus
              className="h-11 flex-1 rounded-full border border-input bg-card px-4 text-[15px] outline-none transition-shadow placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20 disabled:opacity-60"
            />
            <Button
              type="submit"
              size="icon"
              disabled={typing || !draft.trim()}
              className="size-11 rounded-full transition-transform active:scale-90">
              <ArrowUp className="size-5" strokeWidth={2.5} />
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
