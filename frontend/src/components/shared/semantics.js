// One semantic color system, used identically on every screen.
// green = bullish / high confidence / improving · gray = neutral / stable
// amber = medium / cold start · red = bear / low / declining

export const trendMeta = {
  improving: { label: "improving", cls: "text-emerald-600" },
  stable: { label: "stable", cls: "text-slate-400" },
  declining: { label: "declining", cls: "text-red-500" },
}

export const ratingMeta = {
  bullish: { label: "Bullish", variant: "positive", dot: "bg-emerald-500" },
  neutral: { label: "Neutral", variant: "neutral", dot: "bg-slate-300" },
  bear: { label: "Bear", variant: "negative", dot: "bg-red-500" },
}

export const confidenceMeta = {
  high: { label: "High confidence", variant: "positive" },
  medium: { label: "Medium confidence", variant: "caution" },
  low: { label: "Low confidence", variant: "negative" },
}

// Founder axis is a 0–100 score, not a rating — map it onto the same dot colors.
export const scoreDot = (score) =>
  score >= 70 ? "bg-emerald-500" : score >= 50 ? "bg-slate-300" : "bg-red-500"

export const verdictMeta = {
  approve: { label: "Approve", variant: "positive" },
  review: { label: "Review", variant: "caution" },
  decline: { label: "Decline", variant: "negative" },
}

export const fmtAmount = (n) =>
  n >= 1000 ? `$${Math.round(n / 1000)}K` : `$${n}`
