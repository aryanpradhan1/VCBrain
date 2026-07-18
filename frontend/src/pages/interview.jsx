import { useEffect, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, ArrowUp, Check } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Founder-facing live interview. 4–5 adaptive questions; the resulting
// response_pattern / resilience_score feed the backend and are NEVER shown here.
const QUESTIONS = [
  "Thanks for making time — this stays short. First: what's the single strongest piece of evidence that customers want what you're building?",
  "If that evidence turned out to be weaker than you think — say the numbers don't replicate — what would you do in the following 30 days?",
  "What's the most important thing you've changed your mind about since starting this company, and what changed it?",
  "Who is the one hire that would most change your trajectory right now, and what's your realistic plan to get them?",
  "Last one: what should we have asked about that we didn't? Anything you'd want an investor to weigh.",
]

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
  const [qIndex, setQIndex] = useState(0)
  const [done, setDone] = useState(false)
  const endRef = useRef(null)

  // Agent "types", then asks the next question.
  useEffect(() => {
    if (!typing) return
    const t = setTimeout(() => {
      setMessages((m) => [...m, { from: "agent", text: QUESTIONS[qIndex] }])
      setTyping(false)
    }, 1100 + Math.random() * 500)
    return () => clearTimeout(t)
  }, [typing, qIndex])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, typing, done])

  const send = (e) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text || typing || done) return
    setMessages((m) => [...m, { from: "founder", text }])
    setDraft("")
    if (qIndex + 1 < QUESTIONS.length) {
      setQIndex((i) => i + 1)
      setTyping(true)
    } else {
      setTimeout(() => setDone(true), 700)
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
            {done ? "Complete" : `Question ${Math.min(qIndex + 1, QUESTIONS.length)} of ${QUESTIONS.length}`}
          </div>
        </div>
        <div className="flex gap-1">
          {QUESTIONS.map((_, i) => (
            <span
              key={i}
              className={cn(
                "h-1 w-5 rounded-full transition-colors duration-300",
                i < qIndex || done ? "bg-primary" : i === qIndex ? "bg-primary/40" : "bg-border"
              )}
            />
          ))}
        </div>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto py-6">
        {messages.map((m, i) => (
          <Bubble key={i} from={m.from}>
            {m.text}
          </Bubble>
        ))}
        {typing && (
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
