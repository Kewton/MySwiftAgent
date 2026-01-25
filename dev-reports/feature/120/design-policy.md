# 設計方針: myAgentDesk リファクタリング

**作成日**: 2025-10-31
**ブランチ**: feature/issue/120
**担当**: Claude Code

---

## 📋 要求・要件

### ビジネス要求
- myAgentDesk の保守性・拡張性を向上させる
- コード品質を CLAUDE.md の基準に準拠させる
- TypeScript 型安全性を強化する
- テストカバレッジを維持・向上させる

### 機能要件
- 既存機能を100%維持（後方互換性）
- 以下の既存機能：
  - ジョブ作成フロー（チャット形式での要求入力）
  - 会話履歴管理（検索・編集・削除）
  - 要求状態の可視化（完全性スコア表示）
  - 多言語対応（日本語・英語）

### 非機能要件
- **保守性**: 単一ファイル489行 → 複数の小さなモジュールに分割
- **型安全性**: TypeScript 型エラー 0件
- **品質**: Linting エラー 0件、フォーマット準拠
- **テスト**: カバレッジ維持（現状: 42 tests passing）
- **アクセシビリティ**: A11y警告の解消

---

## 🏗️ アーキテクチャ設計

### 現状の問題点

#### 1. 単一責任原則（SRP）違反
**問題**: `src/routes/create_job/+page.svelte` が489行で、以下の責務を全て持つ
- UI表示（チャット、サイドバー、要求カード）
- 状態管理（メッセージ、要求、ストリーミング）
- APIコール（チャット、ジョブ作成）
- イベントハンドリング（送信、IME、スクロール）

**影響**:
- 変更時の影響範囲が広い
- テストが困難
- コードレビューの負荷が高い

#### 2. 型安全性の問題
**問題**: Button コンポーネントに `class` プロップが型定義されていない
```svelte
<!-- エラー箇所: src/routes/create_job/+page.svelte:401 -->
<Button
  variant="primary"
  disabled={requirements.completeness < 0.8}
  class="w-full"  <!-- ← 型エラー -->
>
```

**影響**: TypeScript のコンパイルエラー、IDE の型チェック失敗

#### 3. アクセシビリティ警告
**問題**:
- `autofocus` 属性の使用（キーボードナビゲーション妨害）
- マウスイベントハンドラーに ARIA ロール不足

#### 4. テストカバレッジ不足
**現状**:
- コンポーネント単体テスト: 4ファイル、42テスト（全てpass）
- ページレベルテスト: 0件
- カバレッジレポート: 未測定

**問題**:
- create_job ページ（489行）のテストが存在しない
- ビジネスロジックのテストがない

### リファクタリング方針

#### 戦略: 段階的リファクタリング（Strangler Fig Pattern）

既存機能を破壊せず、段階的に改善する方針を採用

**原則**:
1. ✅ **後方互換性維持**: 既存の API・機能は変更しない
2. ✅ **テストファースト**: リファクタリング前にテストを追加
3. ✅ **小さく頻繁にコミット**: 各Phase完了時にコミット
4. ✅ **型安全性優先**: TypeScript の恩恵を最大化

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| フレームワーク | SvelteKit (継続) | 既存プロジェクトとの整合性 |
| 型システム | TypeScript (強化) | 型安全性の向上 |
| テストフレームワーク | Vitest (継続) | 既存のテスト資産を活用 |
| Linter | ESLint + Prettier (継続) | CLAUDE.md の品質基準に準拠 |
| コンポーネント分割 | Atomic Design 簡易版 | 保守性・再利用性向上 |

### 新しいディレクトリ構成

```
src/
├── lib/
│   ├── components/
│   │   ├── atoms/          # 最小単位（Button, Input等）
│   │   │   ├── Button.svelte
│   │   │   ├── Button.test.ts
│   │   │   └── ...
│   │   ├── molecules/      # 複合コンポーネント
│   │   │   ├── ChatInput.svelte
│   │   │   ├── RequirementCard.svelte
│   │   │   └── ...
│   │   ├── organisms/      # 複雑なコンポーネント
│   │   │   ├── ChatPanel.svelte
│   │   │   ├── RequirementPanel.svelte
│   │   │   └── ...
│   │   └── sidebar/        # サイドバー専用（既存）
│   │       └── ...
│   ├── services/           # ビジネスロジック（新規）
│   │   ├── chat-api.ts
│   │   ├── job-api.ts
│   │   └── ...
│   ├── stores/             # 状態管理（既存）
│   │   ├── conversations.ts
│   │   ├── locale.ts
│   │   └── ...
│   └── utils/              # ユーティリティ（既存）
│       ├── markdown.ts
│       └── ...
├── routes/
│   ├── create_job/
│   │   ├── +page.svelte      # シンプルな構成（< 150行目標）
│   │   └── +page.test.ts     # ページレベルテスト（新規）
│   └── ...
└── ...
```

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: リファクタリング後に遵守
  - Single Responsibility Principle: ファイルサイズ削減、責務分離
  - Open-Closed Principle: コンポーネント設計で拡張性確保
  - Liskov Substitution Principle: 型安全性で保証
  - Interface Segregation Principle: Props 最小化
  - Dependency Inversion Principle: サービス層導入
- [x] **KISS原則**: 過度な抽象化を避け、シンプルに
- [x] **YAGNI原則**: 必要最小限のリファクタリング
- [x] **DRY原則**: 重複コードの共通化（特にAPIコール）

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠（TypeScript フロントエンド）
- [x] レイヤー分離: Presentation（UI） / Service（API） / Store（状態）

### 設定管理ルール
- [x] 環境変数: API_BASE を環境変数化（将来対応）
- [ ] **要検討**: myVault連携は不要（フロントエンドのみ）

### 品質担保方針
- [ ] **現状課題**: TypeScript プロジェクトのため、Python 品質基準は適用外
- [x] TypeScript 型チェック: エラー 0件 目標
- [x] ESLint: エラー 0件 目標
- [x] Prettier: 全ファイル適用
- [ ] **テストカバレッジ**: 目標 80%以上（新規設定）

### CI/CD準拠
- [x] PRラベル: `refactor` ラベルを付与予定
- [x] コミットメッセージ: Conventional Commits 規約準拠
- [x] pre-push チェック: TypeScript プロジェクト用のチェックスクリプト

### 参照ドキュメント遵守
- [x] CLAUDE.md: 開発ルール遵守
- [ ] NEW_PROJECT_SETUP.md: 既存プロジェクトのため不要
- [ ] GRAPHAI_WORKFLOW_GENERATION_RULES.md: 関連なし

### 違反・要検討項目

#### 1. テストカバレッジ目標の新規設定
**問題**: CLAUDE.md には Python プロジェクトのカバレッジ基準（90%/50%）があるが、TypeScript プロジェクトの基準が未定義

**提案**: TypeScript プロジェクト用の品質基準を定義
- **単体テスト**: 80%以上（コンポーネント・サービス層）
- **統合テスト**: 60%以上（ページレベル）

**代替案**:
1. ✅ **新基準を採用** (推奨) - TypeScript 専用基準を CLAUDE.md に追記
2. ❌ **Python基準を流用** - 言語特性が異なるため不適切
3. ⏸️ **カバレッジ未測定** - 品質担保の観点から推奨しない

---

## 📝 設計上の決定事項

### 1. Button コンポーネントの `class` プロップ対応
**決定**: `$$restProps` を使用してカスタムクラスを受け入れる

**理由**:
- Svelte のベストプラクティス
- 型安全性を保ちながら柔軟性を確保
- 他のコンポーネントでも同様のパターンを適用可能

**実装方針**:
```svelte
<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'danger' | 'ghost' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let disabled = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';

  // カスタムクラスを受け入れる
  let className = '';
  export { className as class };
</script>

<button
  {type}
  {disabled}
  class="{variantClasses[variant]} {sizeClasses[size]} {className}"
  on:click
>
  <slot />
</button>
```

### 2. create_job ページの分割方針
**決定**: 以下の3つのコンポーネントに分割
1. **ChatPanel**: チャット表示・入力（200行目標）
2. **RequirementPanel**: 要求状態カード（100行目標）
3. **CreateJobPage**: 全体統合（< 150行目標）

**理由**:
- 単一責任原則の遵守
- テストの容易性
- 並行開発の可能性

### 3. APIコールのサービス層移行
**決定**: `lib/services/` ディレクトリに API クライアントを作成

**対象API**:
- `chat-api.ts`: チャットストリーミング
- `job-api.ts`: ジョブ作成

**理由**:
- ビジネスロジックとUIの分離
- APIコールのテスト容易性
- エラーハンドリングの一元化

### 4. A11y 警告の解消方針
**決定**:
- `autofocus`: 削除し、UX的に必要な場合のみ使用
- ARIA ロール: `role="button"` を追加

**理由**: アクセシビリティ基準の遵守

---

## 🚨 リスク管理

### リスク1: 既存機能の破壊
**対策**:
- リファクタリング前にE2Eテスト追加
- 各Phase完了時に手動動作確認
- ロールバック計画（git revert）

### リスク2: スコープクリープ
**対策**:
- Phase定義を厳密に
- 新機能追加は別Issue化
- レビュー時の機能追加指摘は次フェーズへ

### リスク3: テスト追加の工数増
**対策**:
- 最小限のテストケースに絞る
- カバレッジ目標を段階的に（Phase 1: 60% → Phase 3: 80%）

---

## 📅 次のステップ

1. ✅ 設計方針レビュー（本ドキュメント）
2. 📝 作業計画立案（work-plan.md）
3. 🚀 Phase 1 実装開始
