// Fixtures for six startups spanning the three contract archetypes (strong / cold-start / weak)
// plus three in-between cases so the dashboard reads like a real pipeline.
//
// Contract fields match /shared/contract.md exactly — never rename.
// SYNC-POINT FLAGS (proposed contract additions, exact shapes below — B's glue passes through):
//   1. `public_signals` — exact Signal Intake output field names
//   2. `thesis` — exact Thesis Engine output shape
//   3. `enrichment` — frontend-driven addition: founder profiles, one-liners, market sizing,
//      news, and the per-agent trace that powers the pipeline visual.

export const opportunities = [
  // ── 1. STRONG ────────────────────────────────────────────────────────────
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
    thesis: {
      thesis_match: true,
      match_type: "exact",
      rationale: "Robotics · Pre-seed · North America — inside the fund's stated sectors and stage.",
    },
    founder_score: { value: 84, confidence_interval: 6, trend: "improving" },
    founder_axis: {
      score: 88,
      trend: "improving",
      rationale:
        "Second-time founder with a 2024 devtools exit. 18 months of sustained commits across 12 repos; shipped three hardware revisions in nine months with a team of four.",
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
        "Warehouse labor gap is structural, not cyclical; mid-market 3PLs remain underserved by incumbents priced for enterprise.",
      citations: [
        "Deck slide 5: $23B SAM, third-party sourced",
        "Diligence: 11 of 14 claimed LOIs independently verified",
      ],
    },
    idea_vs_market_axis: {
      rating: "bullish",
      trend: "improving",
      rationale:
        "Retrofit-first sidesteps the capex objection that stalls competitors; unit economics already positive on pilots.",
      citations: [
        "Deck slide 7: pilot gross margin 41%",
        "Interview: pricing model updated after customer pushback",
      ],
    },
    claim_trust: [
      { claim: "traction", confidence: "high", evidence: "Claimed $38K MRR — Stripe-verified screenshot plus two independent customer references." },
      { claim: "team", confidence: "high", evidence: "Prior exit verified via press and LinkedIn; CTO's robotics publications confirmed on arXiv." },
      { claim: "market_size", confidence: "medium", evidence: "$23B SAM cites a credible analyst report but assumes full penetration; bottom-up lands nearer $9B." },
      { claim: "ask", confidence: "high", evidence: "$100K at consistent terms across deck and interview." },
    ],
    memo: {
      required: {
        company_snapshot:
          "Retrofit autonomy kits that turn existing warehouse forklifts into self-driving units, sold as a subscription to mid-market 3PLs.",
        investment_hypotheses: [
          "Retrofit beats new-build robotics on payback (<8 months vs 3+ years) — the deciding variable for mid-market buyers.",
          "A second-time hardware founder can recruit the scarce talent this category needs.",
          "Subscription pricing turns a capex sale into an opex line, collapsing the sales cycle.",
        ],
        swot: {
          strengths: ["Proven founder-market fit", "Positive pilot unit economics", "11 verified LOIs"],
          weaknesses: ["Four-person team for a hardware+software surface", "Single lidar supplier"],
          opportunities: ["Mid-market 3PLs ignored by incumbents", "Labor shortage tailwind"],
          threats: ["Incumbents pricing down into mid-market", "Hardware margin compression"],
        },
        problem_and_product:
          "Warehouses can't hire forklift operators fast enough, and robotic replacements cost $250K+ per unit. Relay's kit converts an existing forklift for $1.2K/month, installed in a day.",
        traction_kpis: "$38K MRR (verified) · 6 paying pilots · 11 verified LOIs · 128% NRR across pilot cohort.",
      },
      optional_or_flagged: {
        team_and_history: "CEO Maya Okonkwo (2nd-time founder, prior exit); CTO Daniel Reyes (ex-Boston Dynamics, 3 arXiv publications); 2 founding engineers.",
        cap_table: "Not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "Top-down market size is likely 2.5x inflated; the bullish case must survive on the $9B bottom-up figure.",
        "Lidar single-supplier dependency is unpriced risk if the vendor is acquired.",
      ],
    },
    portfolio_check: { overlap: false, note: "No exposure to warehouse automation or logistics robotics." },
    verdict: "approve",
    amount_recommended: 100000,
    enrichment: {
      one_liner: "Self-driving retrofit kits for the forklifts warehouses already own.",
      problem: "Warehouses can't hire forklift operators; full robots cost $250K+ per unit.",
      solution: "A $1.2K/month retrofit kit installed in a day — no new hardware, no floor changes.",
      sector: "Robotics",
      stage: "Pre-seed",
      geography: "Austin, US",
      website: "https://relayrobotics.example.com",
      founders: [
        {
          name: "Maya Okonkwo",
          role: "CEO",
          avatar: "https://randomuser.me/api/portraits/women/44.jpg",
          background: "2nd-time founder — sold devtools co. to Zebra Technologies (2024). Ex-Amazon Robotics PM.",
          linkedin: "https://linkedin.com/in/maya-okonkwo",
          github: "https://github.com/mayaok",
          x: "https://x.com/mayaokonkwo",
          ai_read: "Exit verified via press + LinkedIn cross-reference. Recruiting record is the strongest single signal.",
        },
        {
          name: "Daniel Reyes",
          role: "CTO",
          avatar: "https://randomuser.me/api/portraits/men/32.jpg",
          background: "Ex-Boston Dynamics perception engineer, 6 yrs. 3 arXiv publications on warehouse SLAM.",
          linkedin: "https://linkedin.com/in/daniel-reyes-robotics",
          github: "https://github.com/dreyes",
          ai_read: "Publications confirmed on arXiv; commit history matches claimed role (90% consistency).",
        },
      ],
      news: [
        { title: "Relay Robotics retrofits its 100th forklift", source: "TechCrunch", date: "2026-06-12" },
        { title: "The retrofit wave coming for warehouse automation", source: "The Information", date: "2026-05-03" },
      ],
      market: {
        tam: 23, sam: 9, som: 0.4, unit: "$B",
        basis: "TAM: top-down analyst report (deck slide 5). SAM: bottom-up mid-market 3PL count — diligence's lower figure. SOM: 3-yr obtainable at current install rate.",
      },
      pmf: { signal: "strong", note: "6 paying pilots with 128% NRR — usage grows after purchase, the clearest early PMF marker." },
      agent_trace: [
        { agent: "screen", label: "Screen", kind: "rule", summary: "Deck + name present — passed gate", ms: 2 },
        { agent: "intake", label: "Signal Intake", kind: "ai", summary: "14 deck claims extracted · GitHub/Devpost/arXiv pulled", ms: 1240 },
        { agent: "thesis", label: "Thesis Engine", kind: "rule", summary: "Exact match: Robotics · Pre-seed · NA", ms: 6 },
        { agent: "scorer", label: "Multi-Axis Scorer", kind: "ai", summary: "3 axes scored · 7 citations grounded", ms: 4210 },
        { agent: "diligence", label: "Diligence", kind: "ai", summary: "11/14 claims verified · 1 flagged (market size)", ms: 3890 },
        { agent: "memo", label: "Memo Synthesizer", kind: "ai", summary: "Appendix-1 memo + adversarial view assembled", ms: 2050 },
      ],
    },
  },

  // ── 2. COLD-START ────────────────────────────────────────────────────────
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
    thesis: {
      thesis_match: true,
      match_type: "adjacent_llm_judged",
      rationale: "Healthcare workflow automation is adjacent to the fund's AI-infrastructure thesis — LLM judged the clinical-documentation wedge a fit.",
    },
    founder_score: { value: 38, confidence_interval: 24, trend: "stable" },
    founder_axis: {
      score: 46,
      trend: "stable",
      rationale:
        "Public data is thin: no prior companies, no press, one active repo. What exists is promising — 14 months of steady solo commits on a clinical-notes parser — but one signal can't anchor a confident read.",
      citations: [
        "GitHub: 1 repo, commit consistency 0.8, 14-month longevity",
        "No Devpost/HN footprint; no prior funding record found",
      ],
    },
    market_axis: {
      rating: "neutral",
      trend: "stable",
      rationale:
        "Prior-auth automation is a real wedge, but the market framing is secondhand and we have no independent signal on buyer access.",
      citations: ["Deck slide 4: market claim cites a 2024 CAQH index report"],
    },
    idea_vs_market_axis: {
      rating: "neutral",
      trend: "stable",
      rationale:
        "Plausible, timely thesis (LLM-drafted prior-auth packets, nurse-reviewed) — but pre-revenue, no pilot letters, nothing yet distinguishing it from similar seed entrants.",
      citations: ["Deck slide 6: workflow diagram; no customer evidence attached"],
    },
    claim_trust: [
      { claim: "traction", confidence: "low", evidence: "'3 health systems in conversation' — no names, no letters, not verifiable." },
      { claim: "team", confidence: "medium", evidence: "RN license verified against state registry; technical depth partially evidenced by repo quality." },
      { claim: "market_size", confidence: "low", evidence: "Single secondhand citation; no bottom-up model provided." },
    ],
    memo: {
      required: {
        company_snapshot:
          "Pre-revenue tool drafting prior-authorization packets from EHR notes for nurse review, founded by a practicing RN who taught herself to code.",
        investment_hypotheses: [
          "A clinician-founder can win nurse trust that pure-tech entrants consistently fail to earn.",
          "Prior-auth is a wedge into broader clinical-documentation automation.",
        ],
        swot: {
          strengths: ["Authentic founder-problem fit", "14 months of consistent solo execution"],
          weaknesses: ["Solo founder, no network into buyers", "Pre-revenue, no pilots"],
          opportunities: ["CMS rules forcing prior-auth turnaround times from 2026"],
          threats: ["Well-funded competitors moving down-market"],
        },
        problem_and_product:
          "Prior authorizations consume 13 nurse-hours per week per clinic. Cove drafts the packet from the chart; a nurse reviews and submits in minutes.",
        traction_kpis: "Pre-revenue. Working prototype demoed live; 3 claimed (unverified) health-system conversations.",
      },
      optional_or_flagged: {
        team_and_history: "Solo founder: Priya Nair, RN — 8 years clinical, self-taught engineer.",
        cap_table: "Not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "Cold start: the wide interval means this score is closer to a hypothesis than a measurement — the interview does most of the work.",
        "Solo clinical founder must hire engineering senior to her own level; no evidence yet she can.",
      ],
    },
    portfolio_check: { overlap: false, note: "No exposure to healthcare workflow automation." },
    verdict: "review",
    amount_recommended: 100000,
    enrichment: {
      one_liner: "Prior-auth packets drafted from the chart, reviewed by a nurse in minutes.",
      problem: "Prior authorizations eat 13 nurse-hours per clinic per week.",
      solution: "LLM drafts the packet from EHR notes; a nurse reviews and submits.",
      sector: "Health tech",
      stage: "Pre-seed",
      geography: "Columbus, US",
      website: "https://covehealth.example.com",
      founders: [
        {
          name: "Priya Nair",
          role: "Founder (solo)",
          avatar: "https://randomuser.me/api/portraits/women/68.jpg",
          background: "RN, 8 years clinical practice. Self-taught engineer — 14 months building nights and weekends.",
          linkedin: "https://linkedin.com/in/priya-nair-rn",
          github: "https://github.com/priyanair",
          ai_read: "License verified against state registry. Thin public footprint is the risk, not the person — flagged cold-start, routed to interview.",
        },
      ],
      news: [],
      market: {
        tam: 12, sam: 2.1, som: 0.08, unit: "$B",
        basis: "TAM: secondhand (2024 CAQH index, deck slide 4) — low confidence. SAM/SOM: our own rough cut; founder provided no bottom-up model.",
      },
      pmf: { signal: "early", note: "Pre-revenue, no pilots — PMF unproven. Founder-problem fit is real; buyer access is the open question." },
      agent_trace: [
        { agent: "screen", label: "Screen", kind: "rule", summary: "Sourced outbound — GitHub scan surfaced repo", ms: 3 },
        { agent: "intake", label: "Signal Intake", kind: "ai", summary: "8 deck claims · 1 public source found (GitHub only)", ms: 980 },
        { agent: "thesis", label: "Thesis Engine", kind: "ai", summary: "Adjacent match — LLM judged clinical-docs wedge a fit", ms: 1650 },
        { agent: "scorer", label: "Multi-Axis Scorer", kind: "ai", summary: "3 axes scored · cold-start flag widened interval to ±24", ms: 3900 },
        { agent: "diligence", label: "Diligence", kind: "ai", summary: "0/3 traction claims verifiable · gaps written to Memory", ms: 2400 },
        { agent: "memo", label: "Memo Synthesizer", kind: "ai", summary: "Memo assembled · verdict routed to review + interview", ms: 1870 },
      ],
    },
  },

  // ── 3. WEAK ──────────────────────────────────────────────────────────────
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
    thesis: {
      thesis_match: true,
      match_type: "exact",
      rationale: "E-commerce · Pre-seed · North America — inside stated sectors, but see portfolio overlap.",
    },
    founder_score: { value: 44, confidence_interval: 9, trend: "declining" },
    founder_axis: {
      score: 51,
      trend: "stable",
      rationale:
        "Capable generalist with two prior startups that wound down inside 18 months each. GitHub activity is bursty — intense weeks, month-long gaps — consistent with the serial-pivot history.",
      citations: [
        "GitHub: 9 repos, commit consistency 0.3, 26-month longevity",
        "Crunchbase: two prior ventures, both inactive",
      ],
    },
    market_axis: {
      rating: "neutral",
      trend: "stable",
      rationale: "Personalization spend is real but consolidated; buyers default to platform-native tools unless shown a step-change result.",
      citations: ["Deck slide 5: market figures check out against public filings"],
    },
    idea_vs_market_axis: {
      rating: "bear",
      trend: "declining",
      rationale:
        "'AI-powered recommendations' is a feature platforms ship natively, free. No proprietary data, no distribution wedge; demo results indistinguishable from Shopify's built-in.",
      citations: [
        "Deck slide 7: claimed 31% AOV lift — methodology footnote reveals n=1 store, 2-week window",
        "Interview: could not articulate a defensible data advantage",
      ],
    },
    claim_trust: [
      { claim: "traction", confidence: "low", evidence: "'40 stores on waitlist' — form created 9 days before the deck; contradicts interview statement of '15 or so'." },
      { claim: "market_size", confidence: "high", evidence: "Figures accurately cite public Shopify/Klaviyo filings." },
      { claim: "team", confidence: "medium", evidence: "Employment verifies, but deck omits both prior shutdowns — surfaced via Crunchbase." },
    ],
    memo: {
      required: {
        company_snapshot: "Shopify app applying LLM re-ranking to product recommendation carousels for small e-commerce stores.",
        investment_hypotheses: [
          "Only viable if the claimed 31% AOV lift replicates across a real cohort — currently unsupported at n=1.",
        ],
        swot: {
          strengths: ["Fast shipper; polished demo in six weeks"],
          weaknesses: ["No proprietary data", "Undisclosed prior shutdowns", "Contradictory traction claims"],
          opportunities: ["SMB stores underserved by enterprise vendors"],
          threats: ["Shopify ships this natively for free", "Zero switching costs"],
        },
        problem_and_product:
          "Small stores lack data teams to tune recommendations. Snapcart re-ranks carousels via API using an LLM over product metadata and clickstream.",
        traction_kpis: "1 pilot store (founder's friend) · claimed 31% AOV lift over 2 weeks · unverified waitlist.",
      },
      optional_or_flagged: {
        team_and_history: "Flagged: two prior ventures wound down within 18 months each; neither disclosed in the deck.",
        cap_table: "Not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "The traction story contradicts itself between deck and interview — the waitlist claim did not survive verification.",
        "Platform risk is existential: Shopify's native feature is free and improving.",
        "Undisclosed shutdowns raise a candor question, not just a track-record one.",
      ],
    },
    portfolio_check: { overlap: true, note: "Overlaps with portfolio company Cartel (e-commerce personalization, 2025 check)." },
    verdict: "decline",
    amount_recommended: 0,
    enrichment: {
      one_liner: "LLM re-ranked product carousels for small Shopify stores.",
      problem: "Small stores lack data teams to tune product recommendations.",
      solution: "An API that re-ranks carousels with an LLM over product metadata.",
      sector: "E-commerce",
      stage: "Pre-seed",
      geography: "Toronto, CA",
      website: "https://snapcart.example.com",
      founders: [
        {
          name: "Jordan Lee",
          role: "Founder & CEO",
          avatar: "https://randomuser.me/api/portraits/men/75.jpg",
          background: "Generalist builder; two prior startups (2023, 2024), both wound down inside 18 months. Ex-Wayfair growth eng.",
          linkedin: "https://linkedin.com/in/jordanlee-builds",
          github: "https://github.com/jlee-builds",
          x: "https://x.com/jordanleebuilds",
          ai_read: "Employment verifies, but both shutdowns were omitted from the deck — surfaced via Crunchbase cross-reference. Candor flag.",
        },
      ],
      news: [{ title: "Show HN: Snapcart — AI product recs for Shopify", source: "Hacker News", date: "2026-05-28" }],
      market: {
        tam: 8, sam: 1.4, som: 0.03, unit: "$B",
        basis: "TAM/SAM: accurately cited from public Shopify/Klaviyo filings (the one high-confidence claim). SOM: our estimate given zero switching costs.",
      },
      pmf: { signal: "weak", note: "n=1 pilot (founder's friend), 2-week window, results indistinguishable from the platform default." },
      agent_trace: [
        { agent: "screen", label: "Screen", kind: "rule", summary: "Deck + name present — passed gate", ms: 2 },
        { agent: "intake", label: "Signal Intake", kind: "ai", summary: "11 deck claims · GitHub/Devpost/Crunchbase pulled", ms: 1180 },
        { agent: "thesis", label: "Thesis Engine", kind: "rule", summary: "Exact match: E-commerce · Pre-seed · NA", ms: 5 },
        { agent: "scorer", label: "Multi-Axis Scorer", kind: "ai", summary: "3 axes scored · idea-vs-market rated bear", ms: 4020 },
        { agent: "diligence", label: "Diligence", kind: "ai", summary: "Waitlist claim contradicted · 2 undisclosed shutdowns found", ms: 4470 },
        { agent: "memo", label: "Memo Synthesizer", kind: "ai", summary: "Memo + 3 adversarial challenges · decline recommended", ms: 1990 },
      ],
    },
  },

  // ── 4. BORDERLINE-STRONG (sourced) ───────────────────────────────────────
  {
    founder_id: "f-004",
    company_id: "c-004",
    company_name: "Ferrite",
    sourcing_channel: "outbound",
    cold_start_flag: false,
    public_signals: {
      github: { repos: 21, commit_consistency_score: 0.85, longevity_months: 31 },
      devpost_hn: { launches: 1, total_upvotes: 512 },
      arxiv: { papers: 2 },
    },
    thesis: {
      thesis_match: true,
      match_type: "exact",
      rationale: "AI infrastructure · Pre-seed · Europe — core thesis sector.",
    },
    founder_score: { value: 71, confidence_interval: 11, trend: "improving" },
    founder_axis: {
      score: 78,
      trend: "improving",
      rationale:
        "Sourced off GitHub Trending before applying anywhere. 31 months of kernel-level work, a 4.2K-star autotuning library, two published papers. No commercial track record yet — hence the interval.",
      citations: [
        "GitHub: 21 repos, commit consistency 0.85, 31-month longevity",
        "Show HN launch: 512 upvotes",
        "arXiv: 2 papers on GPU kernel scheduling",
      ],
    },
    market_axis: {
      rating: "bullish",
      trend: "improving",
      rationale: "Inference cost is every AI company's #2 line item; kernel-level optimization is scarce, defensible expertise.",
      citations: ["Interview: three inbound acquisition-of-team offers already declined"],
    },
    idea_vs_market_axis: {
      rating: "neutral",
      trend: "stable",
      rationale:
        "Open-source adoption is real but monetization is undesigned — classic infra dilemma. Team sells performance, not yet a product.",
      citations: ["Deck slide 6: pricing page is 'coming soon'", "GitHub: 4.2K stars, 61 contributors"],
    },
    claim_trust: [
      { claim: "traction", confidence: "high", evidence: "4.2K GitHub stars and 61 external contributors — publicly verifiable." },
      { claim: "team", confidence: "high", evidence: "Both founders' papers and commit histories publicly confirm claimed expertise." },
      { claim: "market_size", confidence: "medium", evidence: "No sizing in deck; our estimate from cloud-spend reports." },
    ],
    memo: {
      required: {
        company_snapshot: "Open-source GPU kernel autotuner cutting inference costs 30-60%, found via GitHub Trending before the team began fundraising.",
        investment_hypotheses: [
          "The open-source library is a hiring and distribution wedge competitors can't replicate quickly.",
          "Inference cost pressure makes this a budget line, not a nice-to-have.",
        ],
        swot: {
          strengths: ["Deep scarce expertise, publicly verifiable", "Organic community traction"],
          weaknesses: ["No monetization design", "Neither founder has sold to enterprises"],
          opportunities: ["Every inference-heavy startup is a prospect"],
          threats: ["Nvidia ships equivalent tooling", "Hyperscalers absorb the layer"],
        },
        problem_and_product:
          "Teams overpay 30-60% for inference because kernels aren't tuned to their workloads. Ferrite autotunes them automatically per deployment.",
        traction_kpis: "4.2K stars · 61 contributors · 18 companies in the community Slack · pre-revenue.",
      },
      optional_or_flagged: {
        team_and_history: "Elif Kaya + Tomas Richter, ex-DeepMind performance team, left together in 2025.",
        cap_table: "Not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "Open-source love has never guaranteed revenue — monetization is entirely undesigned.",
        "If Nvidia ships this in CUDA, the standalone company disappears.",
      ],
    },
    portfolio_check: { overlap: false, note: "No exposure to AI infrastructure tooling." },
    verdict: "review",
    amount_recommended: 100000,
    enrichment: {
      one_liner: "Open-source autotuner that cuts GPU inference costs 30-60%.",
      problem: "Teams overpay for inference because kernels aren't tuned to their workloads.",
      solution: "Automatic per-deployment kernel autotuning, open-source core.",
      sector: "AI infrastructure",
      stage: "Pre-seed",
      geography: "Berlin, DE",
      website: "https://ferrite.example.dev",
      founders: [
        {
          name: "Elif Kaya",
          role: "Co-founder",
          avatar: "https://randomuser.me/api/portraits/women/22.jpg",
          background: "Ex-DeepMind performance team, 5 yrs. Lead author on both kernel-scheduling papers.",
          linkedin: "https://linkedin.com/in/elifkaya-gpu",
          github: "https://github.com/elifk",
          ai_read: "Sourced via GitHub Trending scan — applied to no fund before ours reached out. Papers + commits verify claimed depth.",
        },
        {
          name: "Tomas Richter",
          role: "Co-founder",
          avatar: "https://randomuser.me/api/portraits/men/18.jpg",
          background: "Ex-DeepMind, CUDA specialist. Maintains the 4.2K-star library day-to-day.",
          linkedin: "https://linkedin.com/in/tomas-richter-cuda",
          github: "https://github.com/trichter",
          x: "https://x.com/trichter_dev",
          ai_read: "61 external contributors accepted into his review pipeline — evidence of technical leadership beyond solo work.",
        },
      ],
      news: [
        { title: "Ferrite hits 4K stars in three months", source: "Hacker News", date: "2026-06-30" },
        { title: "The inference cost crunch, and who's solving it", source: "Latent Space", date: "2026-06-08" },
      ],
      market: {
        tam: 31, sam: 6, som: 0.2, unit: "$B",
        basis: "No sizing in deck (flagged). Our estimate: TAM from cloud inference spend reports; SAM = tunable GPU workloads; SOM at OSS-to-paid conversion norms.",
      },
      pmf: { signal: "early", note: "Strong pull on the open-source artifact (4.2K stars, 61 contributors) — but zero evidence anyone pays yet." },
      agent_trace: [
        { agent: "screen", label: "Screen", kind: "rule", summary: "Sourced: GitHub Trending scan, day 3", ms: 4 },
        { agent: "intake", label: "Signal Intake", kind: "ai", summary: "Partial score from public signals alone → activated outreach", ms: 1420 },
        { agent: "thesis", label: "Thesis Engine", kind: "rule", summary: "Exact match: AI infra · Pre-seed · EU", ms: 5 },
        { agent: "scorer", label: "Multi-Axis Scorer", kind: "ai", summary: "3 axes scored · market axis upgraded after interview", ms: 4150 },
        { agent: "diligence", label: "Diligence", kind: "ai", summary: "All public claims verified · market-size gap flagged", ms: 2980 },
        { agent: "memo", label: "Memo Synthesizer", kind: "ai", summary: "Memo assembled · review (monetization open question)", ms: 2010 },
      ],
    },
  },

  // ── 5. MIXED (inbound, one bear axis) ────────────────────────────────────
  {
    founder_id: "f-005",
    company_id: "c-005",
    company_name: "Kelpwise",
    sourcing_channel: "inbound",
    cold_start_flag: false,
    public_signals: {
      github: { repos: 5, commit_consistency_score: 0.6, longevity_months: 22 },
      devpost_hn: { launches: 1, total_upvotes: 129 },
      arxiv: { papers: 1 },
    },
    thesis: {
      thesis_match: true,
      match_type: "adjacent_llm_judged",
      rationale: "Climate MRV is adjacent to stated sectors — LLM judged the sensing/data angle close enough to the fund's deep-tech appetite.",
    },
    founder_score: { value: 58, confidence_interval: 14, trend: "improving" },
    founder_axis: {
      score: 66,
      trend: "improving",
      rationale:
        "Marine biology PhD turned engineer — rare, genuine founder-market fit for ocean carbon measurement. Software track record is shallower than the science.",
      citations: ["arXiv: 1 paper on kelp carbon sequestration rates", "GitHub: 5 repos, 22-month history"],
    },
    market_axis: {
      rating: "neutral",
      trend: "stable",
      rationale:
        "Blue-carbon credit market is early and standards-dependent; buyers exist but volumes hinge on registries formalizing kelp methodologies.",
      citations: ["Deck slide 4: registry timeline — externally confirmed but not yet ratified"],
    },
    idea_vs_market_axis: {
      rating: "bear",
      trend: "stable",
      rationale:
        "Hardware buoy network is capital-heavy for pre-seed, and revenue waits on a standards body outside the company's control.",
      citations: ["Deck slide 8: $310 unit cost × 400-buoy target", "Interview: no interim revenue plan while registries deliberate"],
    },
    claim_trust: [
      { claim: "team", confidence: "high", evidence: "PhD and publication verified; 2 seasons of field deployment photos with EXIF-consistent locations." },
      { claim: "traction", confidence: "medium", evidence: "2 paid pilot contracts with aquaculture farms confirmed; carbon-credit pipeline is speculative." },
      { claim: "market_size", confidence: "low", evidence: "Depends entirely on unratified registry methodology — flagged as conditional." },
    ],
    memo: {
      required: {
        company_snapshot: "Sensor buoys + ML measuring carbon sequestration of kelp farms, selling MRV data to credit registries and farm operators.",
        investment_hypotheses: [
          "If kelp methodologies ratify, first-mover MRV data becomes the toll booth for every credit issued.",
        ],
        swot: {
          strengths: ["Scientist-founder with field credibility", "2 paid pilots"],
          weaknesses: ["Capital-heavy hardware", "Revenue gated on external standards body"],
          opportunities: ["Registry ratification would unlock the whole market at once"],
          threats: ["Ratification slips years", "Satellite MRV leapfrogs buoys"],
        },
        problem_and_product:
          "Kelp farms can't sell carbon credits without trusted measurement. Kelpwise buoys measure sequestration continuously and package registry-grade MRV data.",
        traction_kpis: "2 paid pilots ($48K combined) · 40 buoys deployed · 1 registry partnership LOI.",
      },
      optional_or_flagged: {
        team_and_history: "Dr. Isla Marchetti (CEO, marine biology PhD) + Noah Tran (CTO, ex-Saildrone firmware).",
        cap_table: "Not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "The entire revenue model waits on a standards body the company doesn't control.",
        "Satellite-based MRV could make the buoy network obsolete before it scales.",
      ],
    },
    portfolio_check: { overlap: false, note: "No climate or MRV exposure." },
    verdict: "review",
    amount_recommended: 100000,
    enrichment: {
      one_liner: "Registry-grade carbon measurement for kelp farms, from a buoy network.",
      problem: "Kelp farms can't sell carbon credits without trusted measurement.",
      solution: "Sensor buoys + ML that package registry-grade MRV data continuously.",
      sector: "Climate",
      stage: "Pre-seed",
      geography: "Lisbon, PT",
      website: "https://kelpwise.example.com",
      founders: [
        {
          name: "Isla Marchetti",
          role: "CEO",
          avatar: "https://randomuser.me/api/portraits/women/12.jpg",
          background: "Marine biology PhD (Lisbon), published on kelp sequestration rates. 2 seasons of field deployments.",
          linkedin: "https://linkedin.com/in/isla-marchetti",
          ai_read: "Publication verified on arXiv; deployment photos EXIF-consistent with claimed sites. Science credibility is the anchor signal.",
        },
        {
          name: "Noah Tran",
          role: "CTO",
          avatar: "https://randomuser.me/api/portraits/men/51.jpg",
          background: "Ex-Saildrone firmware engineer, 4 yrs of ocean-hardened sensor work.",
          linkedin: "https://linkedin.com/in/noah-tran-hw",
          github: "https://github.com/ntran-hw",
          ai_read: "Commit history matches firmware role; hardware unit-cost claims consistent with his prior platform's BOM.",
        },
      ],
      news: [{ title: "Can kelp become a carbon market?", source: "Bloomberg Green", date: "2026-04-19" }],
      market: {
        tam: 14, sam: 1.8, som: 0.05, unit: "$B",
        basis: "TAM: blue-carbon projections IF registries ratify kelp — explicitly conditional. SAM: farms in ratifiable geographies. SOM: pilot-rate extrapolation.",
      },
      pmf: { signal: "early", note: "2 paid pilots prove farms will pay for measurement — but the big market waits on ratification." },
      agent_trace: [
        { agent: "screen", label: "Screen", kind: "rule", summary: "Deck + name present — passed gate", ms: 2 },
        { agent: "intake", label: "Signal Intake", kind: "ai", summary: "12 deck claims · GitHub/arXiv/press pulled", ms: 1310 },
        { agent: "thesis", label: "Thesis Engine", kind: "ai", summary: "Adjacent match — LLM judged deep-tech sensing angle a fit", ms: 1540 },
        { agent: "scorer", label: "Multi-Axis Scorer", kind: "ai", summary: "3 axes scored · idea-vs-market rated bear (capital + gating)", ms: 4080 },
        { agent: "diligence", label: "Diligence", kind: "ai", summary: "Pilots verified · market size marked conditional", ms: 3350 },
        { agent: "memo", label: "Memo Synthesizer", kind: "ai", summary: "Memo assembled · review pending registry-risk discussion", ms: 1930 },
      ],
    },
  },

  // ── 6. STRONG BUT PORTFOLIO-BLOCKED ──────────────────────────────────────
  {
    founder_id: "f-006",
    company_id: "c-006",
    company_name: "Ledgerline",
    sourcing_channel: "inbound",
    cold_start_flag: false,
    public_signals: {
      github: { repos: 7, commit_consistency_score: 0.75, longevity_months: 20 },
      devpost_hn: { launches: 2, total_upvotes: 210 },
      arxiv: { papers: 0 },
    },
    thesis: {
      thesis_match: true,
      match_type: "exact",
      rationale: "Fintech · Pre-seed · Europe/Africa corridor — inside stated sectors and geography.",
    },
    founder_score: { value: 81, confidence_interval: 7, trend: "stable" },
    founder_axis: {
      score: 84,
      trend: "stable",
      rationale:
        "Ex-Flutterwave payments lead who built the exact reconciliation system she's now productizing. Deep, verifiable domain history.",
      citations: ["LinkedIn + press: 4 yrs leading reconciliation at Flutterwave", "GitHub: 7 repos incl. open-source ledger tooling used by 3 fintechs"],
    },
    market_axis: {
      rating: "bullish",
      trend: "stable",
      rationale: "Cross-border SMB trade reconciliation is a compliance-driven must-have; regulation is expanding the addressable pool annually.",
      citations: ["Deck slide 5: regulatory timeline, externally confirmed"],
    },
    idea_vs_market_axis: {
      rating: "bullish",
      trend: "improving",
      rationale: "Wedge is narrow and urgent (audit-ready reconciliation), expansion path is natural (payments, FX).",
      citations: ["Deck slide 7: 9 paying customers, $21K MRR", "Diligence: 8 of 9 customers confirmed by reference"],
    },
    claim_trust: [
      { claim: "traction", confidence: "high", evidence: "$21K MRR; 8 of 9 claimed customers confirmed by direct reference." },
      { claim: "team", confidence: "high", evidence: "Flutterwave history verified via press and two former colleagues." },
      { claim: "market_size", confidence: "medium", evidence: "Deck's TAM reasonable but conflates SMB and enterprise segments." },
    ],
    memo: {
      required: {
        company_snapshot: "Audit-ready reconciliation for SMB exporters moving money across African and European corridors.",
        investment_hypotheses: [
          "Compliance pressure makes reconciliation a must-buy before it's a nice-to-have.",
          "Founder's operator history at Flutterwave is direct, verified founder-market fit.",
        ],
        swot: {
          strengths: ["Verified revenue", "Operator-grade domain depth"],
          weaknesses: ["Solo founder carrying product + sales"],
          opportunities: ["Regulatory expansion grows the pool annually"],
          threats: ["Banks bundling reconciliation into corridor products"],
        },
        problem_and_product:
          "SMB exporters reconcile cross-border payments in spreadsheets and fail audits. Ledgerline auto-matches transactions across currencies and produces audit-ready records.",
        traction_kpis: "$21K MRR · 9 paying customers (8 verified) · 3-month logo retention 100%.",
      },
      optional_or_flagged: {
        team_and_history: "Grace Adeyemi, solo founder — ex-Flutterwave reconciliation lead, 4 yrs.",
        cap_table: "Angels only, uncapped SAFEs — details not disclosed",
      },
    },
    adversarial_view: {
      challenges: [
        "Portfolio overlap: existing position in Cartel's fintech affiliate creates concentration risk in the same corridor.",
        "Solo founder at $21K MRR — key-person risk is unpriced.",
      ],
    },
    portfolio_check: { overlap: true, note: "Corridor overlap with 2025 fintech position — concentration, not competition." },
    verdict: "review",
    amount_recommended: 100000,
    enrichment: {
      one_liner: "Audit-ready reconciliation for SMB exporters across Africa–Europe corridors.",
      problem: "Cross-border SMBs reconcile payments in spreadsheets and fail audits.",
      solution: "Auto-matched transactions across currencies, packaged audit-ready.",
      sector: "Fintech",
      stage: "Pre-seed",
      geography: "London, UK / Lagos, NG",
      website: "https://ledgerline.example.com",
      founders: [
        {
          name: "Grace Adeyemi",
          role: "Founder & CEO",
          avatar: "https://randomuser.me/api/portraits/women/31.jpg",
          background: "Ex-Flutterwave reconciliation lead, 4 yrs — built the internal system she's now productizing. Open-source ledger tooling used by 3 fintechs.",
          linkedin: "https://linkedin.com/in/grace-adeyemi-fintech",
          github: "https://github.com/gadeyemi",
          x: "https://x.com/graceadeyemi",
          ai_read: "Strongest verified operator history in the pipeline — two direct references confirmed role and scope. Only flag: solo.",
        },
      ],
      news: [
        { title: "Ledgerline raises angel round for cross-border reconciliation", source: "TechCabal", date: "2026-03-14" },
        { title: "Why African SMB exporters fail audits", source: "Rest of World", date: "2026-02-02" },
      ],
      market: {
        tam: 18, sam: 4.2, som: 0.3, unit: "$B",
        basis: "TAM from deck, adjusted down after diligence split SMB from enterprise. SAM: corridor SMB exporters under new audit rules. SOM: 3-yr at current ACV.",
      },
      pmf: { signal: "strong", note: "9 paying customers with 100% 3-month retention — pulled, not sold." },
      agent_trace: [
        { agent: "screen", label: "Screen", kind: "rule", summary: "Deck + name present — passed gate", ms: 2 },
        { agent: "intake", label: "Signal Intake", kind: "ai", summary: "13 deck claims · GitHub/press/references pulled", ms: 1200 },
        { agent: "thesis", label: "Thesis Engine", kind: "rule", summary: "Exact match: Fintech · Pre-seed · EU/Africa", ms: 5 },
        { agent: "scorer", label: "Multi-Axis Scorer", kind: "ai", summary: "3 axes scored · all bullish or high", ms: 3980 },
        { agent: "diligence", label: "Diligence", kind: "ai", summary: "8/9 customers reference-confirmed · TAM adjusted down", ms: 5100 },
        { agent: "memo", label: "Memo Synthesizer", kind: "ai", summary: "Approve-grade memo · routed to review on portfolio overlap", ms: 2100 },
      ],
    },
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
  "f-004": {
    founder_score: { value: 71, confidence_interval: 11, trend: "improving" },
    narrative:
      "We found you before you applied anywhere — your public engineering record is exceptional and fully verified. The open question holding your score's ceiling is commercial: show one design partner paying, and both the number and our confidence will move.",
  },
  "f-005": {
    founder_score: { value: 58, confidence_interval: 14, trend: "improving" },
    narrative:
      "Your scientific credibility is verified and rare, and your pilots prove farms will pay. The uncertainty in your score reflects market timing outside your control, not doubts about you — interim revenue while registries deliberate would change the picture fastest.",
  },
  "f-006": {
    founder_score: { value: 81, confidence_interval: 7, trend: "stable" },
    narrative:
      "Your verified revenue and operator history put you near the top of everything we've scored. The current hold isn't about you — it's a fund-side portfolio concentration question being discussed this week.",
  },
}

// One-line pitch for dashboard rows.
export const pitchOf = (opp) => opp.enrichment?.one_liner ?? opp.memo.required.company_snapshot
