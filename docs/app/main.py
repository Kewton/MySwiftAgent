from fastapi import FastAPI

app = FastAPI(
    title="docs",
    version="0.1.0",
    description="Documentation service for MySwiftAgent"
)

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント（CI/CDで使用）"""
    return {"status": "healthy", "service": "docs"}

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "Welcome to docs"}

@app.get("/api/v1/")
async def api_root():
    """API v1 ルート"""
    return {"version": "1.0", "service": "docs"}