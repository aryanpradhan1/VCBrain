// API layer. With VITE_API_URL unset we serve fixtures with realistic latency;
// set VITE_API_URL to B's FastAPI base URL and every call becomes a real fetch —
// same shapes per /shared/contract.md, so the swap is a no-op for the screens.

import { opportunities, founderResults } from "@/fixtures/opportunities"

const BASE = import.meta.env.VITE_API_URL

const delay = (ms) => new Promise((r) => setTimeout(r, ms))

async function real(path, options) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json()
}

export async function listOpportunities() {
  if (BASE) return real("/opportunities")
  await delay(650)
  return [...opportunities].sort((a, b) => b.founder_score.value - a.founder_score.value)
}

export async function getOpportunity(id) {
  if (BASE) return real(`/opportunities/${id}`)
  await delay(500)
  const opp = opportunities.find((o) => o.company_id === id)
  if (!opp) throw new Error("Opportunity not found")
  return opp
}

export async function getFounderResults(founderId) {
  if (BASE) return real(`/founders/${founderId}/results`)
  await delay(700)
  const res = founderResults[founderId]
  if (!res) throw new Error("Founder not found")
  return res
}

export async function postDecision(id, decision) {
  if (BASE)
    return real(`/opportunities/${id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    })
  await delay(450)
  return { decision }
}

export async function submitApplication(formData) {
  if (BASE) return real("/applications", { method: "POST", body: formData })
  await delay(800)
  return { company_id: "demo-submission", founder_id: "f-002", status: "queued", status_url: "/applications/demo-submission" }
}

export async function getApplicationStatus(id) {
  if (BASE) return real(`/applications/${id}`)
  await delay(600)
  return { company_id: id, founder_id: "f-002", company_name: "Demo company", status: "ready", opportunity_url: "/opportunities/c-002" }
}
