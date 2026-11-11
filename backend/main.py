import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root directory is on Python search path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure backend environment variables are loaded regardless of working directory
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from limiter import limiter
from routes import invoices, webhooks

app = FastAPI(
    title="LedgerMind Autonomous FinOps Engine",
    description="Multi-agent invoice extraction, audit, and reconciliation pipeline.",
    version="1.0.0"
)

# Attach rate limiter to app state and register SlowAPIMiddleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Custom enterprise 429 response handler for rate limiting
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "Rate limit exceeded",
            "detail": f"Too many requests. Quota policy: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", None)
        }
    )

# Enable CORS for local and staging frontends (e.g., React Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register clean route modules (supports /api/invoices and /api/v1/invoices)
app.include_router(invoices.router, prefix="/api/invoices")
app.include_router(invoices.router, prefix="/api/v1/invoices")
app.include_router(webhooks.router)

@app.get("/", summary="System Health Check")
def health_check():
    """System health check endpoint."""
    return {
        "status": "online",
        "system": "LedgerMind FinOps Engine",
        "database": "PostgreSQL (Neon Connected)"
    }
