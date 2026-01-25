# Phase 4 作業計画: sourceノード修正後のワークフロー再生成・動作確認

**作成日**: 2025-10-26
**ブランチ**: feature/issue/110
**前提条件**: workflowGeneratorAgentsプロンプト修正完了（sourceノード設定とuser_input参照）

---

## 📊 修正内容サマリー

### ✅ 今回の修正（Phase 4 準備完了）

**修正ファイル**: `expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py`

**主要な変更点**:

1. **「Required Nodes」セクションの強化** (line 116-118):
   - `source: {}` が必須であることを明示
   - user_inputがAPIリクエストから注入されることを記載

2. **「sourceNode and user_input Reference」セクションの追加** (line 120-130):
   - `source: {}` を常に定義することを強調（CRITICAL）
   - オブジェクト形式のuser_input（推奨）の説明を追加
     - 例: `{"user_input": {"test": "value1", "test2": "value2"}}`
     - `:source.property_name` でのアクセス方法を具体例付きで記載
   - 文字列形式のuser_input（非推奨）の説明を追加
   - `jsonParserAgent`を使用しないことを注意喚起

3. **実例の追加** (line 150-169):
   - ユーザーが提供した例と同様のワークフローYAML構造を追加
   - `source: {}` が必須であることを強調
   - `:source.test2` でのプロパティアクセス方法を示す

**品質チェック結果**:
- ✅ **Ruff linting**: All checks passed
- ✅ **MyPy type checking**: Success (no issues found)

---

## 🎯 Phase 4 の目的

### 主目的

**修正版プロンプトでシナリオ4の全6タスクのワークフローを再生成し、動作確認を完了する**

### 具体的目標

1. ✅ **sourceノード設定の正確性**: すべてのYAMLで `source: {}` が設定される
2. ✅ **user_input参照の正確性**: `:source.property_name` でのアクセスが正しく実装される
3. ✅ **YAML構文エラーゼロ**: Phase 2の成果を維持
4. ✅ **ワークフロー実行成功**: 最低1タスクでGraphAI実行成功
5. 📊 **品質評価**: 自動生成品質の向上を数値で測定

---

## 📋 対象タスク一覧（シナリオ4）

| # | TaskMaster ID | タスク名 | 説明 | 優先度 |
|---|--------------|---------|------|-------|
| 1 | `tm_01K8DXE601HMZWW0K5HR9FDYCQ` | キーワード分析と構成案作成 | キーワードからポッドキャスト構成案を作成 | 🔴 最優先 |
| 2 | `tm_01K8DXE60MMZW6PTEFX2EXQB1E` | ポッドキャストスクリプトの生成 | 構成案からスクリプト（台本）を生成 | 🟡 高 |
| 3 | `tm_01K8DXE614QCAMG90V7Y9XHMXC` | 音声コンテンツの生成 | TTSエンジンでMP3音声ファイル生成 | 🟡 高 |
| 4 | `tm_01K8DXE61HWT5JKMTQBHDY31EB` | ホスティングとリンク取得 | クラウドストレージにアップロード・URL取得 | 🟢 中 |
| 5 | `tm_01K8DXE6219B7KJKNZZHZ07Q1B` | メールコンテンツの作成 | メール件名・本文を作成 | 🟢 中 |
| 6 | `tm_01K8DXE62F5HG3T16GS2GFQD2W` | メール送信 | SMTP/メールAPIで送信 | 🟢 中 |

---

## 🛠️ Phase 4 タスク分解

### Task 4.1: 環境確認・事前準備 (30分)

#### 4.1.1 expertAgent APIサーバー確認

**実施内容**:
```bash
# サーバー起動確認
curl -X GET http://localhost:8104/health

# Workflow Generator API確認
curl -X POST http://localhost:8104/aiagent-api/v1/workflow-generator \
  -H "Content-Type: application/json" \
  -d '{"task_master_id": "tm_01K8DXE601HMZWW0K5HR9FDYCQ"}'
```

**期待される結果**:
- ✅ expertAgent APIサーバーが起動している
- ✅ Workflow Generator APIが正常応答

#### 4.1.2 データベース接続確認

**実施内容**:
- JobMaster ID `jm_01K8DXE62NFJNB0SHJZPAWQWVT` の存在確認
- TaskMaster 6件の存在確認
- InterfaceMaster 定義の確認

#### 4.1.3 作業ディレクトリ準備

**実施内容**:
```bash
mkdir -p /tmp/scenario4_workflows_phase4
mkdir -p /tmp/scenario4_test_results
```

---

### Task 4.2: シナリオ4ワークフロー一括再生成 (2-3時間)

#### 4.2.1 JobMaster単位での一括生成

**リクエスト**:
```bash
curl -X POST http://localhost:8104/aiagent-api/v1/workflow-generator \
  -H "Content-Type: application/json" \
  -d '{
    "job_master_id": "jm_01K8DXE62NFJNB0SHJZPAWQWVT"
  }' \
  | jq '.' > /tmp/scenario4_workflows_phase4/generation_result.json
```

**期待される出力**:
```json
{
  "status": "success",
  "workflows": [
    {
      "task_master_id": 123,
      "task_name": "キーワード分析と構成案作成",
      "workflow_name": "keyword_analysis",
      "yaml_content": "version: 0.5\nnodes:\n  source: {}\n  ...",
      "status": "success",
      "validation_result": {"is_valid": true},
      "retry_count": 0
    },
    // ... 5 more tasks
  ],
  "total_tasks": 6,
  "successful_tasks": 6,
  "failed_tasks": 0,
  "generation_time_ms": 120000.0
}
```

#### 4.2.2 生成されたYAMLの保存

**実施内容**:
```bash
# Python scriptでYAMLを個別ファイルに保存
python3 << 'EOF'
import json

with open('/tmp/scenario4_workflows_phase4/generation_result.json', 'r') as f:
    data = json.load(f)

for idx, workflow in enumerate(data['workflows'], 1):
    filename = f"/tmp/scenario4_workflows_phase4/task_{idx:03d}_{workflow['workflow_name']}.yaml"
    with open(filename, 'w') as wf:
        wf.write(workflow['yaml_content'])
    print(f"✅ Saved: {filename}")
EOF
```

#### 4.2.3 sourceノード設定の検証

**検証項目**:
- [ ] 全6ファイルで `source: {}` が設定されている
- [ ] `source: {}` が空オブジェクトである（パラメータなし）
- [ ] sourceノードが必ずnodes配列の最初に配置されている

**検証スクリプト**:
```bash
for file in /tmp/scenario4_workflows_phase4/task_*.yaml; do
  echo "Checking: $file"
  grep -q "source: {}" "$file" && echo "✅ source: {} found" || echo "❌ source: {} NOT found"
done
```

#### 4.2.4 user_input参照の検証

**検証項目**:
- [ ] `:source.property_name` でのプロパティアクセスが実装されている
- [ ] `jsonParserAgent` が使用されていない（不要な複雑化を避ける）
- [ ] `:source` 単体での文字列参照が使用されていない（オブジェクト形式推奨）

**検証スクリプト**:
```bash
for file in /tmp/scenario4_workflows_phase4/task_*.yaml; do
  echo "Checking: $file"
  grep -E ":source\.[a-zA-Z_]+" "$file" && echo "✅ :source.property_name found" || echo "⚠️  No :source.property_name reference"
  grep -q "jsonParserAgent" "$file" && echo "❌ jsonParserAgent found (should not be used)" || echo "✅ No jsonParserAgent"
done
```

---

### Task 4.3: 個別タスク動作確認 (3-4時間)

#### 4.3.1 タスク1: キーワード分析と構成案作成（最優先）

**目的**: 最もシンプルなタスクで動作確認

**GraphAIサーバーへのワークフロー登録**:
```bash
# GraphAIサーバーが起動していることを前提
curl -X POST http://localhost:8105/api/v1/workflow/register \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "keyword_analysis",
    "yaml_content": "'"$(cat /tmp/scenario4_workflows_phase4/task_001_keyword_analysis.yaml)"'"
  }'
```

**テスト実行**:
```bash
curl -X POST http://localhost:8105/api/v1/myagent/default/keyword_analysis \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": {
      "keyword": "AI技術の最新動向",
      "target_duration": "15分",
      "target_audience": "一般ビジネスパーソン"
    }
  }' \
  | jq '.' > /tmp/scenario4_test_results/task_001_result.json
```

**検証ポイント**:
- [ ] HTTP 200 OK が返される
- [ ] レスポンスに `results` フィールドが含まれる
- [ ] `results.output` に構成案JSONが含まれる
- [ ] エラーメッセージが含まれていない

**期待される出力例**:
```json
{
  "results": {
    "output": {
      "topic": "AI技術の最新動向",
      "sections": [
        {"title": "導入", "duration": "2分"},
        {"title": "最新のAI技術", "duration": "8分"},
        {"title": "まとめ", "duration": "5分"}
      ],
      "tone": "わかりやすく、親しみやすい",
      "target_audience": "一般ビジネスパーソン"
    }
  },
  "errors": {},
  "logs": []
}
```

#### 4.3.2 タスク2: ポッドキャストスクリプトの生成

**前提条件**: タスク1の出力を使用

**テスト実行**:
```bash
# タスク1の出力を取得
TASK1_OUTPUT=$(jq -c '.results.output' /tmp/scenario4_test_results/task_001_result.json)

curl -X POST http://localhost:8105/api/v1/myagent/default/podcast_script_generation \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": {
      "podcast_plan": '"$TASK1_OUTPUT"'
    }
  }' \
  | jq '.' > /tmp/scenario4_test_results/task_002_result.json
```

**検証ポイント**:
- [ ] 構成案（タスク1の出力）を正しく受け取る
- [ ] スクリプト（台本）が生成される
- [ ] 話者とセリフが含まれる

#### 4.3.3 タスク3: 音声コンテンツの生成

**前提条件**: タスク2の出力を使用

**テスト実行**:
```bash
TASK2_OUTPUT=$(jq -c '.results.output' /tmp/scenario4_test_results/task_002_result.json)

curl -X POST http://localhost:8105/api/v1/myagent/default/audio_generation \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": {
      "script": '"$TASK2_OUTPUT"'
    }
  }' \
  | jq '.' > /tmp/scenario4_test_results/task_003_result.json
```

**検証ポイント**:
- [ ] `/v1/utility/text_to_speech_drive` API連携が正しい
- [ ] 音声ファイル（MP3）が生成される
- [ ] Google DriveにアップロードされたURLが返される

**注意**:
- Google API認証が必要
- 認証情報がない場合はスキップ可能

#### 4.3.4 タスク4-6: 残りのタスク（時間があれば実施）

**タスク4**: ホスティングとリンク取得
**タスク5**: メールコンテンツの作成
**タスク6**: メール送信

**実施方針**:
- タスク1-3が成功した場合に実施
- 時間的制約がある場合はスキップ可能
- YAML生成とsourceノード設定の検証が主目的

---

### Task 4.4: End-to-End 動作確認（オプション） (2-3時間)

#### 4.4.1 全タスク連携テスト

**目的**: シナリオ4の全フローを通して実行

**テストシナリオ**:
1. ユーザーがキーワード "機械学習の基礎" を入力
2. タスク1で構成案生成
3. タスク2でスクリプト生成
4. タスク3で音声ファイル生成
5. タスク4でGoogle Driveにアップロード
6. タスク5でメールコンテンツ作成
7. タスク6でメール送信

**実施条件**:
- ✅ expertAgent APIサーバーが起動
- ✅ GraphAIサーバーが起動
- ✅ Google API認証情報が設定済み
- ✅ テスト用Gmailアカウントが利用可能

**実施内容**:
```bash
# E2Eテストスクリプト
bash << 'EOF'
#!/bin/bash
set -e

echo "=== シナリオ4 E2Eテスト開始 ==="

# Step 1: キーワード分析
echo "Step 1: キーワード分析"
TASK1_RESULT=$(curl -s -X POST http://localhost:8105/api/v1/myagent/default/keyword_analysis \
  -H "Content-Type: application/json" \
  -d '{"user_input": {"keyword": "機械学習の基礎"}}')
echo "$TASK1_RESULT" | jq '.'

# Step 2: スクリプト生成
echo "Step 2: スクリプト生成"
TASK1_OUTPUT=$(echo "$TASK1_RESULT" | jq -c '.results.output')
TASK2_RESULT=$(curl -s -X POST http://localhost:8105/api/v1/myagent/default/podcast_script_generation \
  -H "Content-Type: application/json" \
  -d '{"user_input": {"podcast_plan": '"$TASK1_OUTPUT"'}}')
echo "$TASK2_RESULT" | jq '.'

# Step 3-6: 以下同様に実行...

echo "=== E2Eテスト完了 ==="
EOF
```

#### 4.4.2 異常系テスト

**テストケース**:
- [ ] 不正なキーワード入力（空文字列、特殊文字）
- [ ] タスク間のデータ不整合（スキーマ違反）
- [ ] API エラー（TTS API、Gmail API）
- [ ] タイムアウト（長時間処理）

---

### Task 4.5: 結果評価・ドキュメント作成 (2時間)

#### 4.5.1 評価指標の測定

| 評価項目 | Phase 2実績 | Phase 4目標 | Phase 4実績 | 改善率 |
|---------|------------|-----------|-----------|--------|
| **sourceノード設定率** | - | 100% (6/6) | XX% | - |
| **user_input参照正確性** | - | 100% (6/6) | XX% | - |
| **YAML構文エラー** | 0件 | 0件 | XX件 | - |
| **ワークフロー実行成功率** | 0% (0/6) | ≥16.7% (1/6) | XX% | +XX% |
| **平均生成時間** | 109.4秒/タスク | <120秒/タスク | XX秒 | XX% |
| **Self-repair平均リトライ回数** | - | <1回 | XX回 | - |

#### 4.5.2 Phase 2 vs Phase 4 比較

**Phase 2（モデル切り替え前）**:
- ✅ YAML構文エラー: 0件
- ❌ 複数行文字列記法: 誤
- ❌ ワークフロー実行: HTTP 500発生（全タスク失敗）

**Phase 4（プロンプト修正後）**:
- ✅ YAML構文エラー: XX件
- ✅ sourceノード設定: XX/6タスク
- ✅ user_input参照: XX/6タスク
- ✅ ワークフロー実行: XX/6タスク成功

#### 4.5.3 成果物ドキュメント

**必須ドキュメント**:
1. `phase-4-workflow-generation-results.md`: ワークフロー再生成結果
2. `phase-4-source-node-validation.md`: sourceノード設定検証レポート
3. `phase-4-execution-test-results.md`: 動作確認テスト結果
4. `phase-4-completion-report.md`: Phase 4完了報告

**成果物（YAML）**:
- `/tmp/scenario4_workflows_phase4/task_001_keyword_analysis.yaml`
- `/tmp/scenario4_workflows_phase4/task_002_podcast_script_generation.yaml`
- `/tmp/scenario4_workflows_phase4/task_003_audio_generation.yaml`
- `/tmp/scenario4_workflows_phase4/task_004_hosting_upload.yaml`
- `/tmp/scenario4_workflows_phase4/task_005_email_content.yaml`
- `/tmp/scenario4_workflows_phase4/task_006_email_send.yaml`

**成果物（テスト結果）**:
- `/tmp/scenario4_test_results/task_001_result.json`
- `/tmp/scenario4_test_results/task_002_result.json`
- （以下同様）

---

## ✅ 成功基準

### 必須要件（Phase 4最小目標）

- [ ] **sourceノード設定率**: 100% (6/6タスク)
- [ ] **YAML構文エラー**: 0件（Phase 2の成果を維持）
- [ ] **ワークフロー実行成功**: 最低1タスク（タスク1推奨）
- [ ] **プロンプト修正の効果確認**: `:source.property_name` 参照が実装される

### 推奨要件（Phase 4推奨目標）

- [ ] ワークフロー実行成功率: ≥50% (3/6タスク)
- [ ] タスク1-3の連携テスト成功
- [ ] 修正パターンの文書化

### オプション要件（Phase 4理想目標）

- [ ] ワークフロー実行成功率: 100% (6/6タスク)
- [ ] End-to-Endテスト完全成功
- [ ] 異常系テスト完了

---

## ⚠️ リスクと対策

### リスク1: expertAgent APIサーバーが起動していない

**リスク**: ワークフロー生成APIが利用できない

**対策**:
- Phase 4開始前に環境確認を実施（Task 4.1）
- サーバー起動手順を文書化
- ローカル開発環境でのテスト実施

### リスク2: GraphAIサーバーが利用不可

**リスク**: ワークフロー実行テストができない

**対策**:
- YAML生成と静的検証のみ実施
- 実行テストは別タスクに延期
- 最小構成でのローカルGraphAI環境構築

### リスク3: プロンプト修正が不十分

**リスク**: 再生成されたYAMLでも実行エラーが発生

**対策**:
- Few-shot Learning追加を検討
- エラーパターンを収集してプロンプト改善
- Self-repair loopの最大リトライ回数を増加（3→5回）

### リスク4: Google API認証情報がない

**リスク**: タスク3-6の実行テストができない

**対策**:
- タスク1-2のみ動作確認を実施
- モックデータでの部分検証
- 認証情報設定手順を文書化

### リスク5: 生成時間が長すぎる

**リスク**: Phase 2で平均109秒/タスク（6.6倍増加）

**対策**:
- タイムアウト設定を調整（現在200秒）
- 並列生成の検討（現在は直列）
- モデル切り替えの再検討（Gemini 2.0 Flash復帰）

---

## 📅 スケジュール

| Task | 内容 | 予定工数 | 優先度 | 開始予定 | 完了予定 |
|------|------|---------|-------|---------|---------|
| Task 4.1 | 環境確認・事前準備 | 30分 | 🔴 最優先 | 即時 | +30分 |
| Task 4.2 | ワークフロー一括再生成 | 2-3時間 | 🔴 最優先 | +30分 | +3.5時間 |
| Task 4.3 | 個別タスク動作確認 | 3-4時間 | 🟡 高 | +3.5時間 | +7.5時間 |
| Task 4.4 | E2E動作確認（オプション） | 2-3時間 | 🟢 中 | +7.5時間 | +10.5時間 |
| Task 4.5 | 結果評価・ドキュメント | 2時間 | 🟡 高 | +7.5時間 | +9.5時間 |

**総予定工数**:
- 必須タスク（4.1-4.3、4.5）: 7.5-9.5時間
- オプションタスク（4.4）: +2-3時間
- **合計**: 9.5-12.5時間

---

## 🔄 Phase 4 完了後の次のステップ

### 推奨される次のアクション

**ケース1: Phase 4が完全成功（6/6タスク実行成功）**
- ✅ 他シナリオ（1-3）への展開を実施
- ✅ CI/CD統合の検討
- ✅ パフォーマンス最適化

**ケース2: Phase 4が部分成功（1-5タスク実行成功）**
- 🔄 失敗タスクの個別対応（Phase 5）
- 🔄 プロンプトのさらなる改善
- 🔄 エラーハンドリング強化

**ケース3: Phase 4が未達成（0タスク実行成功）**
- ⚠️ 根本原因の再分析
- ⚠️ YAML手動修正でのパターン学習
- ⚠️ Few-shot Learning強化

---

## 📚 参考ドキュメント

**必須参照**:
- [ ] [GraphAI ワークフロー生成ルール](../../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [ ] [GraphAI Input Schema](../../../../graphAiServer/docs/GRAPHAI_INPUT_SCHEMA.md)
- [ ] [アーキテクチャ概要](../../../../docs/design/architecture-overview.md)

**推奨参照**:
- [ ] `workflow-generation-work-plan.md`: 元の作業計画（Phase 1-5全体）
- [ ] `phase-2-completion-report.md`: Phase 2の成果と課題
- [ ] `phase-3-work-plan.md`: Phase 3の計画（実行時エラー対応）

**関連コミット**:
- [ ] workflowGeneratorAgentsプロンプト修正コミット（今回の修正）

---

## 📝 ドキュメント管理

### 保存先

`dev-reports/feature/issue/110/`

### ファイル構成

```
dev-reports/feature/issue/110/
├── workflow-generation-work-plan.md          # 全体の作業計画
├── phase-2-completion-report.md              # Phase 2完了報告
├── phase-3-work-plan.md                      # Phase 3作業計画
├── phase-4-work-plan.md                      # 本ドキュメント
├── phase-4-workflow-generation-results.md    # Phase 4: 再生成結果
├── phase-4-source-node-validation.md         # Phase 4: sourceノード検証
├── phase-4-execution-test-results.md         # Phase 4: 実行テスト結果
└── phase-4-completion-report.md              # Phase 4: 完了報告
```

---

## ✅ チェックリスト

### Task 4.1: 環境確認

- [ ] expertAgent APIサーバー起動確認
- [ ] GraphAIサーバー起動確認（オプション）
- [ ] データベース接続確認
- [ ] 作業ディレクトリ準備

### Task 4.2: ワークフロー再生成

- [ ] JobMaster IDでのAPI呼び出し
- [ ] 6タスク全てのYAML取得
- [ ] YAMLファイル保存
- [ ] sourceノード設定検証（6/6）
- [ ] user_input参照検証（6/6）

### Task 4.3: 個別動作確認

- [ ] タスク1: キーワード分析（最優先）
- [ ] タスク2: スクリプト生成
- [ ] タスク3: 音声生成
- [ ] タスク4: ホスティング（時間があれば）
- [ ] タスク5: メールコンテンツ（時間があれば）
- [ ] タスク6: メール送信（時間があれば）

### Task 4.4: E2Eテスト（オプション）

- [ ] 全タスク連携テスト
- [ ] 異常系テスト
- [ ] パフォーマンス測定

### Task 4.5: 評価・ドキュメント

- [ ] 評価指標の測定
- [ ] Phase 2 vs Phase 4 比較
- [ ] 4つの成果物ドキュメント作成
- [ ] YAMLファイル・テスト結果の整理

---

**作成日**: 2025-10-26
**作成者**: Claude Code
**バージョン**: 1.0
**ステータス**: 作業計画立案完了 → 実施待ち
