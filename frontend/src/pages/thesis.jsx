import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Check } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Page } from "@/components/shared/page"
import { cn } from "@/lib/utils"

const SECTORS = [
  "AI infrastructure", "Developer tools", "Fintech", "Healthcare", "Robotics",
  "Climate", "E-commerce", "Bio", "Consumer", "Defense",
]
const STAGES = ["Pre-seed", "Seed", "Series A"]
const GEOS = ["North America", "Europe", "LATAM", "Africa", "South Asia", "East Asia"]
const CHECKS = ["$50K", "$100K", "$250K"]
const OWNERSHIP = ["0.5–1%", "1–2%", "2–5%"]
const RISK = ["Conservative", "Balanced", "Aggressive"]

const DEFAULTS = {
  sectors: ["AI infrastructure", "Developer tools", "Robotics"],
  stage: "Pre-seed",
  geos: ["North America", "Europe"],
  check: "$100K",
  ownership: "1–2%",
  risk: "Balanced",
}

const STORAGE_KEY = "founderscore.thesis"

function Chip({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-3.5 py-1.5 text-sm font-medium transition-all duration-150 active:scale-95",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-card text-muted-foreground hover:border-slate-300 hover:text-foreground"
      )}>
      {children}
    </button>
  )
}

function Segmented({ options, value, onChange, layoutId }) {
  return (
    <div className="inline-flex rounded-full bg-secondary p-1">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className="relative rounded-full px-4 py-1.5 text-sm font-medium">
          {value === opt && (
            <motion.span
              layoutId={layoutId}
              transition={{ type: "spring", stiffness: 500, damping: 35 }}
              className="absolute inset-0 rounded-full bg-card card-hairline"
            />
          )}
          <span className={cn("relative", value === opt ? "text-foreground" : "text-muted-foreground")}>
            {opt}
          </span>
        </button>
      ))}
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <div>
      <div className="mb-2 flex items-baseline gap-2">
        <span className="text-sm font-semibold tracking-tight">{label}</span>
        {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
      </div>
      {children}
    </div>
  )
}

export default function Thesis() {
  const [config, setConfig] = useState(() => {
    try {
      return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") }
    } catch {
      return DEFAULTS
    }
  })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!saved) return
    const t = setTimeout(() => setSaved(false), 2200)
    return () => clearTimeout(t)
  }, [saved])

  const toggle = (key, item) =>
    setConfig((c) => ({
      ...c,
      [key]: c[key].includes(item) ? c[key].filter((x) => x !== item) : [...c[key], item],
    }))

  const save = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    setSaved(true)
  }

  return (
    <Page>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Thesis Engine</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          The deterministic gate every sourced and inbound founder passes through. Ambiguous matches
          go to LLM fit judgment; everything else is filtered here.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Fund thesis</CardTitle>
          <CardDescription>Configurable, never hardcoded — changes apply to the next scan.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-7">
          <Field label="Sectors" hint="select all that apply">
            <div className="flex flex-wrap gap-2">
              {SECTORS.map((s) => (
                <Chip key={s} active={config.sectors.includes(s)} onClick={() => toggle("sectors", s)}>
                  {s}
                </Chip>
              ))}
            </div>
          </Field>

          <Field label="Stage">
            <Segmented options={STAGES} value={config.stage} onChange={(v) => setConfig((c) => ({ ...c, stage: v }))} layoutId="seg-stage" />
          </Field>

          <Field label="Geography" hint="select all that apply">
            <div className="flex flex-wrap gap-2">
              {GEOS.map((g) => (
                <Chip key={g} active={config.geos.includes(g)} onClick={() => toggle("geos", g)}>
                  {g}
                </Chip>
              ))}
            </div>
          </Field>

          <div className="grid gap-7 sm:grid-cols-3">
            <Field label="Check size">
              <Segmented options={CHECKS} value={config.check} onChange={(v) => setConfig((c) => ({ ...c, check: v }))} layoutId="seg-check" />
            </Field>
            <Field label="Ownership target">
              <Segmented options={OWNERSHIP} value={config.ownership} onChange={(v) => setConfig((c) => ({ ...c, ownership: v }))} layoutId="seg-own" />
            </Field>
            <Field label="Risk appetite">
              <Segmented options={RISK} value={config.risk} onChange={(v) => setConfig((c) => ({ ...c, risk: v }))} layoutId="seg-risk" />
            </Field>
          </div>

          <div className="flex items-center gap-3 border-t border-border pt-5">
            <Button onClick={save} className="rounded-full px-5">
              Save thesis
            </Button>
            <AnimatePresence>
              {saved && (
                <motion.span
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-600">
                  <Check className="size-4" strokeWidth={2.5} />
                  Saved — applies to the next scan
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </CardContent>
      </Card>
    </Page>
  )
}
