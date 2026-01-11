# Architecture Review: Issue #348 - TaskFlow Engine

## Executive Summary

| 項目 | 評価 |
|------|------|
| **総合評価** | **A** (Approved with Minor Recommendations) |
| **設計品質** | 4.2 / 5.0 |
| **セキュリティ** | 4.0 / 5.0 |
| **既存システム整合性** | 4.5 / 5.0 |
| **実装可能性** | 4.3 / 5.0 |
| **保守性** | 4.0 / 5.0 |

**判定**: 設計は承認可能。いくつかの改善推奨事項を実装フェーズで対応することを推奨。

---

## 1. SOLID原則準拠評価

### 1.1 Single Responsibility Principle (SRP) - 単一責任原則

| コンポーネント | 評価 | コメント |
|--------------|------|---------|
| BaseNode | ✅ 良好 | ノード実行の共通処理に集中 |
| ApiRestNode | ✅ 良好 | REST API呼び出しのみに責務限定 |
| CodeJsNode | ✅ 良好 | JavaScript実行のみに責務限定 |
| TransformNode | ⚠️ 要注意 | 4つのmode (template/concat/map/merge) が混在 |
| ContextManager | ✅ 良好 | コンテキスト管理のみ |
| SchemaValidator | ✅ 良好 | スキーマ検証のみ |
| StepExecutor | ⚠️ 要注意 | 直列・並列両方を処理 |

**改善提案 (Should Fix)**:
- `TransformNode` の各modeを個別クラスに分離（`TemplateTransformNode`, `ConcatTransformNode` 等）
- `StepExecutor` を `SequentialExecutor` と `ParallelExecutor` に分離（既に設計図では分離されているが型定義と齟齬）

### 1.2 Open/Closed Principle (OCP) - 開放/閉鎖原則

| 評価対象 | 評価 | コメント |
|---------|------|---------|
| ノード種別追加 | ✅ 良好 | BaseNodeを継承して新種別追加可能 |
| 変数参照記法 | ✅ 良好 | パーサーに新記法追加可能 |
| Transformモード | ⚠️ 要注意 | 新モード追加時にTransformNode修正必要 |

**改善提案 (Consider)**:
- Transformモードを Strategy パターンで実装し、設定ファイルで新モード登録可能に

### 1.3 Liskov Substitution Principle (LSP) - リスコフの置換原則

| 評価対象 | 評価 | コメント |
|---------|------|---------|
| BaseNode継承 | ✅ 良好 | 各ノードはBaseNodeと完全に置換可能 |
| 実行結果型 | ✅ 良好 | すべてのノードがNodeResult型を返す |

**評価**: 設計上問題なし

### 1.4 Interface Segregation Principle (ISP) - インターフェース分離原則

| 評価対象 | 評価 | コメント |
|---------|------|---------|
| ノードインターフェース | ✅ 良好 | `execute()` メソッドのみ必須 |
| コンテキストAPI | ⚠️ 要注意 | ContextManagerが過剰なメソッドを持つ可能性 |

**改善提案 (Consider)**:
```typescript
// 読み取り専用と書き込み用を分離
interface ContextReader {
  get(nodeId: string): any;
  resolve(reference: string): any;
}

interface ContextWriter {
  set(nodeId: string, output: any): void;
  setError(nodeId: string, error: NodeError): void;
}

interface ContextManager extends ContextReader, ContextWriter {}
```

### 1.5 Dependency Inversion Principle (DIP) - 依存性逆転原則

| 評価対象 | 評価 | コメント |
|---------|------|---------|
| ノード → バリデータ | ✅ 良好 | インターフェース経由で依存 |
| エグゼキュータ → ノード | ✅ 良好 | BaseNode抽象に依存 |
| シークレット管理 | ✅ 良好 | 既存のAdapterパターンを踏襲 |

**SOLID総合評価**: 4.2 / 5.0 - 高い設計品質

---

## 2. 構造品質評価

### 2.1 モジュール性 (Modularity)

| 評価項目 | スコア | 詳細 |
|---------|--------|------|
| 責務分離 | 4.5/5 | 明確なレイヤー構成（API/Engine/Nodes/Types） |
| 独立性 | 4.0/5 | 各ノードは独立して開発・テスト可能 |
| 再利用性 | 4.0/5 | BaseNodeパターンで共通処理を抽出 |

**良好な点**:
- `engine/`, `nodes/`, `api/v2/` の明確な分離
- 既存の `services/` との棲み分けが明確

### 2.2 結合度 (Coupling)

| 結合関係 | 評価 | コメント |
|---------|------|---------|
| API → Engine | ✅ 低結合 | インターフェース経由 |
| Engine → Nodes | ✅ 低結合 | Factory経由でインスタンス生成 |
| Nodes → Validator | ✅ 低結合 | 依存注入可能 |
| Engine → SecretsManager | ⚠️ 中結合 | 直接依存あり |

**改善提案 (Should Fix)**:
```typescript
// SecretsProviderインターフェースを導入
interface SecretsProvider {
  getSecret(key: string): Promise<string>;
}

// ContextManagerに注入
class ContextManager {
  constructor(
    private readonly secretsProvider: SecretsProvider,
    private readonly envProvider: EnvProvider
  ) {}
}
```

### 2.3 凝集度 (Cohesion)

| モジュール | 評価 | 詳細 |
|-----------|------|------|
| ApiRestNode | ✅ 高凝集 | HTTP通信に特化 |
| TransformNode | ⚠️ 中凝集 | 複数の変換ロジックを内包 |
| ContextManager | ✅ 高凝集 | 状態管理に特化 |
| SchemaValidator | ✅ 高凝集 | 検証ロジックに特化 |

### 2.4 拡張性 (Extensibility)

| 拡張シナリオ | 難易度 | 影響範囲 |
|------------|--------|---------|
| 新ノード種別追加 | 低 | `nodes/` のみ |
| 新変数参照記法追加 | 低 | `context/` のみ |
| 新Transformモード追加 | 中 | `nodes/transform-node.ts` |
| 条件分岐機能追加 | 高 | Engine全体 |
| ループ機能追加 | 高 | Engine全体 |

**評価**: 基本的な拡張は容易。高度な制御フロー機能は将来的な設計拡張が必要。

### 2.5 保守性 (Maintainability)

| 評価項目 | スコア | 詳細 |
|---------|--------|------|
| 可読性 | 4.5/5 | 明確な命名規則、TypeScript型定義 |
| テスト容易性 | 4.0/5 | 依存注入により単体テスト可能 |
| デバッグ容易性 | 4.0/5 | 詳細なログ設計 |
| ドキュメント性 | 4.5/5 | Mermaid図、詳細な型定義 |

---

## 3. セキュリティレビュー (OWASP Top 10)

### 3.1 A01:2021 - Broken Access Control

| 対策 | 実装状況 | リスク |
|------|---------|-------|
| Admin Token認証 | ✅ 実装予定 | 低 |
| エンドポイント保護 | ✅ 設計済み | 低 |
| シークレット保護 | ✅ MyVault統合 | 低 |

**懸念点**: なし

### 3.2 A02:2021 - Cryptographic Failures

| 対策 | 実装状況 | リスク |
|------|---------|-------|
| シークレット暗号化 | ✅ MyVault側で対応 | 低 |
| 通信暗号化 | ⚠️ 記載なし | 中 |

**改善提案 (Must Fix)**:
- 外部API呼び出し時のTLS/HTTPS強制を明記
```json
{
  "config": {
    "url": "https://...",  // HTTP禁止
    "verify_ssl": true     // SSL検証必須
  }
}
```

### 3.3 A03:2021 - Injection

| 攻撃ベクトル | 対策 | リスク |
|-------------|------|-------|
| JavaScript Injection | ✅ isolated-vmサンドボックス | 低 |
| Template Injection | ⚠️ Handlebarsのみ記載 | 中 |
| Command Injection | ✅ シェル実行なし | 低 |
| SQL Injection | ✅ DB直接アクセスなし | 低 |

**改善提案 (Should Fix)**:
- Handlebarsの `noEscape` オプションを禁止
- `{{{}}}` (unescaped) の使用制限を明記

### 3.4 A04:2021 - Insecure Design

| 評価項目 | 状況 | コメント |
|---------|------|---------|
| 脅威モデリング | ⚠️ 明示的なし | セキュリティ設計は記載あり |
| セキュアバイデフォルト | ✅ 良好 | サンドボックス、検証がデフォルト |

**改善提案 (Consider)**:
- 脅威モデリング結果をドキュメントに追加

### 3.5 A05:2021 - Security Misconfiguration

| 対策 | 実装状況 | リスク |
|------|---------|-------|
| デフォルト設定 | ✅ セキュア | 低 |
| エラーメッセージ | ⚠️ 要確認 | 中 |

**改善提案 (Should Fix)**:
- 本番環境ではスタックトレースを隠蔽
```typescript
if (process.env.NODE_ENV === 'production') {
  error.stack = undefined;
}
```

### 3.6 A06:2021 - Vulnerable and Outdated Components

| 対策 | 実装状況 | リスク |
|------|---------|-------|
| 依存ライブラリ管理 | ⚠️ 明示的なし | 中 |

**改善提案 (Should Fix)**:
- `isolated-vm` のセキュリティアドバイザリ監視
- `npm audit` をCIに追加

### 3.7 A07:2021 - Identification and Authentication Failures

| 対策 | 実装状況 | リスク |
|------|---------|-------|
| Admin Token | ✅ 設計済み | 低 |
| Token有効期限 | ⚠️ 記載なし | 中 |

**改善提案 (Consider)**:
- Admin Tokenの有効期限・ローテーション方針を明記

### 3.8 A08:2021 - Software and Data Integrity Failures

| 対策 | 実装状況 | リスク |
|------|---------|-------|
| ワークフロー定義検証 | ✅ Zodスキーマ | 低 |
| JavaScript検証 | ✅ パス制限 | 低 |

**評価**: 良好

### 3.9 A09:2021 - Security Logging and Monitoring Failures

| 対策 | 実装状況 | リスク |
|------|---------|-------|
| 実行ログ | ✅ NodeLog設計 | 低 |
| セキュリティイベント | ⚠️ 明示的なし | 中 |

**改善提案 (Should Fix)**:
- 認証失敗、スキーマ違反等のセキュリティイベントを明示的にログ

### 3.10 A10:2021 - Server-Side Request Forgery (SSRF)

| 攻撃ベクトル | 対策 | リスク |
|-------------|------|-------|
| 任意URL呼び出し | ⚠️ 制限なし | **高** |

**改善提案 (Must Fix)**:
```typescript
// 許可ドメインのホワイトリスト
const ALLOWED_DOMAINS = [
  'api.example.com',
  '*.internal.company.com'
];

// プライベートIP禁止
function validateUrl(url: string): boolean {
  const parsed = new URL(url);
  // 192.168.x.x, 10.x.x.x, 127.0.0.1 等を禁止
  if (isPrivateIP(parsed.hostname)) {
    throw new Error('Private IP addresses are not allowed');
  }
  // ホワイトリストチェック
  if (!matchesWhitelist(parsed.hostname, ALLOWED_DOMAINS)) {
    throw new Error('Domain not in whitelist');
  }
  return true;
}
```

### セキュリティ総合評価

| カテゴリ | リスクレベル | 対策状況 |
|---------|------------|---------|
| SSRF | **高** | 要対策 |
| Injection | 中 | 概ね対策済み |
| Authentication | 低 | 対策済み |
| Logging | 中 | 改善推奨 |
| TLS | 中 | 明記推奨 |

**セキュリティスコア**: 4.0 / 5.0 (SSRF対策後は4.5に向上見込み)

---

## 4. 既存システムとの整合性

### 4.1 レイヤーアーキテクチャ整合性

```
現行アーキテクチャ:
┌─────────────────────────────────────────┐
│ Frontend (myAgentDesk)                  │
├─────────────────────────────────────────┤
│ Agent Layer (expertAgent, GraphAiServer)│
├─────────────────────────────────────────┤
│ Platform Layer (myVault, jobqueue等)    │
└─────────────────────────────────────────┘

TaskFlow Engine配置:
┌─────────────────────────────────────────┐
│ Frontend (myAgentDesk)                  │
├─────────────────────────────────────────┤
│ Agent Layer                             │
│  ├─ expertAgent                         │
│  └─ GraphAiServer                       │
│       ├─ /api/v1/ (GraphAI Legacy) ✅   │
│       └─ /api/v2/ (TaskFlow Engine) 新規│
├─────────────────────────────────────────┤
│ Platform Layer (myVault, jobqueue等)    │
└─────────────────────────────────────────┘
```

**評価**: ✅ 完全互換 - 既存レイヤー構成を維持

### 4.2 API設計整合性

| 項目 | 既存パターン | TaskFlow設計 | 整合性 |
|------|-------------|-------------|--------|
| エンドポイント命名 | `/api/v1/{resource}` | `/api/v2/workflows` | ✅ |
| レスポンス形式 | `{results, errors, logs}` | `{results, errors, logs}` | ✅ |
| エラーコード | 200/400/500 | 200/400/500 | ✅ |
| 認証ヘッダー | `X-Admin-Token` | `X-Admin-Token` | ✅ |

**評価**: ✅ 完全互換

### 4.3 サービス間通信整合性

| 通信 | 既存方式 | TaskFlow方式 | 整合性 |
|------|---------|-------------|--------|
| MyVault連携 | secretsManager経由 | secretsManager経由 | ✅ |
| expertAgent連携 | HTTP POST | HTTP POST | ✅ |
| ログ出力 | 既存Logger | 既存Logger | ✅ |

**評価**: ✅ 完全互換

### 4.4 設定管理整合性

| 項目 | 既存 | TaskFlow | 整合性 |
|------|------|---------|--------|
| 環境変数 | `process.env` | `${env.VAR}` | ✅ |
| シークレット | MyVault | `${secrets.KEY}` | ✅ |
| ワークフロー定義 | `config/graphai/` YAML | `config/taskflow/` JSON | ✅ 分離 |

**評価**: ✅ 良好 - 既存設定と新設定が明確に分離

### 既存システム整合性スコア: 4.5 / 5.0

---

## 5. リスク評価マトリクス

### 5.1 技術リスク

| リスク | 発生確率 | 影響度 | リスクレベル | 対策 |
|-------|---------|-------|-------------|------|
| isolated-vm脆弱性 | 低 | 高 | **中** | バージョン固定、監視 |
| 並列実行デッドロック | 低 | 中 | 低 | Promise.allSettled採用 |
| メモリリーク | 中 | 中 | **中** | コンテキストクリア徹底 |
| パフォーマンス劣化 | 中 | 中 | **中** | ベンチマークテスト |

### 5.2 セキュリティリスク

| リスク | 発生確率 | 影響度 | リスクレベル | 対策 |
|-------|---------|-------|-------------|------|
| SSRF攻撃 | 中 | 高 | **高** | URL検証強化 |
| サンドボックス突破 | 低 | 高 | **中** | isolated-vm使用 |
| 認証バイパス | 低 | 高 | **中** | 既存パターン踏襲 |
| シークレット漏洩 | 低 | 高 | **中** | MyVault統合 |

### 5.3 運用リスク

| リスク | 発生確率 | 影響度 | リスクレベル | 対策 |
|-------|---------|-------|-------------|------|
| 移行時の互換性問題 | 中 | 中 | **中** | v1/v2併存 |
| 学習コスト | 中 | 低 | 低 | ドキュメント整備 |
| デバッグ複雑化 | 中 | 中 | **中** | 詳細ログ設計 |

### リスク総合評価

| カテゴリ | 高リスク | 中リスク | 低リスク |
|---------|---------|---------|---------|
| 技術 | 0 | 3 | 1 |
| セキュリティ | 1 | 3 | 0 |
| 運用 | 0 | 3 | 1 |

**総合リスクレベル**: 中 - 対策を講じれば許容可能

---

## 6. 改善提案サマリー

### 6.1 Must Fix (必須対応)

| ID | 項目 | 対象 | 理由 |
|----|------|------|------|
| M1 | SSRF対策 | ApiRestNode | セキュリティ上のクリティカルリスク |
| M2 | TLS強制 | ApiRestNode | 通信セキュリティ確保 |

### 6.2 Should Fix (推奨対応)

| ID | 項目 | 対象 | 理由 |
|----|------|------|------|
| S1 | TransformNode分離 | nodes/ | SRP準拠、保守性向上 |
| S2 | SecretsProvider抽象化 | engine/ | DIP準拠、テスト容易性 |
| S3 | Template Injection対策 | TransformNode | セキュリティ強化 |
| S4 | 本番エラー隠蔽 | 全体 | 情報漏洩防止 |
| S5 | npm audit CI統合 | CI/CD | 脆弱性早期検知 |
| S6 | セキュリティログ強化 | 全体 | 監査対応 |

### 6.3 Consider (検討推奨)

| ID | 項目 | 対象 | 理由 |
|----|------|------|------|
| C1 | Transformモード Strategy化 | TransformNode | OCP準拠 |
| C2 | ContextReader/Writer分離 | ContextManager | ISP準拠 |
| C3 | 脅威モデリング文書化 | ドキュメント | セキュリティ設計の可視化 |
| C4 | Admin Token有効期限 | 認証 | セキュリティ強化 |

---

## 7. 実装時チェックリスト

### Phase 1実装時

- [ ] M1: SSRF対策をApiRestNode実装時に組み込み
- [ ] M2: URL検証でHTTPS強制
- [ ] S2: SecretsProviderインターフェース定義

### Phase 2実装時

- [ ] S1: TransformNodeをモード別に分離検討
- [ ] S3: Handlebarsのセキュア設定

### Phase 4実装時

- [ ] S4: 本番環境でのエラー隠蔽
- [ ] S6: セキュリティイベントログ追加

### Phase 5実装時

- [ ] S5: npm audit をCIに追加
- [ ] 全改善提案の実装確認

---

## 8. 結論

### 承認判定: **Approved with Conditions**

設計は全体として高品質であり、既存システムとの整合性も確保されています。以下の条件を満たした上で実装を開始することを推奨します：

#### 実装開始前の必須対応
1. **M1: SSRF対策の設計詳細化** - 許可ドメインリストと検証ロジックを設計書に追記
2. **M2: TLS強制の明記** - `https://` のみ許可することを設計書に追記

#### 実装中の対応
- Should Fix項目 (S1-S6) を各フェーズで対応
- Consider項目 (C1-C4) は時間が許せば対応

### 最終評価

| 評価軸 | スコア | コメント |
|-------|--------|---------|
| 設計品質 | 4.2/5.0 | SOLID原則概ね準拠 |
| セキュリティ | 4.0/5.0 | SSRF対策後は4.5見込み |
| 既存整合性 | 4.5/5.0 | 完全互換設計 |
| 実装可能性 | 4.3/5.0 | 明確なフェーズ分割 |
| 保守性 | 4.0/5.0 | 良好なモジュール構成 |
| **総合** | **4.2/5.0** | **A評価** |

---

## 参照ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [design-policy.md](./design-policy.md) | レビュー対象の設計方針書 |
| [CLAUDE.md](../../CLAUDE.md) | 品質基準・開発ガイドライン |
| [OWASP Top 10 2021](https://owasp.org/Top10/) | セキュリティチェックリスト |

---

**レビュー実施日**: 2026-01-10
**レビュアー**: Claude Code (Architecture Review)
**対象Issue**: #348
**ステータス**: **Approved** (Must Fix項目は設計書に反映済み)
