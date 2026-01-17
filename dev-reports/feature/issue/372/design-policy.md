# 設計方針書：Issue #372 - TaskFlowEngine用ベースURL解決機能

## 1. 概要

### 1.1 背景
- TaskFlowGeneratorAgent が生成した TaskFlow（ワークフロー）には capability の呼び出しが含まれる
- capability 定義には相対URL（`/v1/utility/google_search`）のみが含まれており、実際のAPIサーバーのベースURLが指定されていない
- TaskFlowEngine が api_rest ノードでAPIを実行する際、完全なURLが必要になる
- 現状では相対URLのままHTTP通信しようとして失敗する

### 1.2 目的
TaskFlowEngine が capability のAPIを実行できるように、以下を実現する：
1. capability の相対URLから完全なURLを構築する仕組み
2. 環境変数によるベースURL設定のサポート
3. 実行時のURL解決とデバッグ可能な構造

### 1.3 スコープ
- **対象**
  - mySwiftAgentCore の TaskFlowEngine
  - capability 管理システム
  - api_rest ノードの実行処理
- **対象外**
  - expertAgent 側の変更
  - capability YAML ファイル自体の変更（既存形式を維持）

## 2. アーキテクチャ設計

### 2.1 設計原則

1. **関心の分離**: URL解決ロジックは専用のコンポーネントに分離
2. **設定の外部化**: ベースURLは環境変数または設定ファイルで管理
3. **テスタビリティ**: URL解決ロジックは単独でテスト可能
4. **拡張性**: 将来的な認証情報管理や他のメタデータにも対応可能

### 2.2 システム構成

```
┌─────────────────────────────────────────────────────────────┐
│                     mySwiftAgentCore                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌────────────────┐                │
│  │ Capability      │    │ EndpointConfig │                │
│  │ Registry        │───▶│ Manager        │                │
│  └─────────────────┘    └────────────────┘                │
│           │                      │                          │
│           ▼                      ▼                          │
│  ┌─────────────────┐    ┌────────────────┐                │
│  │ Capability      │    │ URL Resolver   │                │
│  │ Loader (YAML)   │    │                │                │
│  └─────────────────┘    └────────────────┘                │
│                                 │                           │
│                                 ▼                           │
│  ┌─────────────────────────────────────┐                  │
│  │        TaskFlow Engine              │                  │
│  ├─────────────────────────────────────┤                  │
│  │  ┌─────────────┐   ┌──────────────┐│                  │
│  │  │ ApiRestNode │──▶│ Capability   ││                  │
│  │  │ Executor    │   │ Executor     ││                  │
│  │  └─────────────┘   └──────────────┘│                  │
│  └─────────────────────────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 主要コンポーネント

#### 2.3.1 EndpointConfigManager
- **責務**: エンドポイント設定の管理
- **機能**:
  - index.yaml の api_endpoints セクションを読み込み
  - 環境変数の値を解決（`${VAR:-default}` 形式）
  - エンドポイント設定をメモリにキャッシュ

#### 2.3.2 URLResolver
- **責務**: 相対URLから完全なURLを構築
- **機能**:
  - capability の _internal.endpoint を取得
  - 適切なベースURLを選択
  - 完全なURLを構築
  - 認証情報の付与（auth_type に応じて）

#### 2.3.3 CapabilityExecutor
- **責務**: capability ベースのAPI実行
- **機能**:
  - capability ID からエンドポイント情報を解決
  - URLResolver を使って完全なURLを取得
  - ApiRestNode にパラメータを渡して実行

## 3. 詳細設計

### 3.1 データ構造

```typescript
// エンドポイント設定
interface EndpointConfig {
  base_url: string;         // ${EXPERT_AGENT_BASE_URL:-http://localhost:8004}
  description: string;      // AI Agent API (LangGraph agents, utilities)
  endpoint_prefix?: string; // /v1/
}

// api_endpoints セクション
interface ApiEndpointsConfig {
  [key: string]: EndpointConfig;
}

// URL解決結果
interface ResolvedEndpoint {
  url: string;              // 完全なURL
  auth?: {
    type: 'bearer' | 'basic' | 'api_key';
    secret_key: string;
    header_name?: string;
  };
  timeout_ms?: number;
}
```

### 3.2 処理フロー

1. **起動時**
   ```
   1. index.yaml から api_endpoints を読み込み
   2. 環境変数を解決（${VAR:-default} パターン）
   3. EndpointConfigManager に設定を登録
   ```

2. **TaskFlow実行時**
   ```
   1. api_rest ノードが capability を参照
   2. CapabilityRegistry から capability を取得
   3. URLResolver で完全なURLを構築
      - _internal.endpoint から相対パスを取得
      - エンドポイントプレフィックスから適切なベースURLを選択
      - 環境変数解決済みのベースURLと結合
   4. ApiRestNodeExecutor でHTTPリクエスト実行
   ```

### 3.3 環境変数の解決

```typescript
// 環境変数パターン: ${VAR_NAME:-default_value}
function resolveEnvVar(value: string): string {
  const pattern = /\$\{([^}]+)\}/g;
  return value.replace(pattern, (match, content) => {
    const [varName, defaultValue] = content.split(':-');
    return process.env[varName] || defaultValue || match;
  });
}
```

### 3.4 URL構築ロジック

```typescript
function buildFullUrl(capability: CapabilityExtended, config: ApiEndpointsConfig): string {
  const endpoint = capability._internal?.endpoint;
  if (!endpoint) {
    throw new Error(`No endpoint defined for capability: ${capability.id}`);
  }

  // エンドポイントプレフィックスからベースURLを特定
  const baseConfig = findMatchingBaseConfig(endpoint, config);
  if (!baseConfig) {
    throw new Error(`No base URL configuration found for endpoint: ${endpoint}`);
  }

  // 完全なURLを構築
  const baseUrl = resolveEnvVar(baseConfig.base_url);
  return `${baseUrl}${endpoint}`;
}
```

## 4. 実装方針

### 4.1 フェーズ1: 基盤整備
1. EndpointConfigManager の実装
   - index.yaml の api_endpoints 読み込み
   - 環境変数解決ロジック
   - 設定のキャッシュ機構

2. URLResolver の実装
   - URL構築ロジック
   - エンドポイントマッピング
   - エラーハンドリング

### 4.2 フェーズ2: TaskFlowEngine統合
1. CapabilityExecutor の実装
   - capability から URL への変換
   - 認証情報の付与
   - ApiRestNode への委譲

2. ApiRestNode の拡張
   - capability 参照のサポート
   - CapabilityExecutor の利用

### 4.3 フェーズ3: テストとドキュメント
1. 単体テストの作成
   - URL解決ロジックのテスト
   - 環境変数解決のテスト
   - エッジケースのテスト

2. 結合テストの作成
   - TaskFlow 実行のE2Eテスト
   - 実際のAPIコールのテスト

3. ドキュメントの作成
   - 設定方法のドキュメント
   - トラブルシューティングガイド

## 5. 非機能要件

### 5.1 パフォーマンス
- URL解決は高速（< 1ms）
- 設定のキャッシュにより、繰り返しの解決を最適化
- 起動時の設定読み込みは1回のみ

### 5.2 セキュリティ
- APIキーなどの認証情報は環境変数経由で設定
- capability の _internal セクションはクライアントに露出しない
- HTTPSエンドポイントの使用を推奨

### 5.3 保守性
- 設定はYAMLファイルで管理（コードとの分離）
- エラーメッセージは具体的で問題解決に役立つ
- ログ出力により実行時の挙動を追跡可能

## 6. テスト計画

### 6.1 単体テスト
- [ ] EndpointConfigManager のテスト
  - [ ] api_endpoints の読み込み
  - [ ] 環境変数の解決
  - [ ] デフォルト値の適用
- [ ] URLResolver のテスト
  - [ ] 正常なURL構築
  - [ ] エラーケース（エンドポイント未定義など）
- [ ] CapabilityExecutor のテスト
  - [ ] capability からの実行
  - [ ] 認証情報の付与

### 6.2 結合テスト
- [ ] TaskFlow実行のE2Eテスト
  - [ ] google_search capability の実行
  - [ ] 認証が必要なAPIの実行
  - [ ] エラーハンドリング

### 6.3 受入テスト
- [ ] 実際のexpertAgentに対するAPIコール
- [ ] 環境変数による設定変更の確認
- [ ] エラー時の挙動確認

## 7. リスクと対策

### 7.1 リスク
1. **既存の動作への影響**
   - 対策: 後方互換性を保ち、段階的に移行

2. **環境変数の管理複雑化**
   - 対策: 明確なドキュメントとデフォルト値の提供

3. **デバッグの困難さ**
   - 対策: 詳細なログ出力と診断ツールの提供

### 7.2 移行計画
1. 新機能として追加（既存機能に影響なし）
2. テスト環境で十分な検証
3. 段階的な本番環境への適用

## 8. 今後の拡張性

### 8.1 将来的な機能拡張
- 複数環境（dev/staging/prod）の切り替え
- APIバージョン管理
- リトライ・サーキットブレーカーの統合
- メトリクス・トレーシングの統合

### 8.2 他システムとの連携
- myVault との統合（認証情報の安全な管理）
- Langfuse との統合（API実行のトレーシング）

## 9. 受入条件

1. **機能要件**
   - [ ] capability の相対URLから完全なURLを構築できる
   - [ ] 環境変数でベースURLを設定できる
   - [ ] TaskFlowEngine から capability ベースのAPIを実行できる

2. **非機能要件**
   - [ ] URL解決のパフォーマンスが1ms以下
   - [ ] エラー時に明確なメッセージが表示される
   - [ ] 既存の TaskFlow 実行に影響を与えない

3. **ドキュメント**
   - [ ] 設定方法のドキュメントが作成されている
   - [ ] API仕様が更新されている
   - [ ] サンプルコードが提供されている

## 10. 技術仕様

### 10.1 新規インターフェース定義

```typescript
// src/capabilityManagement/endpoint/types.ts

/**
 * エンドポイント設定
 */
export interface EndpointConfig {
  /** ベースURL (環境変数を含む) */
  base_url: string;
  /** 説明 */
  description: string;
  /** エンドポイントプレフィックス */
  endpoint_prefix?: string;
}

/**
 * API エンドポイント設定マップ
 */
export interface ApiEndpointsConfig {
  [key: string]: EndpointConfig;
}

/**
 * 解決されたエンドポイント情報
 */
export interface ResolvedEndpoint {
  /** 完全なURL */
  url: string;
  /** 認証情報 */
  auth?: {
    type: 'bearer' | 'basic' | 'api_key';
    secret_key: string;
    header_name?: string;
  };
  /** タイムアウト（ミリ秒） */
  timeout_ms?: number;
}

/**
 * エンドポイント解決エラー
 */
export class EndpointResolutionError extends Error {
  constructor(
    message: string,
    public readonly capabilityId: string,
    public readonly endpoint?: string
  ) {
    super(message);
    this.name = 'EndpointResolutionError';
  }
}
```

### 10.2 EndpointConfigManager API

```typescript
// src/capabilityManagement/endpoint/EndpointConfigManager.ts

export interface EndpointConfigManagerOptions {
  /** 設定ファイルのベースパス */
  basePath: string;
  /** キャッシュを有効化 */
  enableCache?: boolean;
}

export class EndpointConfigManager {
  constructor(options: EndpointConfigManagerOptions);

  /**
   * プロジェクトのエンドポイント設定を読み込み
   * @param projectId プロジェクトID
   * @returns エンドポイント設定
   */
  async loadProjectEndpoints(projectId: string): Promise<ApiEndpointsConfig>;

  /**
   * 環境変数を解決
   * @param value 環境変数を含む文字列
   * @returns 解決された文字列
   */
  resolveEnvVars(value: string): string;

  /**
   * キャッシュをクリア
   */
  clearCache(): void;
}
```

### 10.3 URLResolver API

```typescript
// src/capabilityManagement/endpoint/URLResolver.ts

export interface URLResolverOptions {
  /** EndpointConfigManager インスタンス */
  configManager: EndpointConfigManager;
  /** デフォルトのプロジェクトID */
  defaultProjectId?: string;
}

export class URLResolver {
  constructor(options: URLResolverOptions);

  /**
   * capability から完全なURLを解決
   * @param capability capability情報
   * @param projectId プロジェクトID（省略時はdefault使用）
   * @returns 解決されたエンドポイント情報
   */
  async resolveCapabilityUrl(
    capability: CapabilityExtended,
    projectId?: string
  ): Promise<ResolvedEndpoint>;

  /**
   * エンドポイントパスから設定を検索
   * @param endpoint エンドポイントパス
   * @param config エンドポイント設定
   * @returns マッチした設定
   */
  findMatchingConfig(
    endpoint: string,
    config: ApiEndpointsConfig
  ): EndpointConfig | undefined;
}
```

### 10.4 CapabilityExecutor API

```typescript
// src/taskflowEngine/nodes/CapabilityExecutor.ts

export interface CapabilityExecutorOptions {
  /** URLResolver インスタンス */
  urlResolver: URLResolver;
  /** CapabilityRegistry インスタンス */
  capabilityRegistry: CapabilityRegistry;
}

export class CapabilityExecutor {
  constructor(options: CapabilityExecutorOptions);

  /**
   * capability を実行
   * @param capabilityId capability ID
   * @param params 実行パラメータ
   * @param context 実行コンテキスト
   * @returns 実行結果
   */
  async execute(
    capabilityId: string,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult>;

  /**
   * capability 設定を検証
   * @param capabilityId capability ID
   * @returns 検証結果
   */
  async validate(capabilityId: string): Promise<NodeValidationResult>;
}
```

### 10.5 拡張された ApiRestNode

```typescript
// src/taskflowEngine/nodes/ApiRestNode.ts の拡張

export interface ApiRestNodeConfig {
  /** 直接URL指定（従来方式） */
  url?: string;
  /** capability ID指定（新方式） */
  capability_id?: string;
  /** HTTPメソッド */
  method: string;
  /** ヘッダー */
  headers?: Record<string, string>;
  /** 認証設定（capability使用時は不要） */
  auth?: AuthConfig;
}

// ApiRestNodeExecutor の execute メソッド拡張
async execute(
  config: NodeConfig,
  params: Record<string, unknown>,
  context: NodeExecutionContext
): Promise<NodeResult> {
  const { url, capability_id, method, headers = {} } = config.config as ApiRestNodeConfig;

  // capability指定の場合
  if (capability_id) {
    const capabilityExecutor = context.services?.capabilityExecutor;
    if (!capabilityExecutor) {
      throw new Error('CapabilityExecutor not available in context');
    }
    return capabilityExecutor.execute(capability_id, params, context);
  }

  // 従来の直接URL指定
  if (url) {
    // 既存の処理...
  }

  throw new Error('Either url or capability_id must be specified');
}
```

### 10.6 環境変数

```bash
# expertAgent のベースURL
EXPERT_AGENT_BASE_URL=http://localhost:8004

# Google APIs のベースURL（通常は変更不要）
GOOGLE_APIS_BASE_URL=https://www.googleapis.com

# その他のサービス
GRAPHAI_SERVER_BASE_URL=http://localhost:8005
MYVAULT_BASE_URL=http://localhost:8003
```

### 10.7 設定ファイル例

```yaml
# mySwiftAgentCore/config/capabilities/default_project/index.yaml

# API エンドポイント設定
api_endpoints:
  # expertAgent API
  expert_agent:
    base_url: "${EXPERT_AGENT_BASE_URL:-http://localhost:8004}"
    description: "AI Agent API (LangGraph agents, utilities)"
    endpoint_prefix: "/v1/"

  # Google APIs
  google_apis:
    base_url: "${GOOGLE_APIS_BASE_URL:-https://www.googleapis.com}"
    description: "Google APIs (Drive, Gmail, etc.)"

  # GraphAI Server
  graphai_server:
    base_url: "${GRAPHAI_SERVER_BASE_URL:-http://localhost:8005}"
    description: "Workflow execution API"
    endpoint_prefix: "/api/"

# Capability リスト
capabilities:
  - gmail_search
  - gmail_send
  - google_search
  # ...
```

## 11. 実装ロードマップ

### Phase 1: 基盤実装（1週間）
- [ ] EndpointConfigManager の実装と単体テスト
- [ ] URLResolver の実装と単体テスト
- [ ] 環境変数解決ロジックのテスト

### Phase 2: TaskFlowEngine統合（1週間）
- [ ] CapabilityExecutor の実装
- [ ] ApiRestNode の拡張
- [ ] NodeExecutionContext への services 追加
- [ ] 結合テストの作成

### Phase 3: ドキュメントと受入テスト（3日）
- [ ] API ドキュメントの作成
- [ ] 設定ガイドの作成
- [ ] 受入テストの実装と実行
- [ ] サンプルコードの作成

### Phase 4: デプロイと監視（2日）
- [ ] 環境変数の設定
- [ ] ステージング環境でのテスト
- [ ] 本番環境への段階的リリース
- [ ] モニタリングとログ設定

## 12. 参考資料

- [Issue #363: TaskFlow実行エンジンの実装](../363/README.md)
- [Issue #365: Capability定義と管理](../365/README.md)
- [service-dependencies.md](../../../../docs/arch/service-dependencies.md)
- [expertAgent capabilities YAML](../../../../expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/config/expert_agent_capabilities.yaml)