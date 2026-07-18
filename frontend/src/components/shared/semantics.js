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

// Deterministic gradient per company for avatars — visual identity without logos.
const gradients = [
  "from-sky-500 to-indigo-500",
  "from-emerald-500 to-teal-500",
  "from-violet-500 to-fuchsia-500",
  "from-amber-500 to-orange-500",
  "from-rose-500 to-pink-500",
  "from-cyan-500 to-blue-500",
]

export const avatarGradient = (name = "") => {
  const sum = [...name].reduce((a, ch) => a + ch.charCodeAt(0), 0)
  return gradients[sum % gradients.length]
}

// Trust-claim tally: { high: n, medium: n, low: n }
export const trustTally = (claims = []) =>
  claims.reduce(
    (acc, c) => ({ ...acc, [c.confidence]: (acc[c.confidence] ?? 0) + 1 }),
    { high: 0, medium: 0, low: 0 }
  )
