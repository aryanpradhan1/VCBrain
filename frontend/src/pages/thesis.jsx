import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Check, LoaderCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Page } from "@/components/shared/page"
import { getThesis, saveThesis } from "@/lib/api"
import { cn } from "@/lib/utils"

const SECTORS = ["AI infrastructure", "Developer tools", "Fintech", "Healthcare", "Robotics", "Climate", "E-commerce", "Bio", "Consumer", "Defense"]
const STAGES = ["Pre-seed", "Seed", "Series A"]
const GEOS = ["North America", "Europe", "LATAM", "Africa", "South Asia", "East Asia"]
const CHECKS = ["$50K", "$100K", "$250K"]
const OWNERSHIP = ["0.5–1%", "1–2%", "2–5%"]
const RISK = ["Conservative", "Balanced", "Aggressive"]
const DEFAULTS = { sectors: ["AI infrastructure", "Developer tools", "Robotics"], stage: "Pre-seed", geos: ["North America", "Europe"], check: "$100K", ownership: "1–2%", risk: "Balanced" }

function Chip({ active, onClick, children }) {
  return <button type="button" onClick={onClick} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-medium transition-all duration-150 active:scale-95", active ? "border-primary bg-primary text-primary-foreground" : "border-border bg-card text-muted-foreground hover:border-slate-300 hover:text-foreground")}>{children}</button>
}

function Segmented({ options, value, onChange, layoutId }) {
  return <div className="inline-flex rounded-full bg-secondary p-1">{options.map((option) => <button key={option} type="button" onClick={() => onChange(option)} className="relative rounded-full px-4 py-1.5 text-sm font-medium">{value === option && <motion.span layoutId={layoutId} transition={{ type: "spring", stiffness: 500, damping: 35 }} className="absolute inset-0 rounded-full bg-card card-hairline" />}<span className={cn("relative", value === option ? "text-foreground" : "text-muted-foreground")}>{option}</span></button>)}</div>
}

function Field({ label, hint, children }) {
  return <div><div className="mb-2 flex items-baseline gap-2"><span className="text-sm font-semibold tracking-tight">{label}</span>{hint && <span className="text-xs text-muted-foreground">{hint}</span>}</div>{children}</div>
}

export default function Thesis() {
  const [config, setConfig] = useState(DEFAULTS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    getThesis().then((data) => setConfig(data)).catch((err) => setError(err.message || "Could not load the fund thesis.")).finally(() => setLoading(false))
  }, [])
  useEffect(() => {
    if (!saved) return undefined
    const timer = window.setTimeout(() => setSaved(false), 2200)
    return () => window.clearTimeout(timer)
  }, [saved])

  const toggle = (key, item) => setConfig((current) => ({ ...current, [key]: current[key].includes(item) ? current[key].filter((value) => value !== item) : [...current[key], item] }))
  const save = async () => {
    setSaving(true); setError("")
    try { setConfig(await saveThesis(config)); setSaved(true) } catch (err) { setError(err.message || "Could not save the thesis.") } finally { setSaving(false) }
  }

  return <Page>
    <div className="mb-6"><h1 className="text-2xl font-semibold tracking-tight">Thesis Engine</h1><p className="mt-1 text-sm text-muted-foreground">The persisted deterministic gate every future inbound and sourced founder passes through. Ambiguous matches go to a separate LLM fit judgment.</p></div>
    <Card><CardHeader><CardTitle>Fund thesis</CardTitle><CardDescription>Stored in the application database. Changes apply to the next analysis and leave existing decisions auditable.</CardDescription></CardHeader><CardContent className="space-y-7">
      {loading ? <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground"><LoaderCircle className="size-4 animate-spin" /> Loading thesis…</div> : <>
        <Field label="Sectors" hint="select all that apply"><div className="flex flex-wrap gap-2">{SECTORS.map((sector) => <Chip key={sector} active={config.sectors.includes(sector)} onClick={() => toggle("sectors", sector)}>{sector}</Chip>)}</div></Field>
        <Field label="Stage"><Segmented options={STAGES} value={config.stage} onChange={(stage) => setConfig((current) => ({ ...current, stage }))} layoutId="seg-stage" /></Field>
        <Field label="Geography" hint="select all that apply"><div className="flex flex-wrap gap-2">{GEOS.map((geo) => <Chip key={geo} active={config.geos.includes(geo)} onClick={() => toggle("geos", geo)}>{geo}</Chip>)}</div></Field>
        <div className="grid gap-7 sm:grid-cols-3"><Field label="Check size"><Segmented options={CHECKS} value={config.check} onChange={(check) => setConfig((current) => ({ ...current, check }))} layoutId="seg-check" /></Field><Field label="Ownership target"><Segmented options={OWNERSHIP} value={config.ownership} onChange={(ownership) => setConfig((current) => ({ ...current, ownership }))} layoutId="seg-own" /></Field><Field label="Risk appetite"><Segmented options={RISK} value={config.risk} onChange={(risk) => setConfig((current) => ({ ...current, risk }))} layoutId="seg-risk" /></Field></div>
        <div className="flex flex-wrap items-center gap-3 border-t border-border pt-5"><Button onClick={save} disabled={saving || !config.sectors.length || !config.geos.length} className="rounded-full px-5">{saving && <LoaderCircle className="size-4 animate-spin" />} Save thesis</Button><AnimatePresence>{saved && <motion.span initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-600"><Check className="size-4" strokeWidth={2.5} /> Saved to the shared workspace</motion.span>}</AnimatePresence>{error && <span className="text-xs text-red-600">{error}</span>}</div>
      </>}
    </CardContent></Card>
  </Page>
}
