"""myVault - Secure personal data vault and secret management service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="myVault",
    version="0.1.0",
    description="Secure personal data vault and secret management service",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint (required for CI/CD)."""
    return {"status": "healthy", "service": "myVault"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to myVault - Secure data vault service"}


@app.get("/api/v1/")
async def api_root() -> dict[str, str]:
    """API v1 root."""
    return {"version": "1.0", "service": "myVault"}
