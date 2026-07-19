import { useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Check, CircleCheck, CircleMinus, CircleX } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { postDecision } from "@/lib/api"
import { fmtAmount } from "./semantics"

const options = [
  {
    key: "approve",
    label: "Approve",
    Icon: CircleCheck,
    cls: "border-emerald-300 bg-white text-emerald-700 hover:bg-emerald-50 focus-visible:ring-emerald-200",
    confirmCls: "bg-emerald-600",
  },
  {
    key: "review",
    label: "Review",
    Icon: CircleMinus,
    cls: "border-border bg-white text-foreground hover:bg-muted",
    confirmCls: "bg-slate-700",
  },
  {
    key: "decline",
    label: "Decline",
    Icon: CircleX,
    cls: "border-red-300 bg-white text-red-600 hover:bg-red-50 focus-visible:ring-red-200",
    confirmCls: "bg-red-600",
  },
]

// Approve / Review / Decline — always shown together, amount always visible.
export function DecisionBar({ opportunity, className }) {
  const [pending, setPending] = useState(null)
  const [confirmed, setConfirmed] = useState(null)

  const decide = async (key) => {
    setPending(key)
    try {
      await postDecision(opportunity.company_id, key)
      setConfirmed(key)
    } finally {
      setPending(null)
    }
  }

  const confirmedOpt = options.find((o) => o.key === confirmed)

  return (
    <div className={cn("relative overflow-hidden rounded-2xl bg-card p-5 card-hairline", className)}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            Investment decision
          </div>
          {opportunity.amount_recommended > 0 ? <><div className="text-2xl font-semibold tracking-tight tabular-nums">{fmtAmount(opportunity.amount_recommended)}</div><p className="mt-0.5 text-[11px] text-muted-foreground">Recommended check, subject to partner decision</p></> : <><div className="text-xl font-semibold tracking-tight">No check recommended</div><p className="mt-0.5 text-[11px] text-muted-foreground">Record a review decision or override with documented conviction.</p></>}
        </div>
        <div className="flex items-center gap-2">
          {options.map(({ key, label, Icon, cls }) => (
            <Button
              key={key}
              variant="outline"
              disabled={pending !== null}
              onClick={() => decide(key)}
              className={cn("rounded-full px-4", cls)}>
              <Icon data-icon="inline-start" />
              {pending === key ? "Saving…" : label}
            </Button>
          ))}
        </div>
      </div>

      <AnimatePresence>
        {confirmed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 z-10 flex items-center justify-center gap-3 bg-card/90 backdrop-blur-sm">
            <motion.span
              initial={{ scale: 0.4, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 400, damping: 18 }}
              className={cn(
                "flex size-9 items-center justify-center rounded-full text-white",
                confirmedOpt?.confirmCls
              )}>
              <Check className="size-5" strokeWidth={3} />
            </motion.span>
            <motion.div
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 }}
              className="text-sm">
              <div className="font-semibold">Decision recorded — {confirmedOpt?.label}</div>
              <div className="text-muted-foreground">
                Logged for {opportunity.company_name}.{" "}
                <button
                  type="button"
                  onClick={() => setConfirmed(null)}
                  className="font-medium text-foreground underline underline-offset-2 hover:opacity-70">
                  Change
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
