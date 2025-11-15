# 運用・その他 (Ops)

デプロイ手順、トラブルシュート、運用ガイドを集約。

## ドキュメント一覧

<!-- /doc-register コマンドで自動更新 -->

### トラブルシューティング

- **[dev-start-troubleshooting.md](./dev-start-troubleshooting.md)** - dev-start.sh起動時の問題と解決策
  - Issue #166: SQLAlchemy非同期ドライバーエラー
  - CommonUIステータスチェック修正
  - myAgentDeskサービス統合

### ローカル開発

- **[local-development.md](./local-development.md)** - ローカル開発環境の起動方法
  - dev-start.sh（推奨）
  - quick-start.sh（docker-compose並行実行用）
  - docker-compose（本番環境検証）
  - ポート番号設計・使い分け

### デプロイメント

- **[deployment-guide.md](./deployment-guide.md)** - デプロイメント手順
- **[valkey-operations.md](./valkey-operations.md)** - Valkey運用ガイド

---

**最終更新**: 2025-11-15
