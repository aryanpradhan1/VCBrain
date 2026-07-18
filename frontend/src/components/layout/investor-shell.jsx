import { NavLink, Outlet } from "react-router-dom"
import { motion } from "motion/react"

import { cn } from "@/lib/utils"

const tabs = [
  { to: "/", label: "Pipeline", end: true },
  { to: "/thesis", label: "Thesis" },
]

export function InvestorShell() {
  return (
    <div className="min-h-dvh">
      <header className="glass sticky top-0 z-40 border-b border-black/5">
        <div className="mx-auto flex h-14 max-w-5xl items-center gap-8 px-5">
          <NavLink to="/" className="flex items-center gap-2">
            <span className="flex size-6 items-center justify-center rounded-lg bg-primary text-[11px] font-bold text-primary-foreground">
              F
            </span>
            <span className="text-sm font-semibold tracking-tight">FounderScore</span>
          </NavLink>

          <nav className="flex items-center gap-1">
            {tabs.map((t) => (
              <NavLink key={t.to} to={t.to} end={t.end} className="relative rounded-full px-3 py-1.5 text-sm">
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="nav-pill"
                        transition={{ type: "spring", stiffness: 500, damping: 35 }}
                        className="absolute inset-0 rounded-full bg-secondary"
                      />
                    )}
                    <span
                      className={cn(
                        "relative font-medium",
                        isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                      )}>
                      {t.label}
                    </span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <span className="ml-auto text-xs text-muted-foreground">Fund workspace</span>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-8">
        <Outlet />
      </div>
    </div>
  )
}
