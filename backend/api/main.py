from fastapi import FastAPI
app = FastAPI(title="FounderScore")

@app.get("/health")
def health():
    return {"status": "ok"}
