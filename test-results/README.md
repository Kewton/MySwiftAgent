# テスト結果ディレクトリ構造

このディレクトリはすべてのテスト実行結果を格納します。

## 📁 ディレクトリ構造

```
test-results/
├── README.md                 # このファイル
├── playwright-report/        # Playwright HTMLレポート
│   └── index.html           # レポートのエントリーポイント
├── artifacts/               # テスト実行時の成果物
│   ├── traces/             # トレースファイル
│   └── downloads/          # ダウンロードファイル
├── screenshots/            # スクリーンショット
│   ├── failures/          # 失敗時のスクリーンショット
│   └── reference/         # ビジュアルリグレッション用の参照画像
├── videos/                # テスト実行の録画
│   └── failures/         # 失敗時の動画
├── coverage/             # カバレッジレポート
│   ├── lcov-report/     # HTML形式のカバレッジレポート
│   │   └── index.html
│   ├── coverage.json    # JSON形式のカバレッジデータ
│   └── lcov.info       # LCOV形式のカバレッジデータ
└── feedback/           # フィードバックレポート
    ├── acceptance/     # 受入テスト結果
    │   ├── summary.md     # サマリレポート
    │   ├── failures.md    # 失敗詳細
    │   └── recommendations.md # 改善推奨事項
    └── tdd/           # TDD実行結果
        ├── iteration-*.md # 各イテレーションのレポート
        └── final.md      # 最終レポート
```

## 📊 レポート種別

### 1. Playwright レポート
- **場所**: `playwright-report/index.html`
- **表示方法**: `npx playwright show-report`
- **内容**: テスト結果、スクリーンショット、トレース

### 2. カバレッジレポート
- **場所**: `coverage/lcov-report/index.html`
- **表示方法**: ブラウザで直接開く
- **内容**: 行カバレッジ、分岐カバレッジ、関数カバレッジ

### 3. フィードバックレポート
- **場所**: `feedback/acceptance/summary.md`
- **内容**: 合否判定、失敗分析、修正推奨

## 🔧 メンテナンス

### クリーンアップコマンド
```bash
# すべてのテスト結果をクリア
npm run test:clean

# 古いレポートのみクリア（7日以上前）
npm run test:clean:old
```

### アーカイブ
```bash
# テスト結果をアーカイブ
npm run test:archive
```

## 📝 注意事項

- このディレクトリはGitで管理されません（.gitignoreに追加済み）
- CI/CD環境では自動的にアーティファクトとして保存されます
- ローカル環境では定期的にクリーンアップを推奨