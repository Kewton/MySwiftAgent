def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "docs"}

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to docs"}

def test_api_v1_root(client):
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {"version": "1.0", "service": "docs"}