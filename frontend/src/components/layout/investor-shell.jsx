import { NavLink, Outlet } from "react-router-dom"
import { motion } from "motion/react"
import {
  Crosshair,
  FilePlus2,
  Gauge,
  Inbox,
  Radar,
  Settings,
  Sparkles,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { opportunities } from "@/fixtures/opportunities"

const investorNav = [
  { to: "/", label: "Pipeline", icon: Inbox, end: true, count: opportunities.length },
  { to: "/?channel=outbound", label: "Sourcing radar", icon: Radar, end: false },
  { to: "/thesis", label: "Thesis Engine", icon: Crosshair },
]

const founderNav = [
  { to: "/apply", label: "Apply", icon: FilePlus2 },
  { to: "/founder/f002", label: "Founder portal", icon: Gauge },
]

function Item({ to, label, icon: Icon, end, count }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
          isActive
            ? "text-foreground"
            : "text-muted-foreground hover:bg-black/4 hover:text-foreground"
        )
      }>
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.span
              layoutId="side-pill"
              transition={{ type: "spring", stiffness: 500, damping: 38 }}
              className="absolute inset-0 rounded-lg bg-card card-hairline"
            />
          )}
          <Icon className="relative size-4 shrink-0" strokeWidth={2} />
          <span className="relative flex-1">{label}</span>
          {count != null && (
            <span className="relative rounded-full bg-secondary px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-secondary-foreground">
              {count}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

function SectionLabel({ children }) {
  return (
    <div className="px-2.5 pt-5 pb-1.5 text-[10px] font-semibold tracking-[0.08em] text-muted-foreground/70 uppercase">
      {children}
    </div>
  )
}

export function InvestorShell() {
  return (
    <div className="min-h-dvh">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[236px] flex-col border-r border-border bg-[#fbfcfd] px-3 py-4 lg:flex">
        <NavLink to="/" className="flex items-center gap-2.5 px-2.5 pb-2">
          <span className="flex size-7 items-center justify-center rounded-md bg-slate-900 text-xs font-bold text-white">
            F
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight">FounderScore</div>
            <div className="text-[10px] text-muted-foreground">The VC Brain</div>
          </div>
        </NavLink>

        <SectionLabel>Invest</SectionLabel>
        <nav className="space-y-0.5">
          {investorNav.map((item) => (
            <Item key={item.label} {...item} />
          ))}
        </nav>

        <SectionLabel>Founder side · demo</SectionLabel>
        <nav className="space-y-0.5">
          {founderNav.map((item) => (
            <Item key={item.label} {...item} />
          ))}
        </nav>

        <div className="mt-auto space-y-3">
          <div className="rounded-lg border border-border bg-white p-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold">
              <Sparkles className="size-3.5 text-amber-500" />
              24-hour decisions
            </div>
            <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
              Sourcing → screening → diligence → $100K decision, same day.
            </p>
          </div>
          <div className="flex items-center gap-2.5 px-2.5">
            <span className="flex size-7 items-center justify-center rounded-full bg-slate-800 text-[10px] font-bold text-white">
              MG
            </span>
            <div className="flex-1 leading-tight">
              <div className="text-xs font-semibold">Maschmeyer Group</div>
              <div className="text-[10px] text-muted-foreground">Fund workspace</div>
            </div>
            <Settings className="size-4 text-muted-foreground/60" />
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-40 flex h-13 items-center gap-2.5 border-b border-border bg-background/95 px-4 backdrop-blur lg:hidden">
        <span className="flex size-6 items-center justify-center rounded-md bg-slate-900 text-[11px] font-bold text-white">
          F
        </span>
        <span className="text-sm font-semibold tracking-tight">FounderScore</span>
        <nav className="ml-auto flex items-center gap-1 text-sm">
          <NavLink to="/" end className="rounded-full px-2.5 py-1 font-medium text-muted-foreground aria-[current=page]:bg-secondary aria-[current=page]:text-foreground">
            Pipeline
          </NavLink>
          <NavLink to="/thesis" className="rounded-full px-2.5 py-1 font-medium text-muted-foreground aria-[current=page]:bg-secondary aria-[current=page]:text-foreground">
            Thesis
          </NavLink>
        </nav>
      </header>

      <div className="shell-content lg:pl-[236px]">
        <div className="shell-page mx-auto max-w-[1200px] px-5 py-8 lg:px-10">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
