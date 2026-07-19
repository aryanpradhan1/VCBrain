import { useState } from "react"
import { Building2 } from "lucide-react"

import { assetUrl } from "@/lib/api"
import { cn } from "@/lib/utils"

function companySource(sources = []) {
  return sources.find((source) => source.type === "company_website")
}

// Use an explicit company icon or a site favicon. The intentional initial-state
// fallback is better than a random logo or unrelated generated image.
export function CompanyMark({ name, sources, className, imageClassName }) {
  const source = companySource(sources)
  const image = assetUrl(source?.favicon_url || source?.image_url)
  const [failed, setFailed] = useState(false)
  if (image && !failed) return <img src={image} alt={`${name} logo`} loading="lazy" className={cn("object-contain", imageClassName || className)} onError={() => setFailed(true)} />
  return (
    <span className={cn("flex items-center justify-center bg-slate-900 font-semibold text-white", className)} title={`${name} — no public brand mark found`}>
      {name?.[0] || <Building2 className="size-4" />}
    </span>
  )
}

export function SourceMark({ source, className }) {
  const image = assetUrl(source?.favicon_url || source?.image_url)
  const [failed, setFailed] = useState(false)
  if (image && !failed) return <img src={image} alt="" className={cn("rounded object-contain", className)} onError={() => setFailed(true)} />
  const host = (() => { try { return new URL(source?.url).hostname.replace(/^www\./, "") } catch { return "" } })()
  return <span className={cn("flex items-center justify-center rounded bg-secondary text-[9px] font-bold text-muted-foreground uppercase", className)} title={host || source?.source}>{(host || source?.type || "S").slice(0, 1)}</span>
}
