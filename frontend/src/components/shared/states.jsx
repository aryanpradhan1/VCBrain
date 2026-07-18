import { CircleAlert, RotateCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Compact inline error banner — plain language, never a stack trace.
export function ErrorBanner({ message = "Something went wrong loading this panel.", onRetry, className }) {
  return (
    <div
      role="alert"
      className={cn(
        "flex items-center gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800",
        className
      )}>
      <CircleAlert className="size-4 shrink-0" />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <Button variant="ghost" size="xs" onClick={onRetry} className="text-amber-800 hover:bg-amber-100">
          <RotateCw data-icon="inline-start" />
          Retry
        </Button>
      )}
    </div>
  )
}

// One line of copy, no illustration.
export function EmptyState({ children, className }) {
  return (
    <div className={cn("py-12 text-center text-sm text-muted-foreground", className)}>
      {children}
    </div>
  )
}
