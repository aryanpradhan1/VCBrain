import { createContext, useCallback, useContext, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import {
  ExternalLink,
  FileText,
  FlaskConical,
  GitBranch,
  MessageCircle,
  Newspaper,
  Rocket,
  UserSearch,
  X,
} from "lucide-react"

// Every citation in the product opens here — sources always lead somewhere.
// Content is a faithful dummy of what the real pipeline stores (deck slide
// extract, repo stats, interview transcript, press item), never a dead end.

const SourceContext = createContext({ open: () => {} })
export const useSources = () => useContext(SourceContext)

function classify(text) {
  if (/deck slide|slide \d/i.test(text)) return "deck"
  if (/github/i.test(text)) return "github"
  if (/interview/i.test(text)) return "interview"
  if (/devpost|show hn|hacker news|upvote/i.test(text)) return "launch"
  if (/arxiv|paper|publication/i.test(text)) return "paper"
  if (/linkedin|crunchbase|press|reference/i.test(text)) return "person"
  return "generic"
}

const typeMeta = {
  deck: { icon: FileText, label: "Pitch deck extract" },
  github: { icon: GitBranch, label: "GitHub signal" },
  interview: { icon: MessageCircle, label: "Interview transcript" },
  launch: { icon: Rocket, label: "Launch signal" },
  paper: { icon: FlaskConical, label: "Publication" },
  person: { icon: UserSearch, label: "Identity cross-reference" },
  news: { icon: Newspaper, label: "Press coverage" },
  generic: { icon: FileText, label: "Source" },
}

function DeckSlide({ citation, opp }) {
  const slideNum = citation.match(/slide (\d+)/i)?.[1] ?? "—"
  const claim = citation.split(/:\s(.+)/)[1] ?? citation
  return (
    <div>
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2">
          <span className="text-xs font-semibold">{opp?.company_name} — pitch deck</span>
          <span className="text-[10px] text-muted-foreground tabular-nums">slide {slideNum}</span>
        </div>
        <div className="space-y-3 p-5">
          <div className="text-lg font-semibold tracking-tight capitalize">{claim.split(/[,;—]/)[0]}</div>
          <div className="flex items-end gap-1.5 pt-1">
            {[34, 55, 42, 70, 88].map((h, i) => (
              <div key={i} className="w-8 rounded-t-[4px] bg-sky-200" style={{ height: h * 0.7 }} />
            ))}
          </div>
          <p className="text-xs leading-relaxed text-slate-500">"{claim}"</p>
        </div>
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">
        Extracted by Signal Intake from the uploaded PDF — stored as a structured claim, never the raw page.
      </p>
    </div>
  )
}

function GithubCard({ opp }) {
  const gh = opp?.public_signals?.github
  const founder = opp?.enrichment?.founders?.find((f) => f.github)
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <GitBranch className="size-4" />
        {founder ? founder.github.replace("https://github.com/", "@") : "GitHub footprint"}
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        {[
          ["Repos", gh?.repos ?? "—"],
          ["Consistency", gh ? `${Math.round(gh.commit_consistency_score * 100)}%` : "—"],
          ["Active", gh ? `${gh.longevity_months}mo` : "—"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-lg bg-slate-50 py-2">
            <div className="text-base font-semibold tabular-nums">{v}</div>
            <div className="text-[10px] text-muted-foreground">{k}</div>
          </div>
        ))}
      </div>
      {founder && (
        <a
          href={founder.github}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-sky-700 hover:underline">
          Open profile <ExternalLink className="size-3" />
        </a>
      )}
      <p className="mt-2 text-[11px] text-muted-foreground">
        Pulled live by Signal Intake; consistency is a computed statistic — deliberately not AI.
      </p>
    </div>
  )
}

function InterviewCard({ citation }) {
  const excerpt = citation.split(/:\s(.+)/)[1] ?? citation
  return (
    <div className="space-y-2">
      <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-slate-200 bg-white px-3.5 py-2.5 text-[13px] leading-relaxed shadow-sm">
        Walk me through the number behind that claim — what's it based on?
      </div>
      <div className="ml-auto max-w-[90%] rounded-2xl rounded-br-md bg-slate-900 px-3.5 py-2.5 text-[13px] leading-relaxed text-white">
        …{excerpt}
      </div>
      <p className="pt-1 text-[11px] text-muted-foreground">
        Interview Agent transcript extract. Scored on response pattern (engage / update / deflect), never answer content.
      </p>
    </div>
  )
}

function NewsCard({ source }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-[10px] font-semibold tracking-wide text-muted-foreground uppercase">
        {source.newsSource} · {source.date}
      </div>
      <div className="mt-1 text-sm font-semibold leading-snug">{source.title}</div>
      <p className="mt-2 text-xs leading-relaxed text-slate-500">
        Indexed by Signal Intake's bounded press scan and linked to this founder's record in Memory. Full text stays at
        the publisher — only the structured reference is stored.
      </p>
    </div>
  )
}

function StructuredSource({ record }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      {record.image_url && (
        <img src={record.image_url} alt="" className="h-36 w-full object-cover" onError={(event) => { event.currentTarget.style.display = "none" }} />
      )}
      <div className="p-4">
        <div className="text-[10px] font-semibold tracking-wide text-muted-foreground uppercase">{record.source || "Source"}{record.page ? ` · slide ${record.page}` : ""}</div>
        <div className="mt-1 text-sm font-semibold leading-snug">{record.title}</div>
        {record.excerpt && <p className="mt-2 text-xs leading-relaxed text-slate-600">{record.excerpt}</p>}
        {record.url && (
          <a href={record.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-sky-700 hover:underline">
            Open original source <ExternalLink className="size-3" />
          </a>
        )}
      </div>
    </div>
  )
}

function GenericCard({ citation }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 text-[13px] leading-relaxed shadow-sm">
      {citation}
      <p className="mt-2 text-[11px] text-muted-foreground">
        Source-tagged entry in the Memory layer — timestamped and deduplicated at intake.
      </p>
    </div>
  )
}

export function SourceDrawerProvider({ children }) {
  const [source, setSource] = useState(null)
  const open = useCallback((s) => setSource(s), [])

  const type = source?.type ?? (source ? classify(source.citation ?? "") : "generic")
  const meta = typeMeta[type] ?? typeMeta.generic
  const Icon = meta.icon

  return (
    <SourceContext.Provider value={{ open }}>
      {children}
      <AnimatePresence>
        {source && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSource(null)}
              className="fixed inset-0 z-50 bg-slate-900/20 backdrop-blur-[2px]"
            />
            <motion.aside
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 400, damping: 40 }}
              className="fixed inset-y-0 right-0 z-50 flex w-full max-w-sm flex-col gap-4 overflow-y-auto border-l border-black/5 bg-background p-5 shadow-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex size-8 items-center justify-center rounded-lg bg-secondary">
                    <Icon className="size-4" />
                  </span>
                  <div className="leading-tight">
                    <div className="text-sm font-semibold">{meta.label}</div>
                    <div className="text-[11px] text-muted-foreground">Evidence trail · Memory layer</div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSource(null)}
                  className="flex size-7 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground">
                  <X className="size-4" />
                </button>
              </div>

              {source.record ? <StructuredSource record={source.record} /> : <>
                {type === "deck" && <DeckSlide citation={source.citation} opp={source.opp} />}
                {type === "github" && <GithubCard opp={source.opp} />}
                {type === "interview" && <InterviewCard citation={source.citation} />}
                {type === "news" && <NewsCard source={source} />}
                {(type === "launch" || type === "paper" || type === "person" || type === "generic") && (
                  <GenericCard citation={source.citation} />
                )}
              </>}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </SourceContext.Provider>
  )
}
