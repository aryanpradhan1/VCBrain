# Frontend — Role Rules (D)

@shared/contract.md

You are building the entire frontend for FounderScore — investor dashboard, memo view, adversarial view, thesis config, interview live view, founder results page. This is your only responsibility this build; no agent-building duties. Only modify files inside `/frontend/`. Call the backend only via the documented shapes in `/shared/contract.md` — never invent a field name.

Stack: React + Vite + Tailwind + shadcn/ui. Use shadcn primitives (Card, Table, Badge, Button, Tabs, Skeleton) almost as-is — their default light theme is the right starting point, don't fight it.

Build against `/shared/fixtures/` (the three archetypes: strong, cold-start, weak) from minute one. Don't wait on A/B/C's real endpoints — the whole point of the locked contract is that swapping mock for real is a no-op later.

## Design direction — light, clean, Notion-level approachable

Overriding the "Bloomberg dark terminal" note some versions of this spec floated — going light. White/near-white surfaces, generous whitespace, shadcn's default rounded corners and subtle card elevation, normal sans-serif throughout (no forced monospace). This should feel like a well-designed modern SaaS tool a non-technical investor is comfortable in, not a trading terminal.

- **Background**: white / very light gray (`bg-white`, `bg-slate-50` for page background behind cards).
- **Cards**: white background, subtle border (`border-slate-200`), `rounded-xl`, light shadow is fine.
- **Color is functional**: green = bullish / high confidence / improving. Gray/muted = neutral / stable / no data yet. Amber = medium confidence / cold start / caution. Red = bear / declining / decline. Use the light tint + dark text pairing for chips (e.g. `bg-green-50 text-green-700`), not solid fills.
- **Trend indicators**: a small up/down/flat arrow icon next to the number, colored per the status rule above. Sparklines are a nice-to-have if time allows in the polish hour, never a requirement — don't burn build time on them.
- **Numbers**: normal weight, slightly bolder (font-medium) than surrounding text so scores stand out; `tabular-nums` is a nice cheap touch for alignment in lists, not required.
- **Density**: comfortable, not cramped — generous padding (`p-4`–`p-6` territory), clear separation between rows/cards. This is closer to a well-designed dashboard than a data table.

## The rule that governs every screen: asymmetric disclosure

Founders see their Founder Score (value, confidence interval, trend) and a short plain-language narrative. **Nothing else, ever** — not the 3-axis scores, not SWOT, not competitive analysis, not the memo. That's the fund's confidential work product. If you're ever unsure whether something belongs on the founder page, the answer is no.

Investors see everything: 3-axis scores with citations, per-claim Trust Score with evidence, a separate adversarial box, a portfolio check, the full memo, and the decision controls.

## Required screens (all 8, per the brief)

**1. Investor dashboard** — ranked applicant list. Each row: avatar/initial, company name, one-line pitch (truncated), a sourcing-channel tag (inbound/outbound), three small status-colored dots for Founder/Market/Idea-vs-Market (never a single averaged badge), Founder Score with its trend arrow, confidence interval shown small next to it. One reusable row component serves inbound and outbound-converged applicants alike. A natural-language search bar at the top is a nice addition once the list itself works.

**2. Memo view** (click into an applicant) — full Appendix 1 structure (`required` fully populated, `optional_or_flagged` sections shown filled-or-flagged, never silently omitted), Founder Score header, the three axis cards (score/rating + trend + citation text, equal width, never merged into one number), per-claim Trust Score list (claim + evidence + confidence chip).

**3. Adversarial view** — its own visually distinct panel, not a section within the memo — e.g. an amber-tinted callout box. Renders `adversarial_view.challenges`.

**4. Portfolio check indicator** — a single compact status line/badge: overlap true/false + `note`, with a check or flag icon.

**5. Thesis Engine configuration screen** — sectors, stage, geography, check size, ownership targets, risk appetite. A short wizard or a single clean settings form — configurable, never hardcoded.

**6. Interview Agent live-session view** — the founder-facing live interview: a simple chat thread, message bubbles, no avatar gimmicks. 4–5 adaptive questions. This is the founder's side of the Interview Agent; the resulting `response_pattern` and `resilience_score` feed back into their Founder Score but are never displayed to them directly — only the composite score and narrative are.

**7. Founder results page** — separate, much simpler, read-only. Founder Score + confidence interval + trend + the narrative sentence. That's the entire page:

```
Your founder score
68 ± 15   ↑ improving

Your GitHub activity and hackathon win show strong technical
execution. We don't yet have independent signals about traction
or market fit beyond your deck.

[ Start interview ]
```

**8. Loading, error, and empty states for every panel** — shadcn's `Skeleton` (default light) for loading. Errors: a compact inline banner, amber/red tint, plain-language message, never a raw stack trace. Empty states: one line of copy, no illustration needed.

## Shared components — build once, reuse everywhere

- **Score badge**: `value ± interval` + trend arrow (green up / red down / gray flat). Identical on dashboard rows, founder results page, and memo header.
- **Axis pill/card**: same three-color semantic mapping (green=bullish, gray=neutral, red=bear) everywhere a judgment appears.
- **Confidence chip**: high/medium/low, same three colors as axis ratings, same component on the memo and the trust score list.
- **Cold-start badge**: same amber tag, same reasoning copy, every time `cold_start_flag: true` fires — never customized per screen.
- **Decision buttons**: Approve (green outline) / Review (neutral) / Decline (red outline), always shown together with `amount_recommended` alongside, never hidden in a label.

## Your build blocks (of the ~10.5h core build)

- **3:30–3:50 (Kickoff)**: confirm the shared skeleton boots (`npm run dev` loads a blank page, no errors), then lock the design system — Tailwind theme tokens and the shared components above — before building any real screen.
- **3:50–6:00 (Block 1)**: dashboard layout against fixtures, design system fully locked.
- **6:20–8:30 (Block 2)**: wire dashboard to real (not mocked) data as B's API comes online; build the memo view.
- **8:50–11:00 (Block 3)**: Interview Agent live-session view, adversarial view, portfolio check, founder results page.
- **11:20–1:00 (Block 4)**: end-to-end integration testing against all three fixture archetypes, including the cold-start path explicitly.
- **1:00–2:00 (feature freeze)**: this hour is yours for a final visual polish pass, and nothing else — per the cut list, dashboard polish is the *last* thing to cut, not the first, given this is explicitly 15% of the judged score.

## Never do this

- Never average the three axes into a single number or badge.
- Never show tri-axis/SWOT/competitive detail on the founder-facing page.
- Never fabricate a missing memo field — render the exact flagged string (e.g. "Cap table: not disclosed").
- Never let the founder-facing theme drift from the investor theme — one light system, simpler layout only on that one page.
- Never invent a field name not in `/shared/contract.md` — if something's missing, flag it at the next sync point instead of guessing.