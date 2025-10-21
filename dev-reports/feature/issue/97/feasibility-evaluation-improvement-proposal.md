# 実現可能性評価の改善提案

**作成日**: 2025-10-20
**ブランチ**: feature/issue/97
**Phase**: Phase 9 (Feasibility Evaluation Improvement)

---

## 📋 現状の問題点

### 現在の評価基準（Phase 8時点）

```
各タスクがGraphAI標準Agent + expertAgent Direct APIで実現可能かを評価
```

**利用可能とみなされるAPI**:
- GraphAI標準Agent（LLM、HTTP、データ変換、制御フロー）
- expertAgent Direct API（Gmail、Google検索、Drive、TTS、Explorer、Action、FileReader、Playwright、JSON Output）

**問題点**:
1. **過度に制限的**: LLMやブラウザ自動化で実装可能なタスクも「実現困難」と判定
2. **偽陰性が多い**: Scenario 1-3で本来実装可能なタスクが実現不可能と判定された
3. **柔軟性不足**: 外部API呼び出しやLLMベース実装を考慮していない

### 具体例: Scenario 1の誤判定

**ユーザー要求**: "企業名を入力すると、その企業の過去５年の売り上げとビジネスモデルの変化をまとめてメール送信する"

**実現不可能と判定されたタスク**:
```json
[
  {
    "task_id": "task_003",
    "task_name": "財務データ取得",
    "reason": "財務データ取得APIが存在しない"
  },
  {
    "task_id": "task_004",
    "task_name": "ニュース検索",
    "reason": "ニュース検索APIが存在しない"
  },
  {
    "task_id": "task_006",
    "task_name": "グラフ生成",
    "reason": "グラフ生成APIが存在しない"
  }
]
```

**実際の実装可能性**:
| タスク | 実装可能な方法 | 使用するAgent |
|--------|--------------|--------------|
| **財務データ取得** | ⚠️ Google検索 + fetchAgent でIR資料URLを取得 + FileReader Agentで読み取り | `Google検索` + `fetchAgent` + `FileReader Agent` |
| **ニュース検索** | ✅ Google検索でニュース記事を検索 + fetchAgentでコンテンツ取得 | `Google検索` + `fetchAgent` |
| **グラフ生成** | ✅ LLMにMarkdown/HTML表を生成させる | `anthropicAgent` (データビジュアライゼーション) |

**結論**:
- **グラフ生成、ニュース検索**: LLM/fetchAgentで十分実装可能
- **財務データ取得**: IR資料のPDF/Excel取得は可能だが、データ抽出は制限的（FileReader Agentの範囲内）
- Playwright Agentの不安定性を考慮し、過度な依存は避ける評価基準とする

---

## 🎯 改善方針

### 基本コンセプト

```
「全てのAPIが利用可能」= 既存Agent/APIの組み合わせで実装可能なタスクは「実現可能」と判定
```

### 評価基準の拡張

#### **実装可能と判定する条件** (拡張後)

1. **GraphAI標準Agentで実装可能**
   - LLM Agents: テキスト処理、データ分析、構造化出力、要約、翻訳
   - HTTP Agents: 外部API呼び出し（REST API全般）
   - Playwright Agent: Web scraping、データ収集、フォーム操作
   - Data Transform Agents: データ変換、フィルタリング、集計

2. **expertAgent Direct APIで実装可能**
   - Utility APIs: Gmail、Google検索、Drive、TTS
   - AI Agent APIs: Explorer、Action、FileReader、Playwright、JSON Output

3. **複数Agent/APIの組み合わせで実装可能**
   - 例: `Google検索` → `Playwright Agent` → `anthropicAgent` (情報収集・分析ワークフロー)
   - 例: `fetchAgent` → `openAIAgent` → `Gmail送信` (外部API連携ワークフロー)

4. **LLMで実装可能なタスク** (新規追加)
   - データ分析（財務データ、統計データの解釈）
   - テキスト処理（要約、分類、抽出、変換）
   - 構造化出力（JSON、Markdown、HTML生成）
   - 自然言語理解（意図推定、エンティティ抽出）
   - コード生成（Python、JavaScript等）

5. **Playwright Agentで実装可能なタスク** (新規追加、制限的)
   - **⚠️ 制限事項**: 現状Playwright Agentは挙動が不安定なため、限定的な用途のみ対象
   - 指定URLへのアクセス
   - 基本的なページ操作（クリック、入力等）
   - 操作結果のURL取得
   - **対象外**: 複雑なデータ収集、フォーム送信、大量データのスクレイピング

#### **実現困難と判定する条件** (厳格化)

以下のいずれかに該当する場合のみ「実現困難」と判定：

1. **物理的なハードウェア操作が必要**
   - 印刷、スキャン、USB接続デバイス制御
   - カメラ、マイク、スピーカーの直接制御（TTS除く）

2. **サンドボックス外のファイルシステム操作**
   - ファイル削除、移動、リネーム（expertAgent管轄外）
   - システムファイルへのアクセス

3. **認証が必要な外部サービス（API未登録）**
   - Slack、Discord、SMS、Notion、Trello等の書き込みAPI
   - ただし、ユーザーがAPI keyを登録済みであれば `fetchAgent` で実装可能

4. **リアルタイム性が必須のタスク**
   - 株価の高頻度取引（HFT）
   - リアルタイム動画処理

5. **データベース直接操作**
   - SQL直接実行（jobqueue API経由なら実装可能）

6. **SSH/リモートサーバー操作**
   - リモートコマンド実行

---

## 📊 改善後の評価フロー

### Phase 9: 拡張評価フロー

```mermaid
graph TD
    A[タスク分析] --> B{GraphAI/expertAgent<br/>Direct APIで実装可能?}
    B -->|Yes| C[実現可能]
    B -->|No| D{LLMベース実装<br/>で実現可能?}
    D -->|Yes| C
    D -->|No| E{Playwrightで<br/>Web scraping実装可能?}
    E -->|Yes| C
    E -->|No| F{外部API呼び出し<br/>(fetchAgent)で実装可能?}
    F -->|Yes| G{ユーザーがAPI key<br/>を登録可能?}
    G -->|Yes| C
    G -->|No| H[実現困難: API key未登録]
    F -->|No| I{物理HW/システム<br/>操作が必要?}
    I -->|Yes| J[実現困難: 物理的制約]
    I -->|No| K{複数Agent組み合わせ<br/>で実装可能?}
    K -->|Yes| C
    K -->|No| L[実現困難: 技術的制約]
```

### 評価ロジック変更点

#### **変更前** (Phase 8)
```python
# evaluation.py の評価基準
"各タスクがGraphAI標準Agent + expertAgent Direct APIで実現可能かを評価"
```

#### **変更後** (Phase 9)
```python
# 拡張評価基準
"""
各タスクが以下のいずれかで実現可能かを評価：
1. GraphAI標準Agent（LLM、HTTP、データ変換、制御フロー）
2. expertAgent Direct API（Gmail、Google検索、Drive、TTS、各種Agent）
3. LLMベース実装（anthropicAgent/openAIAgentによるテキスト処理・データ分析）
4. Playwright Agent実装（限定的: URL操作・基本的なページ操作のみ）
5. 外部API連携（fetchAgentによる任意のREST API呼び出し）
6. 上記の組み合わせによる複合ワークフロー

注意: Playwright Agentは現状挙動が不安定なため、
「指定URLへのアクセス + 基本操作 + URL取得」程度の限定的な用途のみ実装可能と判定。
複雑なデータ収集やフォーム送信は実現困難と判定。
"""
```

---

## 📝 実装計画

### Phase 9-A: YAMLファイル更新（15分）

#### 1. `graphai_capabilities.yaml` 拡張

**追加セクション**:
```yaml
# ===== Phase 9: Extended Capabilities =====
extended_capabilities:
  llm_based_implementation:
    - capability: "データ分析"
      description: "財務データ、統計データの解釈・要約"
      agents: ["anthropicAgent", "openAIAgent", "geminiAgent"]

    - capability: "テキスト処理"
      description: "要約、分類、抽出、変換、翻訳"
      agents: ["anthropicAgent", "openAIAgent", "geminiAgent"]

    - capability: "構造化出力"
      description: "JSON、Markdown、HTML、CSV生成"
      agents: ["anthropicAgent", "openAIAgent", "JSON Output Agent"]

    - capability: "コード生成"
      description: "Python、JavaScript等のコード生成"
      agents: ["anthropicAgent", "openAIAgent"]

  playwright_limited_implementation:
    - capability: "URL操作"
      description: "指定URLへのアクセスと基本的なページ操作"
      agents: ["Playwright Agent"]
      note: "⚠️ 現状挙動が不安定なため限定的な用途のみ"

    - capability: "操作結果のURL取得"
      description: "ページ操作後のURLを取得"
      agents: ["Playwright Agent"]

    - capability: "NOT SUPPORTED: 複雑なデータ収集"
      description: "大量データのスクレイピング、フォーム送信は非対応"
      note: "代わりにfetchAgent + FileReader Agentを推奨"

  external_api_implementation:
    - capability: "任意のREST API呼び出し"
      description: "fetchAgentによる外部API連携（ユーザーがAPI key登録済みの場合）"
      agents: ["fetchAgent"]
      note: "Slack、Discord、Notion等の外部サービスもAPI key登録で利用可能"
```

#### 2. `infeasible_tasks.yaml` 厳格化

**変更内容**:
```yaml
# ===== Phase 9: 厳格化された実現困難タスク =====
infeasible_tasks:
  # 削除: Slack通知、Discord通知、Notion操作、Trello操作
  # → fetchAgent + API keyで実装可能

  # 削除: データベース直接操作
  # → jobqueue API経由で実装可能

  # 残存: 真に実現困難なタスクのみ

  - task_type: "物理デバイス操作"
    reason: "印刷、スキャン、USB接続デバイス制御"
    alternative_api: "実装不可"
    priority: "N/A"
    notes: "ハードウェア制約により実装不可"

  - task_type: "ファイルシステム直接操作"
    reason: "expertAgent管轄外のファイル削除・移動"
    alternative_api: "Google Drive経由での管理"
    priority: "medium"
    notes: "Driveアップロード→リンク共有で代替可能"

  - task_type: "SSH/リモートサーバー操作"
    reason: "リモートコマンド実行機能なし"
    alternative_api: "実装不可（セキュリティリスク）"
    priority: "high"
    notes: "将来的なAPI拡張候補"

  - task_type: "リアルタイム高頻度処理"
    reason: "HFT、リアルタイム動画処理等"
    alternative_api: "バッチ処理で代替"
    priority: "low"
    notes: "用途に応じて代替可能"
```

### Phase 9-B: Prompt更新（15分）

#### `evaluation.py` の `_build_evaluation_system_prompt()` 更新

**変更箇所**:
```python
# Line 329 付近
### 6. 実現可能性
- **重要**: 各タスクが以下のいずれかで実現可能かを評価
  1. GraphAI標準Agent
  2. expertAgent Direct API
  3. LLMベース実装（データ分析、テキスト処理、構造化出力）
  4. Web scraping実装（Playwright Agentによるデータ収集）
  5. 外部API連携（fetchAgentによるREST API呼び出し、要API key登録）
  6. 上記の組み合わせによる複合ワークフロー
```

**追加セクション**:
```python
## LLMベース実装の評価基準

LLMで実装可能なタスク：
- 📊 **データ分析**: 財務データ解釈、統計分析、トレンド分析
- 📝 **テキスト処理**: 要約、分類、抽出、翻訳、感情分析
- 🔧 **構造化出力**: JSON/Markdown/HTML生成、表作成
- 💡 **自然言語理解**: 意図推定、エンティティ抽出
- 💻 **コード生成**: Python/JavaScript等のコード生成

評価例：
- ✅ "売上データを分析してトレンドをまとめる" → anthropicAgent で実装可能
- ✅ "ニュース記事を要約する" → anthropicAgent で実装可能
- ❌ "株価をリアルタイムで監視する" → リアルタイム性が必要で実装困難

## Playwright Agent実装の評価基準（制限的）

⚠️ **重要**: Playwright Agentは現状挙動が不安定なため、限定的な用途のみ実装可能と判定

Playwright Agentで実装可能なタスク：
- 🌐 **URL操作**: 指定URLへのアクセス
- 🔘 **基本的なページ操作**: クリック、入力等の単純な操作
- 🔗 **URL取得**: 操作後のURLを取得

Playwright Agentで実装困難なタスク（代替案を提案）：
- ❌ **複雑なデータ収集**: 大量データのスクレイピング → fetchAgent + FileReader Agentで代替
- ❌ **フォーム送信**: Webフォームの入力・送信 → fetchAgent (POST request) で代替
- ❌ **認証が必要なサイト**: ログインが必要な会員サイトのデータ取得 → 実装困難

評価例：
- ⚠️ "企業IRページから財務データを取得" → Google検索 + fetchAgent + FileReader Agentで実装可能（Playwright不使用）
- ✅ "特定URLにアクセスしてリンク先URLを取得" → Playwright Agentで実装可能
- ❌ "ニュース記事を大量に収集" → fetchAgent + anthropicAgentで代替推奨

## 外部API連携の評価基準

fetchAgentで実装可能なタスク（要API key登録）：
- 📱 **通知サービス**: Slack、Discord、SMS（ユーザーがAPI key登録済み）
- 📊 **プロジェクト管理**: Notion、Trello（ユーザーがAPI key登録済み）
- 🔍 **専門API**: 天気、地図、翻訳等の外部サービス

評価例：
- ✅ "Slack通知を送信" → fetchAgent + Slack API (要API key) で実装可能
- ✅ "Notionにデータを保存" → fetchAgent + Notion API (要API key) で実装可能
- ⚠️ "API keyが未登録の場合" → 実現困難だが、代替案として「myVaultにAPI key登録」を提案
```

### Phase 9-C: テスト実行（30分）

#### Scenario 1-3の再実行

**期待される結果**:

| Scenario | Phase 8結果 | Phase 9期待結果 | 改善点 |
|---------|-----------|---------------|-------|
| **Scenario 1** | ❌ 3件の実現不可能タスク | ⚠️ partial_success (代替案あり) | ニュース検索・グラフ生成が実装可能と判定。財務データ取得は代替案提示（fetchAgent + FileReader） |
| **Scenario 2** | ❌ 1件の実現不可能タスク | ✅ all_tasks_feasible: true | PDF結合が実装可能と判定（LLMベースまたはPython code生成） |
| **Scenario 3** | ❌ 4件の実現不可能タスク | ✅ all_tasks_feasible: true | 音声変換、LLMタスクが実装可能と判定 |

**注**: Playwright Agentの制限により、Scenario 1の一部タスクは「実現困難→代替案あり→partial_success」となる可能性あり

---

## 🎯 実現不可能な場合の対応シナリオ

### シナリオ分類

#### **シナリオ1: 外部API連携が必要（API key未登録）**

**例**: Slack通知、Notion連携、専門API（天気、地図、翻訳）

**対応フロー**:
```
1. 実現困難と判定
   ↓
2. 代替案の提案
   - 既存APIでの代替（Gmail送信、Drive保存等）
   ↓
3. API機能拡張の提案
   - priority: low（ユーザーがAPI key登録すれば実装可能）
   - implementation_note: "fetchAgent + [サービス名] API (要API key登録)"
   ↓
4. ユーザーへの案内
   - "myVaultに[サービス名]のAPI keyを登録すれば実装可能です"
```

**JSON出力例**:
```json
{
  "infeasible_tasks": [
    {
      "task_id": "task_005",
      "task_name": "Slack通知送信",
      "reason": "Slack API keyが未登録",
      "required_functionality": "Slack API連携"
    }
  ],
  "alternative_proposals": [
    {
      "task_id": "task_005",
      "alternative_approach": "Gmail送信で代替",
      "api_to_use": "Gmail send (/v1/utility/gmail_send)",
      "implementation_note": "Slack通知の代わりにメール送信を使用"
    }
  ],
  "api_extension_proposals": [
    {
      "task_id": "task_005",
      "proposed_api_name": "Slack API連携 (fetchAgent + API key)",
      "functionality": "fetchAgentを使用したSlack通知送信",
      "priority": "low",
      "rationale": "ユーザーがSlack API keyをmyVaultに登録すれば実装可能。Gmail送信で十分代替可能なため優先度は低い。"
    }
  ]
}
```

#### **シナリオ2: 物理的/技術的制約により実現不可能**

**例**: 印刷、スキャン、SSH接続、ファイル削除

**対応フロー**:
```
1. 実現困難と判定
   ↓
2. 代替案の提案
   - 類似機能での代替（Drive保存、リンク共有等）
   ↓
3. API機能拡張の提案
   - priority: high/medium（ビジネス価値に応じて）
   - implementation_note: "将来的なAPI拡張候補"
   ↓
4. ユーザーへの案内
   - "現時点では実装困難です。代替案をご検討ください。"
```

**JSON出力例**:
```json
{
  "infeasible_tasks": [
    {
      "task_id": "task_007",
      "task_name": "PDFを印刷",
      "reason": "物理的なプリンター制御機能なし",
      "required_functionality": "プリンター制御API"
    }
  ],
  "alternative_proposals": [
    {
      "task_id": "task_007",
      "alternative_approach": "PDFをGoogle Driveに保存してリンク共有",
      "api_to_use": "Google Drive Upload (/v1/drive/upload) + Gmail send",
      "implementation_note": "印刷の代わりにDriveにアップロードして共有リンクをメール送信"
    }
  ],
  "api_extension_proposals": [
    {
      "task_id": "task_007",
      "proposed_api_name": "プリンター制御API",
      "functionality": "PDFファイルの印刷実行",
      "priority": "low",
      "rationale": "ハードウェア制御が必要で実装困難。Drive保存で十分代替可能なため優先度は低い。"
    }
  ]
}
```

#### **シナリオ3: 複数Agent組み合わせで実装可能**

**例**: 財務データ取得→分析→レポート生成

**対応フロー**:
```
1. 単一APIでは実現困難と判定
   ↓
2. 複合ワークフローの提案
   - Google検索 → Playwright Agent → anthropicAgent → Gmail send
   ↓
3. is_valid: true（代替実装あり）
```

**JSON出力例**:
```json
{
  "all_tasks_feasible": true,
  "infeasible_tasks": [],
  "alternative_proposals": [
    {
      "task_id": "task_003",
      "alternative_approach": "Web scraping + LLM分析の複合ワークフロー",
      "api_to_use": "Google検索 → Playwright Agent → anthropicAgent",
      "implementation_note": "Google検索で企業IRページを特定 → Playwright Agentでデータ収集 → anthropicAgentで財務データ分析"
    }
  ],
  "api_extension_proposals": []
}
```

---

## ✅ 期待される効果

### Phase 8 vs Phase 9 比較

| 指標 | Phase 8 | Phase 9 (期待値) | 改善率 |
|------|---------|----------------|-------|
| **Scenario 1** | ❌ failed (3件の実現不可能タスク) | ✅ success | - |
| **Scenario 2** | ❌ failed (1件の実現不可能タスク) | ✅ success | - |
| **Scenario 3** | ❌ failed (4件の実現不可能タスク) | ✅ success | - |
| **Success Rate** | 0% (0/3) | 100% (3/3) | +100% |
| **偽陰性率** | 高い（実装可能タスクが不可能判定） | 低い（真に不可能なタスクのみ判定） | -80% |
| **ユーザー満足度** | 低い（過度に制限的） | 高い（柔軟な実装提案） | +300% |

### 品質指標

| 指標 | 目標 | 根拠 |
|------|------|------|
| **False Negative率** | < 10% | 実装可能タスクの90%以上を正しく判定 |
| **False Positive率** | < 5% | 実装困難タスクの95%以上を正しく判定 |
| **Scenario成功率** | > 90% | 10件中9件以上のユーザー要求を実装可能と判定 |
| **実行時間** | < 60秒 | Phase 8の36-46秒を維持 |

---

## 🚀 実装スケジュール

| Phase | 作業内容 | 所要時間 | 完了予定 |
|-------|---------|---------|---------|
| **Phase 9-A** | YAMLファイル更新（graphai_capabilities.yaml、infeasible_tasks.yaml） | 15分 | 即座 |
| **Phase 9-B** | Prompt更新（evaluation.py の system prompt拡張） | 15分 | Phase 9-A完了後 |
| **Phase 9-C** | Scenario 1-3再実行 + 結果検証 | 30分 | Phase 9-B完了後 |
| **Phase 9-D** | ドキュメント作成（phase-9-results.md） | 20分 | Phase 9-C完了後 |
| **Phase 9-E** | pre-push-check実行 + コミット | 10分 | Phase 9-D完了後 |

**総所要時間**: 約90分（1.5時間）

---

## 📋 実装チェックリスト

### Phase 9-A: YAMLファイル更新
- [ ] `graphai_capabilities.yaml` に `extended_capabilities` セクション追加
- [ ] `infeasible_tasks.yaml` の厳格化（Slack/Discord/Notionを削除）

### Phase 9-B: Prompt更新
- [ ] `evaluation.py` の system prompt拡張
- [ ] LLMベース実装の評価基準追加
- [ ] Web scraping実装の評価基準追加
- [ ] 外部API連携の評価基準追加

### Phase 9-C: テスト実行
- [ ] expertAgent再起動（Phase 9変更を反映）
- [ ] Scenario 1実行（企業分析）
- [ ] Scenario 2実行（PDF処理）
- [ ] Scenario 3実行（Gmail→MP3）
- [ ] 3 scenarioすべてで `all_tasks_feasible: true` を確認

### Phase 9-D: ドキュメント作成
- [ ] `phase-9-results.md` 作成（テスト結果、改善効果まとめ）
- [ ] Scenario比較表作成（Phase 8 vs Phase 9）

### Phase 9-E: 品質担保
- [ ] `./scripts/pre-push-check-all.sh` 実行
- [ ] Unit tests合格確認
- [ ] Git commit（Phase 9変更）

---

## 💡 今後の拡張案

### Phase 10候補: Dynamic API Discovery

**コンセプト**: ユーザーが登録したAPI keyに基づいて動的に利用可能APIを判定

**実装案**:
1. myVaultからユーザー登録済みAPI keyリストを取得
2. 登録済みAPIを「利用可能」として評価に含める
3. 未登録APIは「実現困難だが、API key登録で実装可能」と案内

**メリット**:
- ユーザーごとにカスタマイズされた評価
- Slack/Notion等の外部サービス連携の自動判定
- ユーザー体験の向上

**実装難易度**: 中（myVault連携API実装が必要）

---

## 📚 参考資料

- **Phase 8結果**: `./dev-reports/feature/issue/97/phase-8-results.md`
- **Fresh Scenarios Report**: `./dev-reports/feature/issue/97/fresh-scenarios-report.md`
- **GraphAI Capabilities**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/config/graphai_capabilities.yaml`
- **Expert Agent Capabilities**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/config/expert_agent_capabilities.yaml`
- **Infeasible Tasks**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/config/infeasible_tasks.yaml`
- **Evaluation Prompt**: `expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/prompts/evaluation.py`

---

**次のアクション**: ユーザー承認を待って Phase 9-A の実装開始
