# 要件定義書: Issue #192 - Create JobとMLOps Chat UIの統合

## 現状調査サマリ

### 対象プロジェクト
- **プロジェクト名**: myAgentDesk（SvelteKit フロントエンド）
- **関連モジュール**:
  - `src/routes/create_job/+page.svelte` - Create Job画面
  - `src/routes/mlops/chat/+page.svelte` - MLOps Chat画面
  - `src/lib/mlops/components/` - MLOpsコンポーネント群

### 既存の類似機能

| 機能 | 場所 | 概要 |
|------|------|------|
| **CandidateSelector** | `src/lib/mlops/components/CandidateSelector.svelte` | 複数候補から1つを選択するUI（キーボード操作対応） |
| **FeedbackModal** | `src/lib/mlops/components/FeedbackModal.svelte` | 4段階評価フォーム（フォーカストラップ対応） |
| **FeedbackForm** | `src/lib/mlops/components/FeedbackForm.svelte` | ScoreSlider×4 + コメント欄 |
| **MLOps API Client** | `src/lib/mlops/api/client.ts` | selectCandidate(), submitFeedback() |
| **Chat API** | `src/lib/services/chat-api.ts` | streamChatRequirementDefinition() (SSE) |

### 使用されている設計パターン

| パターン | 使用箇所 | 目的 |
|----------|---------|------|
| **イベントディスパッチ** | CandidateSelector, FeedbackModal | 親コンポーネントへの通知 |
| **Svelte Store** | conversationStore, chatSession | グローバル状態管理 |
| **localStorage永続化** | Create Job画面 | ジョブ作成状態の復帰 |
| **SSEストリーミング** | chat-api.ts | リアルタイムLLM応答 |
| **ポーリング** | Create Job画面 | ジョブ状態監視（5秒間隔） |

### 参照したドキュメント
- `myAgentDesk/README.md` - プロジェクト構造、API連携仕様
- `docs/arch/service-dependencies.md` - サービス間依存関係

### 制約事項
1. **既存コンポーネントの再利用**: MLOpsコンポーネントは再利用可能な形で実装済み
2. **API互換性**: expertAgentのMLOps API（/chat/select-candidate, /chat/feedback）は実装済み
3. **アクセシビリティ**: 既存コンポーネントはARIA対応・キーボード操作対応済み

---

## ユーザーストーリー

```
As a 管理者/ユーザー
I want to Create Job画面でLLMチャット後に候補選択とフィードバック送信を完結させたい
So that 画面遷移なしでシームレスなワークフローを実現し、MLOpsメトリクス収集を効率化できる
```

### 背景

現在のUI実装では以下の問題がある：

| 画面 | 機能 | 問題 |
|------|------|------|
| Create Job (`/create_job`) | 実際のLLMチャット | 候補選択・フィードバックUIがない |
| MLOps Chat (`/mlops/chat`) | 候補選択・フィードバック | デモデータのみ、実際のチャットと連携していない |

**結果**: ユーザー導線が分断され、一連のワークフローとして完結しない。

---

## 受入条件（Acceptance Criteria）

### AC-1: Create Job画面での候補選択UI表示

```gherkin
Given ユーザーがCreate Job画面でLLMチャットを実行している
When LLMが複数候補を生成した場合
Then CandidateSelectorコンポーネントが表示される
And 各候補のラベル、説明、信頼度、要件プレビューが表示される
And キーボード操作（Arrow Up/Down, Enter）で選択可能である
```

### AC-2: 候補選択後のフィードバック送信

```gherkin
Given ユーザーがCandidateSelectorで候補を選択・確定した
When 候補が確定された
Then FeedbackModalが表示される
And 4段階評価（要件明確さ、解釈精度、応答有用性、全体満足度）が入力可能
And コメント欄に自由コメントを入力可能
And 送信ボタンでフィードバックがMLOps APIに送信される
```

### AC-3: フィードバックのMLOps Dashboard反映

```gherkin
Given フィードバックが送信された
When MLOps Dashboard（/mlops/dashboard）を確認した
Then 送信したフィードバックがメトリクスに反映されている
And Diagnostics画面で会話履歴が確認できる
```

### AC-4: 会話IDの連携

```gherkin
Given Create Job画面でチャットが進行している
When 候補選択・フィードバック送信を実行した
Then 同一の会話ID（conversation_id）がMLOps APIに連携される
And Diagnostics画面で会話履歴として紐付けられる
```

### AC-5: UIの一貫性維持

```gherkin
Given Create Job画面に候補選択UIが統合された
When 既存のジョブ作成ワークフローを実行した
Then 既存機能（チャット、要件抽出、ジョブ作成モーダル、スライド表示）が正常に動作する
And デザインの一貫性が保たれている（Tailwind CSS、ダークモード対応）
```

---

## 機能要件

### Must Have（必須機能）

| ID | 機能 | 詳細 |
|----|------|------|
| F-1 | CandidateSelector統合 | Create Job画面にCandidateSelectorコンポーネントを追加 |
| F-2 | FeedbackModal統合 | Create Job画面にFeedbackModalコンポーネントを追加 |
| F-3 | LLMレスポンスパーサー | LLMレスポンスから候補データ（Candidate[]）を抽出するパーサー実装 |
| F-4 | 会話ID連携 | chatSessionのconversation_idをMLOps APIに連携 |
| F-5 | 状態管理 | 候補選択状態、フィードバック送信状態の管理 |
| F-6 | エラーハンドリング | API呼び出し失敗時のエラー表示・リトライUI |

### Nice to Have（あると良い機能）

| ID | 機能 | 詳細 |
|----|------|------|
| N-1 | 候補選択のアニメーション | 候補選択時のスムーズなトランジション |
| N-2 | フィードバック送信後の確認UI | 送信成功時のトースト通知 |
| N-3 | 候補比較ビュー | 複数候補を横並びで比較表示 |

### Future Enhancement（将来的な拡張）

| ID | 機能 | 詳細 |
|----|------|------|
| FE-1 | 候補の編集機能 | 選択した候補の要件を手動編集 |
| FE-2 | フィードバック履歴表示 | 過去のフィードバック一覧をCreate Job画面で確認 |
| FE-3 | A/Bテスト統合 | 候補生成アルゴリズムのA/Bテスト結果表示 |

---

## 非機能要件

### パフォーマンス要件

| 項目 | 目標値 |
|------|--------|
| 候補選択UIの表示 | LLM応答後 100ms以内 |
| フィードバック送信 | 500ms以内でAPI応答 |
| UI応答性 | 60fps維持（スクロール、アニメーション） |

### セキュリティ要件

| 項目 | 詳細 |
|------|------|
| 入力バリデーション | フィードバックコメントのXSS対策（既存のsanitize処理を適用） |
| 会話ID | UUIDv4形式、推測不可能 |

### ユーザビリティ要件

| 項目 | 詳細 |
|------|------|
| アクセシビリティ | 既存コンポーネントのARIA対応を維持 |
| キーボード操作 | Tab/Arrow/Enter/Escapeでの操作対応 |
| レスポンシブ | モバイル表示対応（既存のレスポンシブデザイン維持） |
| ダークモード | 既存のダークモードテーマ対応 |

### 互換性要件

| 項目 | 詳細 |
|------|------|
| ブラウザ | Chrome, Firefox, Safari, Edge（最新2バージョン） |
| Node.js | 20.x以上 |
| 既存機能 | Create Job画面の既存機能に影響を与えない |

---

## 技術的制約

### 使用する技術スタック

| 項目 | 技術 | 備考 |
|------|------|------|
| フレームワーク | SvelteKit 2.5.0 | 既存スタック |
| 言語 | TypeScript 5.3.3 | 既存スタック |
| スタイリング | Tailwind CSS 3.4.0 | 既存スタック |
| 状態管理 | Svelte Store | 既存パターン |
| テスト | Vitest + Playwright | 既存スタック |

### 既存システムとの連携

| 連携先 | API | 備考 |
|--------|-----|------|
| expertAgent | POST /chat/select-candidate | 候補選択 |
| expertAgent | POST /chat/feedback | フィードバック送信 |
| expertAgent | GET /observability/requirement-definition-metrics | メトリクス取得 |
| expertAgent | GET /chat/diagnostics/{conversationId} | 会話診断情報 |

### データ形式

#### Candidate型（既存）
```typescript
interface Candidate {
  id: string;
  label: string;
  description: string;
  requirements: RequirementState;
  confidence: number;
}
```

#### FeedbackScores型（既存）
```typescript
interface FeedbackScores {
  requirement_clarity?: number;        // 1-5
  interpretation_accuracy?: number;    // 1-5
  response_helpfulness?: number;       // 1-5
  overall_satisfaction?: number;       // 1-5
  comment?: string;
}
```

---

## リスクと対策

### 技術的リスク

| リスク | 発生確率 | 影響 | 対策 |
|--------|---------|------|------|
| LLMレスポンス形式のばらつき | 高 | 候補パースが失敗 | 堅牢なパーサー実装、フォールバック処理 |
| 既存機能へのリグレッション | 中 | ジョブ作成が動作しない | E2Eテストの追加、リグレッションテスト |
| コンポーネント間の状態競合 | 低 | UI不整合 | 状態管理の一元化、Svelte Storeの活用 |

### ビジネスリスク

| リスク | 発生確率 | 影響 | 対策 |
|--------|---------|------|------|
| UX複雑化 | 中 | ユーザー離脱 | 段階的なUI表示、ツールチップ追加 |
| 学習コスト増加 | 低 | 導入遅延 | ドキュメント整備、チュートリアル |

---

## 実装計画

### 推奨アプローチ: 案A（Create Job画面にMLOps UIを統合）

**理由**:
1. 既存のCreate Jobワークフローを維持
2. MLOpsコンポーネントは再利用可能な形で実装済み
3. 画面遷移なしでシームレスなユーザー体験

### タスク分解

1. [ ] Create Job画面の現状分析
2. [ ] LLMレスポンスから候補データを抽出するパーサー実装
3. [ ] CandidateSelectorコンポーネントをCreate Jobに統合
4. [ ] FeedbackModalをCreate Jobに統合
5. [ ] 会話IDをMLOps APIに連携
6. [ ] 状態管理の実装（候補選択状態、フィードバック送信状態）
7. [ ] エラーハンドリングの実装
8. [ ] 単体テストの追加（コンポーネント）
9. [ ] E2Eテストの追加
10. [ ] ドキュメント更新

### 見積

| フェーズ | 工数 |
|---------|------|
| 調査・設計 | 0.5日 |
| 実装 | 2日 |
| テスト | 1日 |
| ドキュメント | 0.5日 |
| **合計** | **4日** |

---

## 参照ドキュメント

| ドキュメント | 関連する内容 |
|--------------|-------------|
| `myAgentDesk/README.md` | プロジェクト構造、API連携仕様、コンポーネントアーキテクチャ |
| `docs/arch/service-dependencies.md` | サービス間依存関係 |
| `expertAgent/docs/API_REFERENCE.md` | MLOps API仕様（/chat/select-candidate, /chat/feedback） |
| `dev-reports/feature/issue/152/prompts-api-design.md` | 親Issue設計方針 |

---

## 関連Issue

| Issue | タイトル | 関係 |
|-------|---------|------|
| #152 | 要件定義エージェントへのMLOpsの導入 | 親Issue |
| #170 | UI実装（フロントエンド統合） | 関連Issue |
| #191 | プロンプト管理API実装 | 兄弟Issue |

---

*作成日: 2025-12-10*
*Issue: #192*
*ステータス: 要件定義完了*
