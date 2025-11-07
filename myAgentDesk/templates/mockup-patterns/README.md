# UIモックアップパターンテンプレート

このディレクトリには、UIモックアップ生成時に使用するテンプレートが格納されています。

## 📁 構造

```
mockup-patterns/
├── README.md              # このファイル
├── base-layout.svelte     # 共通レイアウトテンプレート
├── pattern-a.svelte       # パターンA: シンプル・ミニマル
├── pattern-b.svelte       # パターンB: 標準・バランス型
├── pattern-c.svelte       # パターンC: リッチ・高機能
├── pattern-d.svelte       # パターンD: 革新的・実験的
└── comparison.svelte      # 比較ビューテンプレート
```

## 🎨 パターン説明

### パターンA: シンプル・ミニマル

- **特徴**: 必要最小限の機能、クリーンなUI
- **対象**: MVP、モバイルファースト
- **実装**: 基本的なHTML要素、最小限のスタイル

### パターンB: 標準・バランス型

- **特徴**: 標準的な機能セット、使いやすさ重視
- **対象**: 一般ユーザー、長期運用
- **実装**: 一般的UIコンポーネント、標準的なレイアウト

### パターンC: リッチ・高機能

- **特徴**: 全機能搭載、高度なカスタマイズ
- **対象**: パワーユーザー、エンタープライズ
- **実装**: 高度なコンポーネント、複雑なインタラクション

### パターンD: 革新的・実験的

- **特徴**: 新しいUXパターン、AIアシスト
- **対象**: 早期採用者、差別化重視
- **実装**: 実験的UI、最新技術の活用

## 🚀 使用方法

1. **スキル実行時**

   ```bash
   /ui-mockup [Feature番号]
   ```

2. **生成される構造**

   ```
   src/routes/(preview)/mockups/feature-[番号]/
   ├── pattern-a/+page.svelte
   ├── pattern-b/+page.svelte
   ├── pattern-c/+page.svelte
   ├── pattern-d/+page.svelte
   └── comparison/+page.svelte
   ```

3. **アクセス方法**
   ```
   開発サーバー起動: npm run dev
   プレビュー: http://localhost:5173/mockups/feature-[番号]/pattern-[a-d]
   比較: http://localhost:5173/mockups/feature-[番号]/comparison
   ```

## 📝 カスタマイズ

各パターンテンプレートは以下の変数を受け取ります：

- `featureNumber`: Feature番号
- `featureName`: Feature名
- `requirements`: UI要件
- `mockData`: テスト用データ

## 🔧 開発ガイドライン

1. **レスポンシブ対応**: すべてのパターンはモバイル〜デスクトップ対応
2. **アクセシビリティ**: WCAG 2.1 AA準拠
3. **パフォーマンス**: Lighthouse スコア90以上目標
4. **ブラウザ対応**: Chrome, Firefox, Safari, Edge最新版

## 📊 選定プロセス

1. 4パターンを生成
2. プレビュー環境で確認
3. 比較ビューで並べて評価
4. 1パターンを選定
5. 選定パターンをベースに本実装

## ✅ チェックリスト

モックアップ作成時の確認事項：

- [ ] 4パターンすべて生成されている
- [ ] インタラクティブに動作する
- [ ] レスポンシブデザイン対応
- [ ] アクセシビリティ対応
- [ ] モックデータで動作確認済み
- [ ] 比較ビューが機能する
