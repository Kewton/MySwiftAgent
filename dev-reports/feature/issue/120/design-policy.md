# 設計方針: myAgentDesk Chat UI拡張 (IME対応・Markdown・会話履歴)

**作成日**: 2025-10-30
**ブランチ**: feature/issue/120
**担当**: Claude Code
**プロジェクト**: myAgentDesk (Svelte/TypeScript フロントエンド)

---

## 📋 要求・要件

### ビジネス要求

expertAgent Phase 1 バックエンド実装（SSE Chat API）に対応するフロントエンドUIを構築し、ユーザーがブラウザ上で以下を実現できるようにする：

1. **自然な日本語入力**: IME（日本語入力システム）を使用した際に、変換中のEnterキーで誤送信しない
2. **リッチな表示**: AIエージェントからの応答をMarkdown形式で表示し、コードブロック・リスト・表などを視覚的に整理
3. **会話履歴の永続化**: OpenWebUI/ChatGPT のようなサイドバー方式で会話を管理し、ブラウザリロード後も履歴を保持

### 機能要件

#### 1. IME対応

- **入力中判定**: 日本語入力の変換中（IME composition中）を検出
- **Enterキー制御**: 変換中のEnterキーは無視し、確定後のEnterキーのみ送信トリガー
- **UI フィードバック**: 変換中は「（変換中）」テキストを表示し、ユーザーに状態を明示

#### 2. Markdown レンダリング

- **対象**: AIエージェント（assistant）のメッセージのみ
- **サポート要素**:
  - 見出し (h1/h2/h3)
  - 強調 (bold/italic)
  - リスト (ul/ol)
  - コードブロック (syntax highlighting)
  - インラインコード
  - 引用 (blockquote)
  - 表 (table)
  - リンク
- **セキュリティ**: XSS攻撃を防ぐため、HTML出力をサニタイズ
- **ダークモード**: ライト/ダークテーマ両対応

#### 3. 会話履歴管理

- **会話単位の管理**: 各会話に一意のIDを付与
- **自動タイトル生成**: 最初のユーザーメッセージから40文字でタイトル自動生成
- **グルーピング**: 会話を日付で分類
  - 今日
  - 昨日
  - 過去7日間
  - それ以前
- **CRUD操作**:
  - Create: 新規会話作成
  - Read: URL パラメータ (`?id=xxx`) で会話を読み込み
  - Update: メッセージ追加、要求状態更新、ジョブ結果保存
  - Delete: 会話削除（確認ダイアログ付き）
- **永続化**: localStorage に自動保存
- **容量管理**: 最大100会話まで保存（古い会話を自動削除）

### 非機能要件

| 項目 | 目標値 | 根拠 |
|------|--------|------|
| **パフォーマンス** | ページロード 1秒以内 | localStorage 読み込みはミリ秒単位 |
| **レスポンシブ性** | メッセージ追加が即座にUI反映 | Svelte Reactive Storeによる自動更新 |
| **セキュリティ** | XSS攻撃耐性 | DOMPurify によるHTML サニタイズ |
| **可用性** | オフライン閲覧可能 | localStorage 使用でサーバー不要 |
| **容量制限** | localStorage 5MB以内 | 会話100件 × 平均メッセージ数50 × 平均文字数200 ≈ 1MB |

---

## 🏗️ アーキテクチャ設計

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                     myAgentDesk (Svelte)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐        │
│  │   Sidebar   │  │  Chat Page  │  │  ChatBubble  │        │
│  │ (会話一覧)   │  │ (メイン画面) │  │ (メッセージ)  │        │
│  └──────┬──────┘  └──────┬──────┘  └───────┬──────┘        │
│         │                │                 │               │
│         └────────────────┼─────────────────┘               │
│                          │                                 │
│                  ┌───────▼────────┐                        │
│                  │ Conversation   │                        │
│                  │    Store       │ ◄────────┐             │
│                  │ (Svelte Store) │          │             │
│                  └───────┬────────┘          │             │
│                          │                   │             │
│                  ┌───────▼────────┐   ┌──────┴──────┐      │
│                  │  localStorage  │   │  Derived    │      │
│                  │   (永続化)      │   │  Stores     │      │
│                  └────────────────┘   └─────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTP (SSE)
                          │
                ┌─────────▼─────────┐
                │  expertAgent API  │
                │  (FastAPI)        │
                │  localhost:8104   │
                └───────────────────┘
```

### データフロー

#### 1. メッセージ送信フロー

```
[User Input (textarea)]
        │
        ├─ IME compositionstart → isComposing = true
        ├─ IME compositionend → isComposing = false
        │
        ▼ Enter key (if !isComposing)
[handleSend()]
        │
        ├─ conversationStore.addMessage(userMsg) → localStorage 自動保存
        │
        ▼ fetch(API)
[SSE Streaming]
        │
        ├─ data: {type: "message"} → conversationStore.updateLastAssistantMessage()
        ├─ data: {type: "requirement_update"} → conversationStore.updateRequirements()
        │
        ▼ Stream complete
[UI Update] (Svelte reactive $:)
        │
        └─ Markdown rendering (ChatBubble)
```

#### 2. 会話履歴ロードフロー

```
[Page Load: /chat?id=xxx]
        │
        ▼ onMount()
[URL Parameter Check]
        │
        ├─ id が存在 → conversationStore.setActive(id)
        └─ id が未存在 → conversationStore.create() → URL 更新
                │
                ▼
        [localStorage から会話をロード]
                │
                ▼ Svelte Reactive Store
        [UI に会話内容を表示]
                │
                ├─ Sidebar: 会話一覧
                ├─ Chat Page: メッセージ履歴
                └─ Requirement Card: 要求状態
```

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| **状態管理** | Svelte Writable Store | シンプルなAPI、自動リアクティブ更新、小規模UIに最適 |
| **派生データ** | Svelte Derived Store | 依存関係の自動追跡、パフォーマンス最適化 |
| **永続化** | localStorage | 5MB容量、ブラウザAPI、サーバー不要、高速読み書き |
| **Markdown解析** | marked (v11.x) | 軽量（~30KB）、GFM対応、カスタマイズ可能 |
| **シンタックスハイライト** | highlight.js (v11.x) | 190言語対応、自動言語検出、テーマ切り替え |
| **HTML サニタイズ** | DOMPurify (v3.x) | XSS防止、信頼性実績（GitHub/MDN採用）、軽量 |
| **ルーティング** | SvelteKit $page Store | ビルトイン、SSR対応、URL パラメータ管理 |
| **ナビゲーション** | SvelteKit goto() | SPA遷移、履歴管理、型安全 |

### ディレクトリ構成

```
myAgentDesk/
├── src/
│   ├── routes/
│   │   ├── chat/
│   │   │   └── +page.svelte        # メインチャットUI (407行)
│   │   └── +layout.svelte          # 全体レイアウト（Chatリンク追加）
│   │
│   └── lib/
│       ├── components/
│       │   ├── Sidebar.svelte      # 会話一覧サイドバー (134行)
│       │   ├── ChatBubble.svelte   # メッセージ表示 (193行)
│       │   ├── Button.svelte       # 共通ボタン
│       │   └── Card.svelte         # 共通カード
│       │
│       └── stores/
│           └── conversations.ts    # 会話管理ストア (338行)
│
├── package.json                    # 依存関係
└── tsconfig.json                   # TypeScript設定
```

---

## 🔍 設計上の決定事項

### 1. IME対応の実装方式

#### 決定内容

**Composition Events を使用**:
- `compositionstart`: IME入力開始時に `isComposing = true`
- `compositionend`: IME入力終了時に `isComposing = false`
- `keydown`: Enterキー検出時に `!isComposing` を条件チェック

#### 検討した代替案

| 案 | メリット | デメリット | 不採用理由 |
|----|---------|-----------|-----------|
| **Composition Events** (採用) | ✅ ブラウザ標準API<br>✅ すべての言語対応<br>✅ 確実な判定 | なし | - |
| isComposing プロパティ | シンプル | ❌ Safari 対応不完全 | クロスブラウザ互換性 |
| キーコード判定 | 軽量 | ❌ 言語依存<br>❌ 将来非推奨 | 保守性の低さ |

#### 実装コード

```typescript
let isComposing = false;

function handleCompositionStart() {
    isComposing = true;
}

function handleCompositionEnd() {
    isComposing = false;
}

function handleKeydown(event: KeyboardEvent) {
    // IME入力中はEnterを無視
    if (event.key === 'Enter' && !event.shiftKey && !isComposing) {
        event.preventDefault();
        handleSend();
    }
}
```

**UI フィードバック**:
```html
<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
    Enter で送信 / Shift + Enter で改行
    {#if isComposing}
        <span class="text-primary-600 dark:text-primary-400">（変換中）</span>
    {/if}
</p>
```

---

### 2. Markdown レンダリング戦略

#### 決定内容

**アシスタントメッセージのみMarkdown対応**:
- ユーザーメッセージ: `whitespace-pre-wrap` でプレーンテキスト表示
- アシスタントメッセージ: `marked` → `DOMPurify` → `@html` レンダリング

#### セキュリティ設計

```typescript
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

// Markdown設定
marked.setOptions({
    highlight: (code, lang) => {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,  // \n → <br>
    gfm: true      // GitHub Flavored Markdown
});

// XSS防止
function renderMarkdown(text: string): string {
    const html = marked(text) as string;
    return DOMPurify.sanitize(html);  // <script>, <iframe>等を除去
}
```

#### スタイリング方針

- **グローバルCSS**: `.markdown-content` クラスで一括管理
- **要素カバレッジ**: 全Markdown要素（h1-h3, p, ul, ol, code, pre, blockquote, table）
- **ダークモード**: `:global(.dark .markdown-content)` で自動切り替え
- **コードブロック**: `highlight.js/styles/github-dark.css` テーマ

---

### 3. 会話履歴の永続化戦略

#### Phase 1: localStorage（採用）

| 項目 | 詳細 |
|------|------|
| **容量** | 5MB (文字列換算) |
| **推定格納数** | 会話100件 × メッセージ50件 × 平均200文字 ≈ 1MB |
| **読み書き速度** | < 1ms（同期API） |
| **データ形式** | JSON (JSON.stringify/parse) |
| **保存タイミング** | Store 更新時に自動保存（subscribe） |

**実装コード**:
```typescript
const STORAGE_KEY = 'myAgentDesk_conversations';
const MAX_CONVERSATIONS = 100;

// 読み込み
function loadFromStorage(): ConversationStoreState {
    if (!browser) return { conversations: [], activeId: null };

    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            const parsed = JSON.parse(stored);
            // 古い会話を削除（最大保存数を超える場合）
            if (parsed.conversations.length > MAX_CONVERSATIONS) {
                parsed.conversations = parsed.conversations
                    .sort((a, b) => b.updatedAt - a.updatedAt)
                    .slice(0, MAX_CONVERSATIONS);
            }
            return parsed;
        }
    } catch (error) {
        console.error('Failed to load conversations:', error);
    }
    return { conversations: [], activeId: null };
}

// 自動保存
subscribe((value) => {
    saveToStorage(value);
});
```

#### Phase 2候補: IndexedDB（将来拡張）

| 項目 | localStorage (Phase 1) | IndexedDB (Phase 2) |
|------|----------------------|---------------------|
| 容量 | 5MB | 無制限（クォータ管理API） |
| 速度 | < 1ms（同期） | 5-10ms（非同期） |
| クエリ | 不可 | インデックス検索可能 |
| 採用タイミング | ✅ 現在 | 会話数が100件を超える場合 |

---

### 4. Conversation Store 設計

#### データ構造

```typescript
export interface Message {
    role: 'user' | 'assistant';
    message: string;
    timestamp: string;
}

export interface RequirementState {
    data_source: string | null;
    process_description: string | null;
    output_format: string | null;
    schedule: string | null;
    completeness: number;  // 0.0 ~ 1.0
}

export interface JobResult {
    job_id: string;
    job_master_id: string;
    status: string;
    message: string;
}

export interface Conversation {
    id: string;                   // Format: conv_${timestamp}_${random}
    title: string;                // 最初のメッセージから自動生成
    createdAt: number;            // Unix timestamp (ms)
    updatedAt: number;            // Unix timestamp (ms)
    messages: Message[];
    requirements: RequirementState;
    jobResult?: JobResult;
}

interface ConversationStoreState {
    conversations: Conversation[];
    activeId: string | null;
}
```

#### Store API設計

| メソッド | 用途 | 副作用 |
|---------|------|--------|
| `create()` | 新規会話作成 | localStorage保存、activeId更新 |
| `setActive(id)` | アクティブ会話変更 | activeId更新のみ |
| `update(id, updates)` | 会話全体更新 | updatedAt更新、localStorage保存 |
| `addMessage(id, message)` | メッセージ追加 | タイトル自動生成、localStorage保存 |
| `updateLastAssistantMessage(id, message)` | ストリーミング更新 | 最後のアシスタントメッセージのみ更新 |
| `updateRequirements(id, requirements)` | 要求状態更新 | localStorage保存 |
| `saveJobResult(id, jobResult)` | ジョブ結果保存 | localStorage保存 |
| `delete(id)` | 会話削除 | localStorage保存、activeId調整 |
| `updateTitle(id, title)` | タイトル変更 | localStorage保存 |
| `clear()` | 全削除 | localStorage完全削除 |

#### Derived Stores（派生ストア）

```typescript
// 1. アクティブな会話を取得
export const activeConversation = derived(
    conversationStore,
    ($store) => $store.conversations.find((c) => c.id === $store.activeId) || null
);

// 2. 会話をソート（最新順）
export const sortedConversations = derived(
    conversationStore,
    ($store) => [...$store.conversations].sort((a, b) => b.updatedAt - a.updatedAt)
);

// 3. 日付グルーピング
export const groupedConversations = derived(
    sortedConversations,
    ($conversations) => {
        const now = Date.now();
        const oneDayMs = 24 * 60 * 60 * 1000;
        const sevenDaysMs = 7 * oneDayMs;

        return {
            today: $conversations.filter(c => now - c.updatedAt < oneDayMs),
            yesterday: $conversations.filter(c => {
                const age = now - c.updatedAt;
                return age >= oneDayMs && age < 2 * oneDayMs;
            }),
            lastSevenDays: $conversations.filter(c => {
                const age = now - c.updatedAt;
                return age >= 2 * oneDayMs && age < sevenDaysMs;
            }),
            older: $conversations.filter(c => now - c.updatedAt >= sevenDaysMs)
        };
    }
);
```

---

### 5. ナビゲーション設計

#### URL パラメータ方式（採用）

**メリット**:
- ✅ ブラウザの戻る/進むボタン対応
- ✅ ブックマーク可能
- ✅ URL共有可能
- ✅ SSR対応（将来拡張）

**実装**:
```typescript
import { page } from '$app/stores';
import { goto } from '$app/navigation';

onMount(() => {
    const id = $page.url.searchParams.get('id');

    if (id) {
        // 既存の会話を選択
        conversationStore.setActive(id);
    } else {
        // 会話が存在しない場合、新規作成
        if (!activeConv) {
            const newConv = conversationStore.create();
            window.history.replaceState({}, '', `/chat?id=${newConv.id}`);
        }
    }
});

// 会話切り替え
function selectConversation(id: string) {
    conversationStore.setActive(id);
    goto(`/chat?id=${id}`);
}
```

#### 検討した代替案

| 案 | メリット | デメリット | 不採用理由 |
|----|---------|-----------|-----------|
| **URL パラメータ** (採用) | ブックマーク可能<br>履歴管理 | URL に会話IDが露出 | - |
| Store のみ | シンプル | ❌ リロード時に状態喪失 | UX 低下 |
| Hash ルーティング | 軽量 | ❌ SSR非対応 | 将来拡張性 |

---

## ✅ 制約条件チェック結果

### コード品質原則

- [x] **SOLID原則**: 遵守
  - **Single Responsibility**:
    - `conversations.ts`: 会話管理のみ
    - `Sidebar.svelte`: 会話一覧表示のみ
    - `ChatBubble.svelte`: メッセージ表示のみ
  - **Open-Closed**:
    - Derived Storeで拡張可能（groupedConversations等）
  - **Liskov Substitution**:
    - Message/RequirementState インターフェース準拠
  - **Interface Segregation**:
    - 各コンポーネントは必要な Store のみ購読
  - **Dependency Inversion**:
    - コンポーネントは Store に依存（具体実装に非依存）

- [x] **KISS原則** (Keep It Simple, Stupid): 遵守
  - localStorage 使用（IndexedDB よりシンプル）
  - Composition Events（複雑なキーコード判定回避）
  - Svelte Reactive Store（Redux等の冗長性回避）

- [x] **YAGNI原則** (You Aren't Gonna Need It): 遵守
  - Phase 1 では localStorage のみ（IndexedDB は将来必要時に追加）
  - キーワードベース要求抽出（LLMベースはPhase 2）
  - シンプルなタイトル生成（編集機能は将来追加）

- [x] **DRY原則** (Don't Repeat Yourself): 遵守
  - `conversations.ts` で会話管理ロジックを一元化
  - `ChatBubble.svelte` でMarkdownレンダリングを共通化
  - Derived Storeで算出ロジックを再利用

### アーキテクチャガイドライン

- [x] `./docs/design/architecture-overview.md`: 準拠
  - フロントエンド層としてmyAgentDeskを配置
  - expertAgent APIとHTTP/SSE通信
  - レイヤー分離（UI/Store/localStorage）

### 設定管理ルール

- [x] **環境変数**: 該当なし（フロントエンドは環境変数不使用）
- [x] **myVault**: 該当なし（APIキー管理はバックエンド側で実施済み）

### 品質担保方針

- [x] **TypeScript型チェック**: エラーゼロ
  - `npm run type-check` 合格
  - 全インターフェース定義済み
  - `any` 型を最小限に抑制

- [x] **ESLint**: エラーゼロ
  - `npm run lint` 合格
  - Svelte推奨設定適用

- [x] **フォーマット**: Prettier適用済み
  - `npm run format` 実行済み

- [ ] **単体テスト**: 未実施（Phase 1範囲外）
  - Phase 2でVitest + Testing Library導入予定

### CI/CD準拠

- [x] **ブランチ命名**: `feature/issue/120` 規約準拠
- [x] **コミットメッセージ**: Conventional Commits準拠予定
  - `feat(myAgentDesk): add chat history persistence with localStorage`
- [x] **PRラベル**: `feature` ラベル付与予定（minor version bump）

### 参照ドキュメント遵守

- [x] **新プロジェクト追加**: 該当なし（既存プロジェクト拡張）
- [x] **GraphAI ワークフロー**: 該当なし（フロントエンド開発）
- [x] **アーキテクチャ概要**: 参照済み
- [x] **開発ガイドライン**: 参照済み

### 違反・要検討項目

**なし** - すべての制約条件を満たしています。

---

## 📊 パフォーマンス見積もり

### localStorage 容量試算

**前提条件**:
- 1会話あたり平均メッセージ数: 50件
- 1メッセージあたり平均文字数: 200文字（日本語・マルチバイト含む）
- JSON オーバーヘッド: 1.2倍

**計算**:
```
100会話 × 50メッセージ × 200文字 × 2byte (UTF-16) × 1.2 (JSON) = 2.4MB
```

**結論**: localStorage 5MB制限内で十分運用可能

### レンダリング速度

| 操作 | 予想時間 | 測定方法 |
|------|---------|---------|
| localStorage 読み込み | < 1ms | `performance.now()` |
| Markdown パース (500文字) | < 5ms | `marked()` 実行時間 |
| DOMPurify サニタイズ | < 2ms | `sanitize()` 実行時間 |
| 会話切り替え | < 10ms | `goto()` + Store更新 |
| メッセージ追加 | < 5ms | Store更新 + localStorage保存 |

---

## 🔒 セキュリティ考慮事項

### XSS（クロスサイトスクリプティング）対策

**脅威**: Markdown内に悪意のある`<script>`タグを挿入

**対策**:
```typescript
import DOMPurify from 'dompurify';

function renderMarkdown(text: string): string {
    const html = marked(text) as string;
    return DOMPurify.sanitize(html);  // <script>, <iframe>, <object>等を削除
}
```

**テストケース**:
```typescript
// Input:  <script>alert('XSS')</script>
// Output: (空文字列 - タグが除去される)

// Input:  <img src=x onerror="alert('XSS')">
// Output: <img src="x"> (onerror属性が除去される)
```

### localStorage の制約

| リスク | 対策 |
|-------|------|
| **5MB制限超過** | 最大100会話で自動削除 |
| **同一オリジン制約** | expertAgent APIは別ドメイン可 |
| **プレーンテキスト保存** | 機密情報（APIキー等）は保存しない |

---

## 🚀 将来拡張（Phase 2候補）

### 1. IndexedDB 移行

**トリガー条件**:
- 会話数が100件を超える
- 検索機能の追加
- オフライン同期機能

**実装方針**:
- `conversations.ts` の内部実装のみ変更
- コンポーネントAPIは互換性維持

### 2. 会話検索機能

- **全文検索**: メッセージ内容でフィルタ
- **タグ機能**: 会話にカスタムタグを付与
- **日付範囲検索**: 期間指定で会話抽出

### 3. エクスポート/インポート

- **JSON エクスポート**: 会話データをダウンロード
- **Markdown エクスポート**: 会話をMarkdownファイルで出力
- **インポート**: 別ブラウザからデータ移行

### 4. AI ベース要求抽出

- **現状**: キーワードベース（Phase 1）
- **拡張**: LLM APIで意図解析（Phase 2）

---

## 📚 技術スタック詳細

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|-----------|------|
| **フレームワーク** | SvelteKit | 2.x | SSR対応SPAフレームワーク |
| **言語** | TypeScript | 5.x | 型安全な開発 |
| **状態管理** | Svelte Stores | Built-in | リアクティブ状態管理 |
| **Markdown** | marked | 11.x | Markdown → HTML変換 |
| **シンタックスハイライト** | highlight.js | 11.x | コードブロック装飾 |
| **セキュリティ** | DOMPurify | 3.x | XSS防止 |
| **スタイリング** | TailwindCSS | 3.x | ユーティリティCSS |
| **ビルドツール** | Vite | 5.x | 高速開発サーバー |

---

## 📝 まとめ

### 実装完了項目

1. ✅ **IME対応**: Composition Events で日本語入力時の誤送信を防止
2. ✅ **Markdown レンダリング**: `marked` + `highlight.js` + `DOMPurify` で安全な表示
3. ✅ **会話履歴管理**: Svelte Store + localStorage で永続化
4. ✅ **サイドバーUI**: OpenWebUI風の会話一覧とグルーピング
5. ✅ **URL ベースナビゲーション**: ブックマーク・履歴管理対応

### 品質指標

| 指標 | 目標 | 実績 | 判定 |
|------|------|------|------|
| TypeScript型チェック | エラーゼロ | ✅ 0件 | ✅ |
| ESLint | エラーゼロ | ✅ 0件 | ✅ |
| コードフォーマット | Prettier適用 | ✅ 適用済み | ✅ |
| ファイル行数 | 適切な分割 | 最大407行 (Chat Page) | ✅ |

### アーキテクチャの強み

- **シンプル**: localStorage + Svelte Store で最小構成
- **拡張性**: IndexedDB/検索機能への移行が容易
- **セキュリティ**: DOMPurify によるXSS防止
- **パフォーマンス**: リアクティブな状態管理で高速UI更新
- **保守性**: SOLID原則に基づく責任分離

---

**承認者**: （ユーザー承認待ち）
**承認日**: YYYY-MM-DD
