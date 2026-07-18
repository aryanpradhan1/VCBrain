import { useState } from "react"
import { ChevronDown } from "lucide-react"

// Section header used across the startup page: icon + title + right-side context chip.
export function Section({ icon: Icon, title, sub, right, children, className }) {
  return (
    <section className={className}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {Icon && (
            <span className="flex size-6 items-center justify-center rounded-md bg-secondary text-muted-foreground">
              <Icon className="size-3.5" strokeWidth={2.2} />
            </span>
          )}
          <div className="leading-tight">
            <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
            {sub && <div className="text-[11px] text-muted-foreground">{sub}</div>}
          </div>
        </div>
        {right}
      </div>
      {children}
    </section>
  )
}

// Clamp long text with a "Read more" toggle — simplify, keep the depth reachable.
export function Expandable({ children, lines = 3, className }) {
  const [open, setOpen] = useState(false)
  const clamp = open
    ? undefined
    : { display: "-webkit-box", WebkitLineClamp: lines, WebkitBoxOrient: "vertical", overflow: "hidden" }
  return (
    <div className={className}>
      <div style={clamp}>{children}</div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="mt-1 inline-flex items-center gap-0.5 text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground">
        {open ? "Show less" : "Read more"}
        <ChevronDown className={`size-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
    </div>
  )
}
