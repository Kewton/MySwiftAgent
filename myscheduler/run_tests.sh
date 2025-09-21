#!/bin/bash

echo "=================================="
echo "MyScheduler Test Script (uv)"
echo "=================================="

# uvがインストールされているかチェック
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 依存関係のインストール（開発用依存関係含む）
echo "Installing dependencies with uv..."
uv sync --extra dev

# テストの実行
echo "Running tests..."
uv run pytest test_app.py -v

# テスト結果の確認
if [ $? -eq 0 ]; then
    echo "=================================="
    echo "✅ All tests passed!"
    echo "=================================="
    echo ""
    echo "To start the server:"
    echo "  uv run uvicorn app:app --reload"
    echo ""
    echo "To run the usage example:"
    echo "  uv run python example_usage.py"
    echo ""
    echo "To run linting:"
    echo "  uv run ruff check ."
    echo "  uv run ruff format ."
    echo ""
    echo "API documentation:"
    echo "  http://localhost:8000/docs"
else
    echo "=================================="
    echo "❌ Some tests failed!"
    echo "=================================="
    exit 1
fi