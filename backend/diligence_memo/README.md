# Part C: Diligence, Trust, Memo, and Interview

This package owns claim validation, per-claim Trust Score output, memo synthesis,
the separate adversarial view, portfolio overlap checks, and the adaptive text
interview. It follows the locked shapes in `shared/contract.md`.

## Local configuration

Copy `.env.example` to `.env` and replace both placeholders. The local `.env` is
ignored by Git and loaded automatically by `clients.py`.

```dotenv
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

## Public entry points

### Diligence-to-memo pipeline

```python
from backend.diligence_memo import ClaimValidator, DiligenceMemoPipeline
from backend.diligence_memo.clients import OpenAIReasoningClient, TavilySearchClient

pipeline = DiligenceMemoPipeline(
    ClaimValidator(TavilySearchClient(), OpenAIReasoningClient())
)
result = pipeline.run(
    {
        "company_name": "Acme",
        "sector": "Fintech infrastructure",
        "deck_claims": [
            {"field": "traction", "value": "$50k ARR", "source_slide": 5}
        ],
    }
)
```

`result` contains `diligence`, per-claim `trust`, `memo`, a separate
`adversarial_view`, `portfolio_check`, `verdict`, and `amount_recommended`.
When `result["diligence"]["memory_update"]` is true, the Memory/API owner should
persist the accompanying gap findings.

### Interview

```python
from backend.diligence_memo import InterviewAgent

session = InterviewAgent().start(deck_claims, max_questions=5)
while (question := session.next_question()) is not None:
    answer = get_founder_text_answer(question)
    session.record_response(answer)
result = session.result()
```

The interview requires 4 or 5 completed text answers. Its score reflects response
patterns such as engaged, updated, defensive, or evasive; it does not judge factual
correctness and is not a psychological assessment.

## Verification

Run the offline suite:

```powershell
python -m unittest discover -s backend/diligence_memo/tests -v
```

Run the low-cost live OpenAI + Tavily + complete-pipeline smoke test:

```powershell
python -m backend.diligence_memo.live_smoke
```

The live command prints only sanitized counts and statuses, never keys or evidence
content.
