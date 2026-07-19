import { useEffect, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, ArrowUp, Check, LoaderCircle } from "lucide-react"
import confetti from "canvas-confetti"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { respondToInterview, startInterview } from "@/lib/api"

function TypingDots() {
  return <div className="flex items-center gap-1 px-1 py-1.5">{[0, 1, 2].map((index) => <motion.span key={index} animate={{ opacity: [0.25, 1, 0.25] }} transition={{ duration: 1.1, repeat: Infinity, delay: index * 0.18 }} className="size-1.5 rounded-full bg-slate-400" />)}</div>
}

function Bubble({ from, children }) {
  const mine = from === "founder"
  return <motion.div initial={{ opacity: 0, y: 10, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ type: "spring", stiffness: 400, damping: 30 }} className={cn("flex", mine ? "justify-end" : "justify-start")}><div className={cn("max-w-[85%] rounded-3xl px-4 py-2.5 text-[15px] leading-relaxed", mine ? "rounded-br-lg bg-primary text-primary-foreground" : "rounded-bl-lg bg-card text-foreground card-hairline")}>{children}</div></motion.div>
}

export default function Interview() {
  const { id } = useParams()
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState("")
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState("")
  const endRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    startInterview(id).then((started) => {
      if (cancelled) return
      setSession(started)
      if (started.question) setMessages([{ from: "agent", text: started.question }])
    }).catch((err) => !cancelled && setError(err.message || "Could not start the interview.")).finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [id])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }) }, [messages, loading, sending, session?.completed])
  useEffect(() => {
    if (!session?.completed) return undefined
    const timer = window.setTimeout(() => confetti({ particleCount: 75, spread: 65, startVelocity: 30, origin: { y: 0.7 }, colors: ["#10b981", "#2dd4bf", "#0ea5e9", "#a78bfa"], disableForReducedMotion: true }), 280)
    return () => window.clearTimeout(timer)
  }, [session?.completed])

  const send = async (event) => {
    event.preventDefault()
    const response = draft.trim()
    if (!response || sending || !session || session.completed) return
    setMessages((current) => [...current, { from: "founder", text: response }])
    setDraft(""); setSending(true); setError("")
    try {
      const next = await respondToInterview(session.session_id, response)
      setSession(next)
      if (next.question) setMessages((current) => [...current, { from: "agent", text: next.question }])
    } catch (err) {
      setError(err.message || "Your response wasn’t saved. Please try again.")
      setDraft(response)
    } finally { setSending(false) }
  }

  const completed = session?.completed
  const currentQuestion = session?.question_number ?? 0
  const totalQuestions = session?.total_questions ?? 5

  return <div className="mx-auto flex h-dvh max-w-lg flex-col px-5">
    <header className="glass sticky top-0 z-10 -mx-5 flex items-center gap-3 border-b border-black/5 px-5 py-3.5"><Link to={`/founder/${id}`} className="flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground"><ArrowLeft className="size-4" /></Link><div className="flex-1"><div className="text-sm font-semibold tracking-tight">Founder interview</div><div className="text-xs text-muted-foreground">{completed ? "Complete" : loading ? "Preparing questions…" : `Question ${currentQuestion} of ${totalQuestions}`}</div></div><div className="flex gap-1">{Array.from({ length: totalQuestions }).map((_, index) => <span key={index} className={cn("h-1 w-5 rounded-full transition-colors duration-300", completed || index < currentQuestion - 1 ? "bg-primary" : index === currentQuestion - 1 ? "bg-primary/40" : "bg-border")} />)}</div></header>
    <div className="flex-1 space-y-3 overflow-y-auto py-6">
      {loading && <div className="flex justify-start"><div className="rounded-3xl rounded-bl-lg bg-card px-3 card-hairline"><TypingDots /></div></div>}
      {messages.map((message, index) => <Bubble key={`${message.from}-${index}`} from={message.from}>{message.text}</Bubble>)}
      {sending && <div className="flex justify-start"><div className="rounded-3xl rounded-bl-lg bg-card px-3 card-hairline"><TypingDots /></div></div>}
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>}
      <AnimatePresence>{completed && <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }} className="flex flex-col items-center gap-3 py-8 text-center"><motion.span initial={{ scale: 0.4 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 400, damping: 16, delay: 0.1 }} className="flex size-10 items-center justify-center rounded-full bg-emerald-600 text-white"><Check className="size-5" strokeWidth={3} /></motion.span><div><div className="text-sm font-semibold">That’s everything — thank you.</div><p className="mx-auto mt-1 max-w-xs text-sm text-muted-foreground">Your responses have been recorded and your Founder Score has been recomputed.</p></div><Button asChild variant="outline" className="mt-1 rounded-full"><Link to={`/founder/${id}`}>Back to your score</Link></Button></motion.div>}</AnimatePresence>
      <div ref={endRef} />
    </div>
    {!completed && !loading && <form onSubmit={send} className="sticky bottom-0 -mx-5 border-t border-black/5 bg-background/80 px-5 py-3 backdrop-blur-lg"><div className="flex items-end gap-2"><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={sending ? "Saving…" : "Type your answer"} disabled={sending || !session} autoFocus className="h-11 flex-1 rounded-full border border-input bg-card px-4 text-[15px] outline-none transition-shadow placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20 disabled:opacity-60" /><Button type="submit" size="icon" disabled={sending || !draft.trim() || !session} className="size-11 rounded-full transition-transform active:scale-90">{sending ? <LoaderCircle className="size-4 animate-spin" /> : <ArrowUp className="size-5" strokeWidth={2.5} />}</Button></div></form>}
  </div>
}
