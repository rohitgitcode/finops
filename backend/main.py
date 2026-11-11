import sys
from pathlib import Path

# Ensure backend root directory is on Python search path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import invoices, webhooks

app = FastAPI(
    title="LedgerMind Autonomous FinOps Engine",
    description="Multi-agent invoice extraction, audit, and reconciliation pipeline.",
    version="1.0.0"
)

# Enable CORS for local and staging frontends (e.g., React Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register clean route modules
app.include_router(invoices.router)
app.include_router(webhooks.router)

@app.get("/", summary="System Health Check")
def health_check():
    """System health check endpoint."""
    return {
        "status": "online",
        "system": "LedgerMind FinOps Engine",
        "database": "PostgreSQL (Neon Connected)"
    }
