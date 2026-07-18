import { BrowserRouter, Route, Routes } from "react-router-dom"

import { InvestorShell } from "@/components/layout/investor-shell"
import Apply from "@/pages/apply"
import Dashboard from "@/pages/dashboard"
import FounderResults from "@/pages/founder-results"
import Interview from "@/pages/interview"
import Memo from "@/pages/memo"
import Thesis from "@/pages/thesis"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Investor workspace — full detail, decision controls */}
        <Route element={<InvestorShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/opportunities/:id" element={<Memo />} />
          <Route path="/thesis" element={<Thesis />} />
        </Route>

        {/* Founder-facing — score + narrative only, ever */}
        <Route path="/apply" element={<Apply />} />
        <Route path="/founder/:id" element={<FounderResults />} />
        <Route path="/founder/:id/interview" element={<Interview />} />
      </Routes>
    </BrowserRouter>
  )
}
