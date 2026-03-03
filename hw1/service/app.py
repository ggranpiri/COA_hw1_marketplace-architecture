from fastapi import FastAPI

app = FastAPI(title="marketplace-health-service", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}