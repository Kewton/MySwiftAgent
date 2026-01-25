# commonUI ドキュメント

commonUIの共通UIコンポーネントに関するドキュメントです。

## 概要

commonUIはStreamlitベースの共通UIコンポーネントを提供します。
複数のサービスで再利用可能なUI部品を含みます。

## コンポーネント一覧

| コンポーネント | 説明 | 使用場所 |
|---------------|------|---------|
| `JobStatusCard` | ジョブ状態表示カード | ダッシュボード |
| `WorkflowViewer` | ワークフロー可視化 | 詳細画面 |
| `LogViewer` | ログ表示コンポーネント | 実行結果画面 |

## 使用方法

```python
from commonUI.components import JobStatusCard

# ジョブ状態カードの表示
JobStatusCard(
    job_id="job-uuid",
    status="running",
    progress=50
)
```

## 開発

### セットアップ

```bash
cd commonUI
uv sync
```

### 実行

```bash
uv run streamlit run app.py
```

ブラウザで http://localhost:8501 を開きます。

### テスト

```bash
uv run pytest tests/
```

## ディレクトリ構成

```
commonUI/
├── app.py                 # メインアプリケーション
├── components/            # 再利用可能なコンポーネント
│   ├── __init__.py
│   ├── job_status.py
│   ├── workflow_viewer.py
│   └── log_viewer.py
├── utils/                 # ユーティリティ
├── tests/                 # テスト
└── pyproject.toml
```

## 関連ドキュメント

- [myAgentDesk](../../myAgentDesk/docs/)
- [システム概要](../../docs/architecture/overview.md)
