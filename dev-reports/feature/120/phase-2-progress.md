# Phase 2 作業状況: myAgentDesk リファクタリング

**Phase名**: サービス層の導入とAPIロジックの分離
**作業日**: 2025-10-31
**所要時間**: 1.0時間

---

## 📝 実装内容

### 1. サービス層ディレクトリ構造の作成

**新規作成**:
```
myAgentDesk/src/lib/services/
├── types.ts           # 型定義
├── chat-api.ts        # チャットAPI サービス
├── job-api.ts         # ジョブ作成API サービス
└── index.ts           # エクスポート集約
```

### 2. 型定義ファイル (types.ts)

**実装内容**:
- Message, RequirementState, JobResult インターフェース定義
- Chat API リクエスト/レスポンス型定義
- Job API リクエスト/レスポンス型定義
- ServiceError カスタムエラークラス

**設計判断**:
- `ServiceError` に `statusCode` と `originalError` を含めることで、エラーハンドリングを詳細化
- Chat API のストリームイベントを Union 型で表現し、型安全性を向上

### 3. Chat API サービス (chat-api.ts)

**実装内容**:
```typescript
export async function streamChatRequirementDefinition(
  conversationId: string,
  userMessage: string,
  previousMessages: Message[],
  currentRequirements: RequirementState,
  onMessage: (content: string) => void,
  onRequirementUpdate: (requirements: RequirementState) => void
): Promise<void>
```

**特徴**:
- SSE ストリーミング処理のカプセル化
- コールバック関数でイベント通知（メッセージチャンク、要求状態更新）
- エラー発生時は ServiceError をスロー
- try-catch によるエラーハンドリングの集約

**抽出前の問題**:
- create_job ページに SSE 処理ロジック（約70行）が直接記述
- ストリーム解析、JSON パース、エラーハンドリングが混在

**抽出後の改善**:
- UI ロジックと API ロジックの完全分離
- テスト容易性の向上（モック化が容易）
- 再利用可能な API クライアント

### 4. Job API サービス (job-api.ts)

**実装内容**:
```typescript
export async function createJob(
  conversationId: string,
  requirements: RequirementState
): Promise<JobCreationResponse>
```

**特徴**:
- JSON レスポンスパース処理のカプセル化
- エラーレスポンスの統一的な処理
- HTTP ステータスコードを ServiceError に含める

**抽出前の問題**:
- create_job ページに fetch 処理（約40行）が直接記述
- エラーハンドリングの重複

**抽出後の改善**:
- ビジネスロジックの分離
- エラー処理の一元化
- 再利用可能な API クライアント

### 5. create_job ページのリファクタリング

**変更内容**:
```typescript
// Before: API_BASE 定義とfetch処理（約110行）
const API_BASE = 'http://localhost:8104/aiagent-api/v1';
// ... 直接 fetch を呼び出し

// After: サービスのimportと呼び出し（約60行）
import { streamChatRequirementDefinition, createJob, ServiceError } from '$lib/services';
// ... サービス関数を呼び出し
```

**削減内容**:
- `handleSend()`: 70行 → 49行（21行削減、-30%）
- `handleCreateJob()`: 40行 → 27行（13行削減、-33%）
- 全体: 489行 → 約450行（約40行削減、-8%）

**改善点**:
1. API 呼び出しロジックの完全分離
2. エラーハンドリングの簡潔化（ServiceError の活用）
3. UIロジックの明確化（メッセージ管理、スクロール制御のみ）

---

## 🧪 テスト実装

### 1. Chat API サービステスト (chat-api.test.ts)

**テストケース数**: 6件

| No. | テストケース | 目的 |
|-----|------------|------|
| 1 | should successfully stream messages | メッセージストリーミング成功パス |
| 2 | should handle requirement updates | 要求状態更新イベントの処理 |
| 3 | should throw ServiceError on network failure | ネットワークエラー時のエラーハンドリング |
| 4 | should throw ServiceError on HTTP error | HTTP エラーレスポンスの処理 |
| 5 | should throw ServiceError when body is not readable | ストリームボディなしのエラー処理 |
| 6 | should handle invalid JSON in stream | 不正JSONのエラー処理 |

**モック戦略**:
- `fetch` をグローバルにモック
- `ReadableStream` の `getReader()` をモック
- SSE データストリームをシミュレート

### 2. Job API サービステスト (job-api.test.ts)

**テストケース数**: 6件

| No. | テストケース | 目的 |
|-----|------------|------|
| 1 | should successfully create a job | ジョブ作成成功パス |
| 2 | should throw ServiceError on network failure | ネットワークエラー時のエラーハンドリング |
| 3 | should throw ServiceError on HTTP 400 error | バリデーションエラーの処理 |
| 4 | should throw ServiceError on HTTP 500 error with unknown detail | 詳細なしエラーの処理 |
| 5 | should throw ServiceError when JSON parsing fails | JSONパースエラーの処理 |
| 6 | should include status code in ServiceError | エラーオブジェクトのstatusCode検証 |

**カバレッジ目標**: 80%以上
- **実績**: 新規サービスファイル全行カバー

---

## 🐛 発生した課題

| 課題 | 原因 | 解決策 | 状態 |
|------|------|-------|------|
| Prettier フォーマット警告 | 新規作成ファイルがフォーマット前 | `npm run format` 実行 | 解決済 ✅ |
| chat-api.test.ts の1テスト失敗 | `rejects.toThrow()` の二重呼び出し | try-catch 構文に変更 | 解決済 ✅ |

---

## 💡 技術的決定事項

### 1. サービス層の設計パターン

**決定**: Repository パターンではなく、シンプルな関数ベースサービスを採用

**理由**:
| パターン | メリット | デメリット | 採用 |
|---------|---------|-----------|------|
| Repository パターン | DI 対応、テスト容易性 | 過剰設計、学習コスト高 | ❌ |
| クラスベースサービス | 状態管理、拡張性 | 冗長、Svelte との相性 | ❌ |
| **関数ベースサービス** | **シンプル、型安全、ツリーシェイク対応** | 状態管理が困難（今回は不要） | ✅ |

**根拠**:
- 現在の要件ではステートレスな API クライアントで十分（YAGNI原則）
- Svelte のリアクティブ性と関数型アプローチの相性が良い
- 将来的にクラス化が必要になった場合も、関数を内部で呼び出せば移行容易

### 2. エラーハンドリング戦略

**決定**: カスタムエラークラス（ServiceError）の導入

**実装**:
```typescript
export class ServiceError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly originalError?: unknown
  ) {
    super(message);
    this.name = 'ServiceError';
  }
}
```

**メリット**:
- エラー種別の判別が容易（`error instanceof ServiceError`）
- HTTP ステータスコードの保持により、UI側で適切なエラー表示が可能
- オリジナルエラーの保持によりデバッグが容易

### 3. テスト戦略

**決定**: fetch のグローバルモックを使用

**代替案との比較**:
| 案 | メリット | デメリット | 採用 |
|----|---------|-----------|------|
| `fetch` グローバルモック | シンプル、vitest標準 | グローバル汚染 | ✅ |
| `msw` (Mock Service Worker) | 実環境に近い | 設定複雑、オーバースペック | ❌ |
| 依存性注入 (DI) | テスト容易性最高 | 過剰設計、コード複雑化 | ❌ |

**理由**: 現状のシンプルなサービス層では、グローバルモックで十分（KISS原則）

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守（単一責任: サービス層は API 呼び出しのみ）
- [x] **KISS原則**: 遵守（シンプルな関数ベース設計）
- [x] **YAGNI原則**: 遵守（DI や Repository パターンは不採用）
- [x] **DRY原則**: 遵守（API ロジックの重複を排除）

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠（レイヤー分離を実現）

### 品質担保方針
- [x] TypeScript 型チェック: **エラー 0件** ✅
- [x] ESLint: **エラー 0件** ✅
- [x] Prettier: **全ファイル適用済み** ✅
- [x] テスト: **54 tests passing (12件新規追加)** ✅
- [x] ビルド: **成功** ✅
- [x] サービス層カバレッジ: **100%** ✅（全行カバー）

### CI/CD準拠
- [x] コミットメッセージ: Conventional Commits 規約準拠予定
- [x] PRラベル: `refactor` 付与予定

### 違反・要検討項目
**なし** - すべての制約条件を満たしています。

---

## 📊 進捗状況

- **Phase 2 タスク完了率**: 100% (6/6タスク完了)
- **全体進捗**: 40% (Phase 2/5完了)

### 完了タスク
- [x] `src/lib/services/` ディレクトリ作成
- [x] `chat-api.ts` 実装（チャットストリーミングAPI）
- [x] `job-api.ts` 実装（ジョブ作成API）
- [x] `create_job` ページをサービス層を使うよう修正
- [x] サービス層のテスト追加（12テスト、カバレッジ100%）
- [x] テスト実行と品質確認

---

## 🎯 品質指標

| 指標 | 目標 | 実績 | 判定 |
|------|------|------|------|
| TypeScript型チェック | エラーゼロ | ✅ 0件 | ✅ |
| ESLint | エラーゼロ | ✅ 0件 | ✅ |
| Prettier | 全ファイル適用 | ✅ 適用済み | ✅ |
| テスト | 全テストpass | ✅ 54/54 (新規+12) | ✅ |
| ビルド | 成功 | ✅ 成功 | ✅ |
| サービス層カバレッジ | 80%以上 | ✅ 100% | ✅ |
| コード削減 | - | ✅ 約40行削減 | ✅ |

---

## 🔍 コード品質改善の定量評価

### 1. ページサイズ削減
- **create_job/+page.svelte**: 489行 → 約450行（-8%）

### 2. 関数の複雑度削減
- **handleSend()**: 70行 → 49行（-30%）
- **handleCreateJob()**: 40行 → 27行（-33%）

### 3. 責務の明確化
- **UI層**: メッセージ管理、スクロール制御、ユーザー入力処理
- **サービス層**: API 呼び出し、エラーハンドリング、データ変換

### 4. テスト容易性の向上
- **Before**: UI コンポーネントテストで API モック化が必要
- **After**: サービス層を独立してテスト可能（12テスト追加）

---

## 📚 次のステップ

**Phase 3**: コンポーネント分割とページの軽量化 (1.5日)

**予定タスク**:
1. Atomic Design に基づくコンポーネント分割
   - RequirementCard コンポーネント抽出
   - ChatContainer コンポーネント抽出
   - MessageInput コンポーネント抽出
2. 各コンポーネントのテスト追加
3. create_job ページの最終リファクタリング（目標: 300行以下）

**承認待ち**: Phase 3 の実装を開始するか確認
