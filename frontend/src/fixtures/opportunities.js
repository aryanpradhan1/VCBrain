// Fixtures for the three archetypes (strong / cold-start / weak).
// Shapes match /shared/contract.md → "Frontend-consumption shape" exactly — never rename a field.
// These belong in /shared/fixtures/ per the contract; they live here until the next sync point
// because /shared/ is outside frontend's folder ownership.
//
// SYNC-POINT FLAG: `public_signals` uses the exact field names from the Signal Intake
// output contract, but the frontend-consumption shape doesn't list it yet — B's glue
// needs to pass it through. Raise at next sync; the dashboard renders signal chips from it.

export const opportunities = [
  {
    founder_id: "f-001",
    company_id: "c-001",
    company_name: "Relay Robotics",
    sourcing_channel: "inbound",
    cold_start_flag: false,
    public_signals: {
      github: { repos: 12, commit_consistency_score: 0.9, longevity_months: 18 },
      devpost_hn: { launches: 2, total_upvotes: 340 },
      arxiv: { papers: 3 },
    },
    founder_score: { value: 84, confidence_interval: 6, trend: "improving" },
    founder_axis: {
      score: 88,
      trend: "improving",
      rationale:
        "Second-time founder; previous devtools company acquired in 2024. 18 months of sustained commit activity across 12 public repos, and shipped three hardware revisions in nine months with a team of four.",
      citations: [
        "GitHub: 12 repos, commit consistency 0.9, 18-month longevity",
        "Deck slide 3: prior exit to Zebra Technologies (2024)",
        "Devpost: 2 launches, 340 upvotes",
      ],
    },
    market_axis: {
      rating: "bullish",
      trend: "stable",
      rationale:
        "Warehouse automation labor gap is structural, not cyclical; mid-market 3PLs remain underserved by incumbents priced for enterprise.",
      citations: [
        "Deck slide 5: $23B SAM, third-party sourced",
        "Claimed 14 signed LOIs from mid-market 3PLs (verified 11 in diligence)",
      ],
    },
    idea_vs_market_axis: {
      rating: "bullish",
      trend: "improving",
      rationale:
        "Retrofit-first approach sidesteps the capex objection that stalls competitors; unit economics already positive on pilot deployments.",
      citations: [
        "Deck slide 7: pilot gross margin 41%",
        "Interview: pricing model updated after customer pushback — responsive iteration",
      ],
    },
    claim_trust: [
      {
        claim: "traction",
        confidence: "high",
        evidence:
          "Claimed $38K MRR; Stripe-verified screenshot plus two customer references confirmed independently.",
      },
      {
        claim: "team",
        confidence: "high",
        evidence:
          "Prior exit verified via press coverage and LinkedIn cross-reference; CTO's robotics publications confirmed on arXiv.",
      },
      {
        claim: "market_size",
        confidence: "medium",
        evidence:
          "$23B SAM cites a credible analyst report, but assumes full mid-market penetration; bottom-up estimate lands nearer $9B.",
      },
      {
        claim: "ask",
        confidence: "high",
        evidence: "$100K at consistent terms across deck and interview; no contradictions.",
      },
    ],
    memo: {
      required: {
        company_snapshot:
          "Retrofit autonomy kits that turn existing warehouse forklifts into self-driving units, sold as a subscription to mid-market 3PLs.",
        investment_hypotheses: [
          "Retrofit beats new-build robotics on payback period (<8 months vs 3+ years), which is the deciding variable for mid-market buyers.",
          "A second-time founder with a hardware exit can recruit the scarce talent this category needs.",
          "Subscription pricing turns a capex sale into an opex line, collapsing the 9-month enterprise sales cycle.",
        ],
        swot: {
          strengths: ["Proven founder-market fit", "Positive pilot unit economics", "11 verified LOIs"],
          weaknesses: ["Four-person team for a hardware+software surface", "Single supplier for lidar module"],
          opportunities: ["Mid-market 3PL segment ignored by incumbents", "Labor shortage tailwind"],
          threats: ["Incumbents could price down into mid-market", "Hardware margin compression"],
        },
        problem_and_product:
          "Warehouses can't hire forklift operators fast enough, and full robotic replacements cost $250K+ per unit. Relay's kit converts an existing forklift for $1.2K/month, installed in a day, no floor changes.",
        traction_kpis:
          "$38K MRR (verified), 6 paying pilots, 11 verified LOIs, net revenue retention 128% across pilot cohort.",
      },
      optional_or_flagged: {
        team_and_history:
          "CEO Maya Okonkwo (2nd-time founder, prior exit), CTO Daniel Reyes (ex-Boston Dynamics, 3 arXiv publications), 2 founding engineers.",
        cap_table: "Not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "Top-down market size is likely 2.5x inflated; bullish case must survive on the $9B bottom-up figure.",
        "Lidar single-supplier dependency is unpriced risk if the vendor is acquired.",
      ],
    },
    portfolio_check: {
      overlap: false,
      note: "No existing portfolio exposure to warehouse automation or logistics robotics.",
    },
    verdict: "approve",
    amount_recommended: 100000,
  },

  {
    founder_id: "f-002",
    company_id: "c-002",
    company_name: "Cove Health",
    sourcing_channel: "outbound",
    cold_start_flag: true,
    public_signals: {
      github: { repos: 1, commit_consistency_score: 0.8, longevity_months: 14 },
      devpost_hn: { launches: 0, total_upvotes: 0 },
      arxiv: { papers: 0 },
    },
    founder_score: { value: 38, confidence_interval: 24, trend: "stable" },
    founder_axis: {
      score: 46,
      trend: "stable",
      rationale:
        "Public data is thin: no prior companies, no press, a single active repo. What exists is promising — the repo shows 14 months of steady solo commits on a clinical-notes parser — but one signal cannot anchor a confident read.",
      citations: [
        "GitHub: 1 repo, commit consistency 0.8, 14-month longevity",
        "No Devpost/HN footprint; no prior funding record found",
      ],
    },
    market_axis: {
      rating: "neutral",
      trend: "stable",
      rationale:
        "Prior-auth automation is a real and painful wedge, but the deck's market framing is secondhand and we have no independent signal on this founder's access to health-system buyers. Thin public data limits conviction either way.",
      citations: ["Deck slide 4: market claim sourced from a 2024 CAQH index report"],
    },
    idea_vs_market_axis: {
      rating: "neutral",
      trend: "stable",
      rationale:
        "The product thesis (LLM-drafted prior-auth packets reviewed by nurses) is plausible and timely, but pre-revenue with no pilot letters; nothing yet distinguishes it from a dozen similar seed-stage entrants.",
      citations: ["Deck slide 6: workflow diagram; no customer evidence attached"],
    },
    claim_trust: [
      {
        claim: "traction",
        confidence: "low",
        evidence:
          "Deck claims '3 health systems in conversation'; no names, no letters, not independently verifiable.",
      },
      {
        claim: "team",
        confidence: "medium",
        evidence:
          "Solo founder; RN license verified against state registry. Clinical background is credible, technical depth partially evidenced by repo quality.",
      },
      {
        claim: "market_size",
        confidence: "low",
        evidence: "Single secondhand citation; no bottom-up model provided.",
      },
    ],
    memo: {
      required: {
        company_snapshot:
          "Pre-revenue tool that drafts prior-authorization packets from EHR notes for nurse review, founded by a practicing RN who taught herself to code.",
        investment_hypotheses: [
          "A clinician-founder can win nurse trust that pure-tech entrants in this category consistently fail to earn.",
          "Prior-auth is a wedge into broader clinical-documentation automation.",
        ],
        swot: {
          strengths: ["Authentic founder-problem fit", "14 months of consistent solo execution"],
          weaknesses: ["Solo, non-traditional founder with no network into buyers", "Pre-revenue, no pilots"],
          opportunities: ["CMS rule changes forcing prior-auth turnaround times from 2026"],
          threats: ["Well-funded competitors (Cohere Health, Latent) moving down-market"],
        },
        problem_and_product:
          "Prior authorizations consume 13 nurse-hours per week per clinic. Cove drafts the packet from the chart automatically; a nurse reviews and submits in minutes instead of hours.",
        traction_kpis:
          "Pre-revenue. Working prototype demoed live in interview; 3 claimed (unverified) health-system conversations.",
      },
      optional_or_flagged: {
        team_and_history: "Solo founder: Priya Nair, RN — 8 years clinical, self-taught engineer.",
        cap_table: "Not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "Cold start: the wide interval means this score is closer to a hypothesis than a measurement — the interview is doing most of the work.",
        "Solo clinical founder must hire engineering senior to her own level; no evidence yet she can.",
      ],
    },
    portfolio_check: {
      overlap: false,
      note: "No portfolio exposure to healthcare workflow automation.",
    },
    verdict: "review",
    amount_recommended: 100000,
  },

  {
    founder_id: "f-003",
    company_id: "c-003",
    company_name: "Snapcart AI",
    sourcing_channel: "inbound",
    cold_start_flag: false,
    public_signals: {
      github: { repos: 9, commit_consistency_score: 0.3, longevity_months: 26 },
      devpost_hn: { launches: 3, total_upvotes: 85 },
      arxiv: { papers: 0 },
    },
    founder_score: { value: 44, confidence_interval: 9, trend: "declining" },
    founder_axis: {
      score: 51,
      trend: "stable",
      rationale:
        "Capable generalist with two prior startups that quietly wound down inside 18 months each. GitHub activity is bursty — intense weeks followed by month-long gaps — a pattern consistent with the serial-pivot history.",
      citations: [
        "GitHub: 9 repos, commit consistency 0.3, 26-month longevity",
        "Crunchbase: two prior ventures, both inactive",
      ],
    },
    market_axis: {
      rating: "neutral",
      trend: "stable",
      rationale:
        "E-commerce personalization spend is real but consolidated; buyers default to platform-native tools (Shopify, Klaviyo) unless a startup shows a step-change result.",
      citations: ["Deck slide 5: market figures check out against public sources"],
    },
    idea_vs_market_axis: {
      rating: "bear",
      trend: "declining",
      rationale:
        "'AI-powered product recommendations' is a feature the platforms ship natively and give away. No proprietary data, no distribution wedge, and the demo's results were indistinguishable from Shopify's built-in.",
      citations: [
        "Deck slide 7 claims 31% AOV lift; methodology footnote reveals n=1 store, 2-week window",
        "Interview: could not articulate a defensible data advantage when pressed",
      ],
    },
    claim_trust: [
      {
        claim: "traction",
        confidence: "low",
        evidence:
          "Claimed '40 stores on waitlist' — the linked waitlist form was created 9 days before the deck; no store names verifiable. Contradicts interview statement of '15 or so signups'.",
      },
      {
        claim: "market_size",
        confidence: "high",
        evidence: "Market figures accurately cite public Shopify/Klaviyo filings.",
      },
      {
        claim: "team",
        confidence: "medium",
        evidence:
          "Employment history verifies, but deck omits both prior shutdowns; surfaced via Crunchbase cross-reference.",
      },
    ],
    memo: {
      required: {
        company_snapshot:
          "Shopify app applying LLM re-ranking to product recommendation carousels for small e-commerce stores.",
        investment_hypotheses: [
          "Only viable if the claimed 31% AOV lift replicates across a real cohort — currently unsupported at n=1.",
        ],
        swot: {
          strengths: ["Fast shipper; polished demo built in six weeks"],
          weaknesses: ["No proprietary data", "Undisclosed prior shutdowns", "Contradictory traction claims"],
          opportunities: ["SMB stores underserved by enterprise personalization vendors"],
          threats: ["Shopify ships this natively for free", "Zero switching costs for buyers"],
        },
        problem_and_product:
          "Small stores lack the data teams to tune recommendations. Snapcart re-ranks carousels via API using an LLM over product metadata and clickstream.",
        traction_kpis:
          "1 pilot store (founder's friend), claimed 31% AOV lift over a 2-week window, unverified waitlist.",
      },
      optional_or_flagged: {
        team_and_history:
          "Flagged: two prior ventures wound down within 18 months each; neither disclosed in the deck.",
        cap_table: "Not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "The traction story contradicts itself between deck and interview — the waitlist claim did not survive basic verification.",
        "Platform risk is existential: Shopify's native feature is free and improving.",
        "Pattern of undisclosed shutdowns raises a candor question, not just a track-record one.",
      ],
    },
    portfolio_check: {
      overlap: true,
      note: "Overlaps with existing portfolio company Cartel (e-commerce personalization, 2025 check).",
    },
    verdict: "decline",
    amount_recommended: 0,
  },
]

// GET /founders/:id/results — the founder-facing shape. Nothing else, ever.
export const founderResults = {
  "f-001": {
    founder_score: { value: 84, confidence_interval: 6, trend: "improving" },
    narrative:
      "Your track record and verified pilot revenue are strong, independent signals — your score is high and our confidence in it is tight. Your market-size framing is the one area where our numbers diverged from yours.",
  },
  "f-002": {
    founder_score: { value: 38, confidence_interval: 24, trend: "stable" },
    narrative:
      "Your 14 months of consistent building show real execution, but there's very little public signal about you yet, so this score carries wide uncertainty. Completing the interview and verifying your health-system conversations would sharpen it quickly — in either direction.",
  },
  "f-003": {
    founder_score: { value: 44, confidence_interval: 9, trend: "declining" },
    narrative:
      "You ship fast and your market research is accurate. Your score is held back by traction claims we couldn't verify and gaps between your deck and interview answers — consistent, verifiable evidence is the fastest way to move it.",
  },
}

// One-line pitch for dashboard rows, derived from memo.required.company_snapshot.
export const pitchOf = (opp) => opp.memo.required.company_snapshot
