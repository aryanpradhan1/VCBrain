import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Database, ExternalLink, Network, Users } from "lucide-react"

import { CompanyMark } from "@/components/shared/company-mark"
import { assetUrl } from "@/lib/api"
import { cn } from "@/lib/utils"

const WIDTH = 1120
const LEFT = { source: 20, affiliation: 218, person: 445, company: 750, memory: 1010 }

function hostname(url) {
  try { return new URL(url).hostname.replace(/^www\./, "") } catch { return "Public source" }
}

function yScale(index, count, height, top = 54, bottom = 54) {
  if (count <= 1) return height / 2
  return top + (index * (height - top - bottom)) / (count - 1)
}

function GraphNode({ x, y, children, className, faded = false }) {
  return (
    <div
      className={cn("absolute z-10 -translate-y-1/2 transition-all duration-200", faded && "opacity-20", className)}
      style={{ left: x, top: y }}>
      {children}
    </div>
  )
}

function Edge({ from, to, tone, faded }) {
  const midpoint = (from.x + to.x) / 2
  return (
    <path
      d={`M ${from.x} ${from.y} C ${midpoint} ${from.y}, ${midpoint} ${to.y}, ${to.x} ${to.y}`}
      fill="none"
      stroke={tone}
      strokeWidth={faded ? 0.7 : 1.35}
      opacity={faded ? 0.08 : 0.4}
      className="transition-all duration-200"
    />
  )
}

export function SourcingIntelligence({ opportunities = [] }) {
  const [focus, setFocus] = useState(null)
  const [scope, setScope] = useState("public")
  const graph = useMemo(() => {
    const companies = scope === "all" ? opportunities : opportunities.filter((item) => item.enrichment?.reference_profile)
    const people = companies.flatMap((company) =>
      (company.enrichment?.founders || []).map((person) => ({ ...person, companyId: company.company_id, companyName: company.company_name }))
    )
    const affiliations = Array.from(new Set(people.flatMap((person) => person.affiliations || []).filter((name) => !companies.some((company) => company.company_name === name))))
    const sources = Array.from(new Set(companies.flatMap((company) => (company.sources || []).map((source) => hostname(source.url)))))
    const height = Math.max(650, people.length * 55 + 90, affiliations.length * 42 + 90, sources.length * 48 + 90)

    const peopleWithPosition = people.map((person, index) => ({ ...person, x: LEFT.person, y: yScale(index, people.length, height) }))
    const companiesWithPosition = companies.map((company) => {
      const ownPeople = peopleWithPosition.filter((person) => person.companyId === company.company_id)
      const y = ownPeople.length ? ownPeople.reduce((sum, person) => sum + person.y, 0) / ownPeople.length : height / 2
      return { ...company, x: LEFT.company, y }
    })
    const affiliationsWithPosition = affiliations.map((name, index) => ({ name, x: LEFT.affiliation, y: yScale(index, affiliations.length, height) }))
    const sourcesWithPosition = sources.map((name, index) => ({ name, x: LEFT.source, y: yScale(index, sources.length, height) }))

    const edges = []
    for (const person of peopleWithPosition) {
      const company = companiesWithPosition.find((item) => item.company_id === person.companyId)
      if (company) edges.push({ from: { x: person.x + 174, y: person.y }, to: { x: company.x, y: company.y }, companyId: person.companyId, tone: "#8b5cf6" })
      for (const affiliation of person.affiliations || []) {
        const node = affiliationsWithPosition.find((item) => item.name === affiliation)
        if (node) edges.push({ from: { x: node.x + 154, y: node.y }, to: { x: person.x, y: person.y }, companyId: person.companyId, tone: "#38bdf8" })
      }
    }
    for (const company of companiesWithPosition) {
      const companySources = new Set((company.sources || []).map((source) => hostname(source.url)))
      for (const source of sourcesWithPosition.filter((item) => companySources.has(item.name))) {
        edges.push({ from: { x: source.x + 148, y: source.y }, to: { x: company.x, y: company.y }, companyId: company.company_id, tone: "#94a3b8" })
      }
      edges.push({ from: { x: company.x + 184, y: company.y }, to: { x: LEFT.memory, y: height / 2 }, companyId: company.company_id, tone: "#10b981" })
    }
    return { companies: companiesWithPosition, people: peopleWithPosition, affiliations: affiliationsWithPosition, sources: sourcesWithPosition, edges, height }
  }, [opportunities, scope])

  if (!graph.companies.length) return null
  const connected = (companyId) => !focus || focus === companyId

  return (
    <section className="mb-6 overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border bg-slate-50/70 px-4 py-3.5">
        <div className="flex items-start gap-2.5">
          <span className="mt-0.5 flex size-7 items-center justify-center rounded-lg bg-violet-100 text-violet-700"><Network className="size-3.5" /></span>
          <div>
            <h2 className="text-sm font-semibold tracking-tight">Sourcing & network intelligence</h2>
            <p className="mt-0.5 text-[11px] text-muted-foreground">Companies mapped to people, affiliations, evidence sources, and persistent Memory.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <div className="flex rounded-lg border border-border bg-white p-0.5 text-[10px] font-semibold">
            <button type="button" onClick={() => { setScope("public"); setFocus(null) }} className={cn("rounded-md px-2.5 py-1", scope === "public" ? "bg-slate-900 text-white" : "text-muted-foreground")}>Verified public</button>
            <button type="button" onClick={() => { setScope("all"); setFocus(null) }} className={cn("rounded-md px-2.5 py-1", scope === "all" ? "bg-slate-900 text-white" : "text-muted-foreground")}>Entire pipeline</button>
          </div>
          <div className="flex items-center gap-2 text-[10px] font-medium text-muted-foreground">
            <span>{graph.companies.length} companies</span><span>·</span><span>{graph.people.length} founders</span><span>·</span><span>{graph.edges.length} evidence edges</span>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-border px-4 py-2.5 text-[10px] font-medium text-muted-foreground">
        <Legend tone="bg-slate-400" label="source → company" />
        <Legend tone="bg-sky-400" label="affiliation → person" />
        <Legend tone="bg-violet-500" label="person → company" />
        <Legend tone="bg-emerald-500" label="company → Memory" />
        <span className="ml-auto">Hover a company to isolate its network</span>
      </div>

      <div className="overflow-x-auto bg-[radial-gradient(circle_at_center,_#f8fafc_0,_#fff_70%)]">
        <div className="relative min-w-[1120px]" style={{ width: WIDTH, height: graph.height }} onMouseLeave={() => setFocus(null)}>
          <ColumnLabel x={LEFT.source} label="Evidence sources" />
          <ColumnLabel x={LEFT.affiliation} label="Institutions & history" />
          <ColumnLabel x={LEFT.person} label="People" />
          <ColumnLabel x={LEFT.company} label="Companies" />
          <ColumnLabel x={LEFT.memory} label="Memory" />

          <svg aria-label="Founder sourcing network" className="absolute inset-0 size-full" viewBox={`0 0 ${WIDTH} ${graph.height}`}>
            {graph.edges.map((edge, index) => <Edge key={index} from={edge.from} to={edge.to} tone={edge.tone} faded={!connected(edge.companyId)} />)}
          </svg>

          {graph.sources.map((source) => (
            <GraphNode key={source.name} x={source.x} y={source.y} className="w-[148px]">
              <div className="truncate rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-[10px] font-semibold text-slate-600 shadow-sm" title={source.name}>{source.name}</div>
            </GraphNode>
          ))}

          {graph.affiliations.map((affiliation) => (
            <GraphNode key={affiliation.name} x={affiliation.x} y={affiliation.y} className="w-[154px]">
              <div className="truncate rounded-lg border border-sky-100 bg-sky-50 px-2.5 py-2 text-[10px] font-semibold text-sky-800" title={affiliation.name}>{affiliation.name}</div>
            </GraphNode>
          ))}

          {graph.people.map((person) => (
            <GraphNode key={`${person.companyId}-${person.name}`} x={person.x} y={person.y} faded={!connected(person.companyId)} className="w-[174px]">
              <div className="flex items-center gap-2 rounded-xl border border-violet-100 bg-white p-2 shadow-sm">
                {person.avatar && <img src={assetUrl(person.avatar)} alt={person.name} className="size-9 shrink-0 rounded-lg object-cover" />}
                <div className="min-w-0"><div className="truncate text-[10px] font-semibold text-slate-800">{person.name}</div><div className="truncate text-[9px] text-muted-foreground">{person.role}</div></div>
              </div>
            </GraphNode>
          ))}

          {graph.companies.map((company) => (
            <GraphNode key={company.company_id} x={company.x} y={company.y} faded={!connected(company.company_id)} className="w-[184px]">
              <Link
                to={`/opportunities/${company.company_id}`}
                onMouseEnter={() => setFocus(company.company_id)}
                className="flex items-center gap-2.5 rounded-xl border border-slate-200 bg-white p-2.5 shadow-sm transition-transform hover:-translate-y-0.5 hover:border-violet-300 hover:shadow-md">
                {company.sources?.some((source) => source.type === "company_website" && (source.favicon_url || source.image_url)) && (
                  <CompanyMark name={company.company_name} sources={company.sources} className="size-10 rounded-lg text-xs" imageClassName="size-10 shrink-0 rounded-lg border border-slate-100 bg-white object-contain p-1" />
                )}
                <div className="min-w-0 flex-1"><div className="truncate text-[11px] font-semibold">{company.company_name}</div><div className="truncate text-[9px] text-muted-foreground">{company.enrichment?.reference_batch || company.enrichment?.sector}</div></div>
                <ExternalLink className="size-3 shrink-0 text-slate-300" />
              </Link>
            </GraphNode>
          ))}

          <GraphNode x={LEFT.memory} y={graph.height / 2} className="w-[96px]">
            <div className="flex flex-col items-center rounded-2xl bg-slate-900 px-3 py-4 text-center text-white shadow-lg">
              <Database className="size-5 text-emerald-300" />
              <span className="mt-1.5 text-[10px] font-semibold">FounderScore</span>
              <span className="text-[8px] text-slate-300">Memory</span>
            </div>
          </GraphNode>
        </div>
      </div>

      <div className="flex items-center gap-2 border-t border-border bg-slate-50/60 px-4 py-3 text-[10px] leading-relaxed text-muted-foreground">
        <Users className="size-3.5 shrink-0" />
        {scope === "public" ? "Verified-public network: real company marks and founder portraits from cited official profiles." : "Entire pipeline: records without verified brand or portrait evidence remain text-only—no fake logos or guessed identities."} Live applications use bounded enrichment.
      </div>
    </section>
  )
}

function ColumnLabel({ x, label }) {
  return <div className="absolute top-3 z-20 text-[9px] font-semibold tracking-[0.1em] text-slate-400 uppercase" style={{ left: x }}>{label}</div>
}

function Legend({ tone, label }) {
  return <span className="inline-flex items-center gap-1.5"><span className={cn("h-px w-4", tone)} />{label}</span>
}
