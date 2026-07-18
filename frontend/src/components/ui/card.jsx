import { cn } from "@/lib/utils"

function Card({ className, ...props }) {
  return (
    <div
      data-slot="card"
      className={cn(
        "flex flex-col gap-5 rounded-xl border border-border bg-card py-5 text-card-foreground shadow-[0_1px_2px_rgb(15_23_42/0.025)]",
        className
      )}
      {...props} />
  );
}

function CardHeader({ className, ...props }) {
  return (
    <div
      data-slot="card-header"
      className={cn("flex flex-col gap-1 px-5", className)}
      {...props} />
  );
}

function CardTitle({ className, ...props }) {
  return (
    <div
      data-slot="card-title"
      className={cn("text-sm font-semibold tracking-tight", className)}
      {...props} />
  );
}

function CardDescription({ className, ...props }) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props} />
  );
}

function CardContent({ className, ...props }) {
  return (
    <div
      data-slot="card-content"
      className={cn("px-5", className)}
      {...props} />
  );
}

function CardFooter({ className, ...props }) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex items-center px-5", className)}
      {...props} />
  );
}

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter }
