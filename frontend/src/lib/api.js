// API layer. With VITE_API_URL unset we serve fixtures with realistic latency;
// set VITE_API_URL to B's FastAPI base URL and every call becomes a real fetch —
// same shapes per /shared/contract.md, so the swap is a no-op for the screens.

import { opportunities, founderResults } from "@/fixtures/opportunities"

const BASE = import.meta.env.VITE_API_URL

// API records intentionally store relative media paths so they remain portable
// between local development and deployment. Browser components must resolve
// those paths against FastAPI rather than the Vite host.
export function assetUrl(path) {
  if (!path || /^(https?:|data:|blob:)/i.test(path)) return path
  return BASE ? `${BASE}${path}` : path
}

const delay = (ms) => new Promise((r) => setTimeout(r, ms))
const mockInterviewSessions = new Map()

const DEMO_INTERVIEW_QUESTIONS = [
  "What's the strongest independent evidence that customers want what you're building?",
  "If that evidence proved weaker than expected, what would you change in the next 30 days?",
  "What's the most important belief about this company that you've revised, and what changed it?",
  "Which missing capability creates the greatest execution risk for your team?",
  "What evidence could falsify the central claim in your pitch?",
]

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
  const fixtureId = /^f\d+$/.test(founderId)
    ? founderId.replace(/^f/, "f-")
    : founderId
  const res = founderResults[fixtureId]
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

export async function startFounderInterview(founderId) {
  if (BASE) {
    return real(`/founders/${founderId}/interview/start`, { method: "POST" })
  }
  await delay(450)
  mockInterviewSessions.set(founderId, { questionIndex: 0, responses: [] })
  return {
    question: DEMO_INTERVIEW_QUESTIONS[0],
    question_number: 1,
    total_questions: DEMO_INTERVIEW_QUESTIONS.length,
    complete: false,
  }
}

export async function respondToFounderInterview(founderId, answer) {
  if (BASE) {
    return real(`/founders/${founderId}/interview/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer }),
    })
  }
  await delay(550)
  const session = mockInterviewSessions.get(founderId)
  if (!session) throw new Error("Interview has not been started")
  session.responses.push(answer)
  session.questionIndex += 1
  if (session.questionIndex >= DEMO_INTERVIEW_QUESTIONS.length) {
    mockInterviewSessions.delete(founderId)
    return {
      question: null,
      question_number: DEMO_INTERVIEW_QUESTIONS.length,
      total_questions: DEMO_INTERVIEW_QUESTIONS.length,
      complete: true,
    }
  }
  const adaptiveQuestion = answer.trim().split(/\s+/).length < 8
    ? "What specific evidence would let an investor independently verify that answer?"
    : DEMO_INTERVIEW_QUESTIONS[session.questionIndex]
  return {
    question: adaptiveQuestion,
    question_number: session.questionIndex + 1,
    total_questions: DEMO_INTERVIEW_QUESTIONS.length,
    complete: false,
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

export async function getThesis() {
  if (BASE) return real("/thesis")
  await delay(300)
  return { sectors: ["AI infrastructure", "Developer tools", "Robotics"], stage: "Pre-seed", geos: ["North America", "Europe"], check: "$100K", ownership: "1–2%", risk: "Balanced" }
}

export async function saveThesis(config) {
  if (BASE) return real("/thesis", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) })
  await delay(450)
  return config
}

export async function startInterview(founderId) {
  if (BASE) return real(`/founders/${founderId}/interviews`, { method: "POST" })
  await delay(450)
  return { session_id: "demo-interview", status: "active", question: "What is the strongest evidence that customers want what you are building?", question_number: 1, total_questions: 5, completed: false }
}

export async function respondToInterview(sessionId, response) {
  if (BASE) return real(`/interviews/${sessionId}/responses`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ response }) })
  await delay(500)
  return { session_id: sessionId, status: "completed", question: null, question_number: 5, total_questions: 5, completed: true }
}
