import pytest
from app.main import app

def test_app_creation():
    """Test that the FastAPI app is created correctly"""
    assert app.title == "docs"
    assert app.version == "0.1.0"
    assert app.description == "Documentation service for MySwiftAgent"