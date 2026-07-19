# Scout

> AI-powered VC decision system that evaluates startup founders in 24 hours

Scout is an autonomous investment decision platform that combines multi-axis scoring, thesis matching, claim validation, and adaptive interviewing to recommend $100K checks to early-stage startups.

## 🎯 Overview

Traditional VC evaluation takes weeks and relies heavily on manual review. FounderScore automates the entire diligence process using AI agents while maintaining rigorous evaluation standards:

- **Multi-Axis Scoring**: Independent evaluation of Founder, Market, and Idea-vs-Market fit (never averaged)
- **Thesis Engine**: Two-stage filtering (deterministic + LLM) against investment criteria
- **Auto-Discovery**: Tavily-powered LinkedIn/GitHub profile discovery for team members
- **Claim Validation**: Bounded public evidence checks using Tavily search
- **Adaptive Interview**: 5-question session that assesses founder resilience and updates scores
- **Memory Layer**: EMA-based scoring that tracks founder evolution across signals

**Result**: Full investment memo with verdict (approve/review/decline) and check recommendation in under 24 hours.

---

## 🏗️ Architecture

### Tech Stack

**Backend** (Python 3.13+)
- FastAPI - API framework
- SQLite - Application/interview storage
- OpenAI GPT-4o - LLM reasoning for scoring, claim validation, interviews
- Tavily - Bounded web search for claim validation and profile discovery
- Pydantic - Data validation
- People Data Labs - LinkedIn profile enrichment (optional)

**Frontend** (React 19)
- React Router - Navigation
- Vite - Build tool
- Tailwind CSS 4 - Styling
- Framer Motion - Animations
- Lucide React - Icons

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  Dashboard │ Memo View │ Founder Results │ Interview        │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Signal Intake│  │   Scoring    │  │  Diligence   │      │
│  │              │  │              │  │              │      │
│  │ • Deck Parse │  │ • Multi-Axis │  │ • Validator  │      │
│  │ • Outbound   │  │ • Thesis     │  │ • Memo       │      │
│  │ • Team Auto  │  │ • Query      │  │ • Interview  │      │
│  │   Discovery  │  │   Parser     │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Memory DB   │  │  App Store   │  │ Presentation │      │
│  │  (EMA Score) │  │  (SQLite)    │  │  (Enrichment)│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 1. **Intelligent Team Discovery**
Automatically finds LinkedIn and GitHub profiles for all team members mentioned in pitch decks using Tavily search. Supports multiple name formats ("Name as Role", "Name (Role)").

### 2. **Multi-Axis Scoring System**
Three independent axes scored 0-100 or bullish/neutral/bear:
- **Founder Axis**: Track record, execution ability, technical depth
- **Market Axis**: Timing, market size, growth trajectory
- **Idea-vs-Market Axis**: Product-market fit, competition, positioning

**Founder Score Formula:**
```
Founder Score = 0.30×Track Record + 0.20×Traction Signal
              + 0.25×Founder-Market Fit + 0.25×Resilience
```

### 3. **Adaptive Interview Agent**
5-question session that:
- Challenges founders on deck claims
- Identifies evasive vs. engaged patterns
- Scores resilience (engaged_updated: 90, defensive: 35, evasive: 15)
- Updates Founder Score based on responses

### 4. **Memory Layer with EMA Scoring**
Persistent scoring across multiple signals:
- **Exponential Moving Average** (α=0.3) weights recent evidence
- **Confidence interval** narrows with more independent sources (25→5)
- **Event-triggered recomputation** on every new signal
- **Append-only audit trail** preserves complete history

### 5. **Bounded Claim Validation**
Never unbounded scraping - only:
- 5 Tavily results for company press
- 1 GitHub profile check
- 1 company website metadata fetch
- Exact LinkedIn URLs supplied by founders

### 6. **Two-Stage Thesis Engine**
1. **Deterministic gate**: Keyword matching for exact/adjacent/reject
2. **LLM judgment**: GPT-4o evaluates edge cases for adjacent sectors

---

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- Node.js 18+
- OpenAI API key
- Tavily API key
- (Optional) People Data Labs API key

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/aryanpradhan1/VCBrain.git
cd VCBrain
```

**2. Backend Setup**
```bash
cd backend

# Install Python dependencies
pip3 install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY='sk-...'
export TAVILY_API_KEY='tvly-...'
export PEOPLE_DATA_LABS_API_KEY='...'  # Optional
```

**3. Frontend Setup**
```bash
cd ../frontend

# Install Node dependencies
npm install

# Create .env file
echo 'VITE_API_URL=http://localhost:8000' > .env
```

### Running the Application

**Terminal 1 - Backend**
```bash
cd backend/api
python3 main.py
```
Backend runs at http://localhost:8000

**Terminal 2 - Frontend**
```bash
cd frontend
npm run dev
```
Frontend runs at http://localhost:5173

**Access the application:** Open http://localhost:5173 in your browser

---

## 📁 Project Structure

```
VCBrain/
├── backend/
│   ├── api/                      # FastAPI application
│   │   ├── main.py              # API routes and glue logic
│   │   ├── db.py                # Memory layer (EMA scoring)
│   │   ├── store.py             # Application storage (SQLite)
│   │   ├── presentation.py      # Data enrichment for UI
│   │   ├── source_enrichment.py # Profile discovery, metadata
│   │   └── document_intake.py   # Deck parsing
│   ├── scoring/                  # Multi-axis scorer
│   │   ├── multi_axis_scorer.py # Founder/Market/Idea scoring
│   │   ├── thesis_engine.py     # Investment thesis matching
│   │   └── query_parser.py      # Natural language search
│   ├── diligence_memo/          # Claim validation & memo
│   │   ├── validator.py         # Tavily-based claim checking
│   │   ├── memo.py              # Investment memo synthesis
│   │   └── interview.py         # Adaptive interview agent
│   └── signal_intake/           # Inbound & outbound sourcing
│       ├── deck_parser.py       # Extract claims from decks
│       └── outbound_scan.py     # GitHub/HN/arXiv scanning
├── frontend/
│   ├── src/
│   │   ├── pages/               # Route pages
│   │   │   ├── dashboard.jsx   # Opportunity list
│   │   │   ├── memo.jsx        # Full investment memo
│   │   │   ├── founder-results.jsx # Founder score view
│   │   │   └── interview.jsx   # Interview session
│   │   ├── components/          # Reusable UI components
│   │   └── lib/                 # API client, utilities
│   └── public/
├── shared/
│   ├── fixtures/                # Test data
│   └── contract.md             # API contract spec
└── README.md
```

---

## 🔌 API Documentation

### Core Endpoints

#### `GET /opportunities`
List all opportunities with optional filtering
```bash
# All opportunities
curl http://localhost:8000/opportunities

# Natural language query
curl "http://localhost:8000/opportunities?query=technical+founder+AI+infra"

# Thesis filter
curl "http://localhost:8000/opportunities?thesis_filter=true"
```

#### `GET /opportunities/{company_id}`
Get full opportunity details (investor view)
```json
{
  "founder_id": "f001",
  "company_id": "c001",
  "founder_score": {
    "value": 68,
    "confidence_interval": 12,
    "trend": "improving"
  },
  "founder_axis": { "score": 72, "rationale": "...", "citations": [...] },
  "market_axis": { "rating": "bullish", "rationale": "..." },
  "claim_trust": [...],
  "memo": { "required": {...}, "optional_or_flagged": {...} },
  "verdict": "approve",
  "amount_recommended": 100000
}
```

#### `GET /founders/{founder_id}/results`
Founder-facing lightweight view (read-only)
```json
{
  "founder_score": {
    "value": 65,
    "confidence_interval": 10,
    "trend": "stable"
  },
  "narrative": "Strong profile with demonstrated execution ability..."
}
```

#### `POST /founders/{founder_id}/interviews`
Start or resume interview session
```json
{
  "session_id": "session-123",
  "status": "active",
  "question": "What is the strongest evidence that customers want what you are building?",
  "question_number": 1,
  "total_questions": 5
}
```

#### `POST /interviews/{session_id}/responses`
Submit interview response
```bash
curl -X POST http://localhost:8000/interviews/session-123/responses \
  -H "Content-Type: application/json" \
  -d '{"response": "We have 50 LOIs from hospitals..."}'
```

**Interactive API Docs:** http://localhost:8000/docs

---

## 🧪 Testing

### Backend Tests
```bash
cd backend/scoring
python3 -m pytest test_all_axes.py
python3 -m pytest test_thesis_engine.py
python3 -m pytest test_query_parser.py
```

### Manual Testing
```bash
# Test team member auto-discovery
cd backend/api
python3 test_team_discovery.py

# Test updated scoring rubric
python3 test_rescore.py

# API health check
curl http://localhost:8000/health
```

---

## 🎨 Design System

### Color Palette
- **Primary**: Blue 600 (`#2563eb`)
- **Success**: Emerald 600 (`#10b981`)
- **Warning**: Amber 600 (`#d97706`)
- **Danger**: Red 600 (`#dc2626`)

### Typography
- **Font**: Inter Variable (system fallback: -apple-system, BlinkMacSystemFont)
- **Headings**: 600-700 weight, tight tracking
- **Body**: 400 weight, relaxed leading

### Components
- **Cards**: Rounded corners (12-24px), subtle shadows, backdrop blur
- **Buttons**: Gradient backgrounds, hover scale animations
- **Animations**: Framer Motion with custom easing curves

---

## 🧠 How It Works

### Application Processing Pipeline

```
1. INTAKE
   └─ Extract deck claims (market_size, traction, team, ask, problem_product)
   └─ Parse team members from deck text
   └─ Auto-discover LinkedIn/GitHub profiles via Tavily

2. SCORING
   └─ Multi-Axis Scorer evaluates Founder/Market/Idea independently
   └─ Thesis Engine determines exact/adjacent/reject match
   └─ Memory Layer computes EMA-based Founder Score

3. DILIGENCE
   └─ Claim Validator checks each deck claim against Tavily results
   └─ Trust scores assigned (high/medium/low confidence)
   └─ Memo Synthesizer generates investment memo

4. INTERVIEW (Optional)
   └─ Founder answers 5 adaptive questions
   └─ Response pattern classified (engaged/defensive/evasive)
   └─ Resilience score computed, Founder Score updated

5. VERDICT
   └─ Decline if thesis doesn't match
   └─ Otherwise, use diligence verdict (approve/review/decline)
   └─ Recommend check amount ($0-$100K)
```

### Founder Score Evolution

```
Signal 1 (Deck):           Score = 53 ± 25  (cold start, wide interval)
Signal 2 (GitHub):         Score = 56 ± 18  (more evidence, narrowing)
Signal 3 (HN Launch):      Score = 59 ± 14  (upward trend)
Signal 4 (Interview: 90):  Score = 65 ± 10  (strong interview boosts score)
```

**Formula:** `new_score = 0.3 × new_signal + 0.7 × old_score`

---

## 👥 Team

**Aryan Pradhan** 
**Shrishant Hattarki**
**Anay Apte**
**Subash Skanthakumar**

---

## 📝 Development Notes

### Key Design Decisions

1. **Why EMA over simple average?**
   Recent signals matter more in founder evaluation. EMA (α=0.3) gives 30% weight to new evidence while maintaining historical context.

2. **Why separate axes instead of a single score?**
   Averaging masks critical information. A 70/100 could mean "good at everything" or "great founder, terrible market" - investors need to see both.

3. **Why bounded search only?**
   Unbounded scraping is expensive, slow, and legally risky. We limit to 5 Tavily results + 1 GitHub check + exact founder-submitted URLs.

4. **Why SQLite instead of Postgres?**
   Zero-setup, file-based, perfect for single-server deployments. Production would scale to Postgres if needed.

### Contract-Driven Development

All modules follow strict contracts defined in `/shared/contract.md`:
- Signal Intake outputs → Scoring inputs
- Scoring outputs → Diligence inputs
- Diligence outputs → Frontend shapes

This prevents integration bugs and enables parallel development.

---

## 🚢 Deployment

**Backend (Railway/Render)**
```bash
# Set environment variables in dashboard
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Deploy command
uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
```

**Frontend (Vercel/Netlify)**
```bash
# Build command
npm run build

# Environment variables
VITE_API_URL=https://your-backend.railway.app
```

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- OpenAI GPT-4o for LLM reasoning
- Tavily for bounded web search
- People Data Labs for LinkedIn enrichment
- Hack Nation for inspiration and support

---

## 📧 Contact

Questions? Reach out to [aryanpradhan2023@gmail.com](mailto:aryanpradhan2023@gmail.com)

**Built with ❤️ by the Scout team**
