import { FlaskConical, GitBranch, Rocket, TrendingUp } from "lucide-react"
import { FaGithub } from "react-icons/fa6"

import { cn } from "@/lib/utils"

// Public-signal chips rendered from the Signal Intake contract shape.
// Zero-signal chips render muted — honesty about thin data is a feature.
function Chip({ icon: Icon, label, active, title }) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium tabular-nums transition-colors",
        active
          ? "border-slate-200 bg-card text-foreground/80 hover:border-slate-300"
          : "border-transparent bg-secondary/60 text-muted-foreground/50"
      )}>
      <Icon className="size-3" strokeWidth={2.2} />
      {label}
    </span>
  )
}

export function SignalChips({ signals, className }) {
  if (!signals) return null
  const { github, devpost_hn, arxiv } = signals
  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
      <Chip
        icon={GitBranch}
        active={github?.repos > 0}
        label={github?.repos > 0 ? `${github.repos} repos · ${github.longevity_months}mo` : "no GitHub"}
        title={
          github?.repos > 0
            ? `GitHub: ${github.repos} repos, ${Math.round(github.commit_consistency_score * 100)}% commit consistency, ${github.longevity_months} months`
            : "No GitHub footprint found"
        }
      />
      {github?.repos > 0 && (
        <Chip
          icon={TrendingUp}
          active={github.commit_consistency_score >= 0.6}
          label={`${Math.round(github.commit_consistency_score * 100)}% consistency`}
          title={`Commit consistency score: ${github.commit_consistency_score}`}
        />
      )}
      <Chip
        icon={Rocket}
        active={devpost_hn?.launches > 0}
        label={
          devpost_hn?.launches > 0
            ? `${devpost_hn.launches} launches · ▲${devpost_hn.total_upvotes}`
            : "no launches"
        }
        title={
          devpost_hn?.launches > 0
            ? `Devpost/HN: ${devpost_hn.launches} launches, ${devpost_hn.total_upvotes} total upvotes`
            : "No Devpost/Hacker News footprint found"
        }
      />
      <Chip
        icon={FlaskConical}
        active={arxiv?.papers > 0}
        label={arxiv?.papers > 0 ? `${arxiv.papers} ${arxiv.papers === 1 ? "paper" : "papers"}` : "no papers"}
        title={arxiv?.papers > 0 ? `arXiv: ${arxiv.papers} publications` : "No arXiv publications found"}
      />
    </div>
  )
}

// Compact dashboard treatment: icon + one useful number, with the complete
// evidence summary in a native tooltip. The memo keeps the expanded version.
function CompactSignal({ icon: Icon, value, active, title, iconClassName }) {
  return (
    <span
      title={title}
      aria-label={title}
      className={cn(
        "inline-flex h-7 items-center gap-1.5 rounded-md border px-2 text-[11px] font-semibold tabular-nums",
        active ? "border-border bg-white text-slate-700" : "border-transparent bg-secondary/70 text-muted-foreground/50"
      )}>
      <Icon className={cn("size-3.5", iconClassName)} />
      <span>{value}</span>
    </span>
  )
}

export function SignalIcons({ signals, className }) {
  if (!signals) return null
  const { github, devpost_hn, arxiv } = signals
  const githubActive = github?.repos > 0
  const launchesActive = devpost_hn?.launches > 0
  const papersActive = arxiv?.papers > 0

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <CompactSignal
        icon={FaGithub}
        value={githubActive ? github.repos : "–"}
        active={githubActive}
        title={githubActive ? `GitHub · ${github.repos} repositories · ${Math.round(github.commit_consistency_score * 100)}% commit consistency · ${github.longevity_months} months` : "No GitHub footprint found"}
      />
      <CompactSignal
        icon={Rocket}
        value={launchesActive ? devpost_hn.launches : "–"}
        active={launchesActive}
        title={launchesActive ? `Launches · ${devpost_hn.launches} Devpost/HN launches · ${devpost_hn.total_upvotes} total upvotes` : "No Devpost or Hacker News launches found"}
      />
      <CompactSignal
        icon={FlaskConical}
        value={papersActive ? arxiv.papers : "–"}
        active={papersActive}
        title={papersActive ? `Research · ${arxiv.papers} arXiv ${arxiv.papers === 1 ? "paper" : "papers"}` : "No arXiv publications found"}
      />
    </div>
  )
}
