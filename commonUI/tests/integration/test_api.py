def test_health_check(client):
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "commonUI"}


def test_root_endpoint(client):
    """ルートエンドポイントのテスト"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to commonUI"}


def test_api_root_endpoint(client):
    """API v1 ルートエンドポイントのテスト"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {"version": "1.0", "service": "commonUI"}