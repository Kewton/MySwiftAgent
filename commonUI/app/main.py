from fastapi import FastAPI

app = FastAPI(
    title="commonUI",
    version="0.1.0",
    description="共通UI コンポーネントとテンプレート管理サービス"
)

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント（CI/CDで使用）"""
    return {"status": "healthy", "service": "commonUI"}

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "Welcome to commonUI"}

@app.get("/api/v1/")
async def api_root():
    """API v1 ルート"""
    return {"version": "1.0", "service": "commonUI"}