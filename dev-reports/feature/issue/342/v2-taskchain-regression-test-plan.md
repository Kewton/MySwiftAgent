# V2 タスクチェーン 回帰テスト計画

**作成日**: 2026-01-09
**関連Issue**: #342
**前提ドキュメント**: `v2-taskchain-remediation-plan.md`

---

## 1. テスト目的

タスクチェーン修正による既存機能への影響を検証し、回帰を防止する。

---

## 2. テスト対象

### 2.1 修正対象コンポーネント

| コンポーネント | 修正内容 | 影響範囲 |
|--------------|---------|---------|
| `master_manager.py` | body_template形式変更 | 全Task 0 |
| `worker.py` | 出力抽出ロジック変更 | 全タスク |
| `yaml_generator.py` | 出力ノード命名規則追加 | 新規ワークフロー |

### 2.2 影響を受ける可能性のある機能

| 機能 | リスク | テスト優先度 |
|------|-------|------------|
| 単一タスクジョブ | 中 | 🔴 High |
| タスクチェーンジョブ | 高 | 🔴 High |
| GraphAIワークフロー直接実行 | 低 | 🟡 Medium |
| Job Generator V1 | 低 | 🟢 Low |
| スケジュールジョブ | 低 | 🟢 Low |

---

## 3. テストケース

### 3.1 単体テスト（CI自動実行）

#### 3.1.1 master_manager.py

| テストID | テスト内容 | 期待結果 | ファイル |
|---------|----------|---------|---------|
| UT-MM-01 | `_build_body_template(0)`の戻り値 | `user_input`が`{{job.body.user_input}}`を含む | `test_master_manager.py` |
| UT-MM-02 | `_build_body_template(1)`の戻り値 | `user_input`が`{{tasks[0].output_data}}`を含む | `test_master_manager.py` |
| UT-MM-03 | `_build_body_template(2)`の戻り値 | `user_input`が`{{tasks[1].output_data}}`を含む | `test_master_manager.py` |

```python
# expertAgent/tests/unit/test_job_generator_v2/test_master_manager.py

def test_build_body_template_task_0_uses_user_input():
    """Task 0のbody_templateがjob.body.user_inputを参照する"""
    manager = MasterManagerSubWorkflow(...)
    template = manager._build_body_template(0)
    assert template["user_input"] == "{{job.body.user_input}}"
    assert template["job_params"] == "{{job.body}}"

def test_build_body_template_task_1_uses_previous_output():
    """Task 1のbody_templateが前タスクの出力を参照する"""
    manager = MasterManagerSubWorkflow(...)
    template = manager._build_body_template(1)
    assert template["user_input"] == "{{tasks[0].output_data}}"

def test_build_body_template_task_2_uses_previous_output():
    """Task 2のbody_templateが前タスクの出力を参照する"""
    manager = MasterManagerSubWorkflow(...)
    template = manager._build_body_template(2)
    assert template["user_input"] == "{{tasks[1].output_data}}"
```

#### 3.1.2 worker.py

| テストID | テスト内容 | 期待結果 | ファイル |
|---------|----------|---------|---------|
| UT-WK-01 | `output`ノードからの抽出 | `output`の内容を返す | `test_worker.py` |
| UT-WK-02 | `output.result`からの抽出 | `result`の内容を返す | `test_worker.py` |
| UT-WK-03 | `output`ノードなしの場合 | 全`results`を返す | `test_worker.py` |
| UT-WK-04 | `format_output`ノード（isResult）からの抽出 | `format_output`の内容を返す | `test_worker.py` |

```python
# jobqueue/tests/unit/test_worker.py

def test_extract_graphai_output_with_output_node():
    """outputノードがある場合、その内容を抽出する"""
    response = {
        "results": {
            "source": {},
            "output": {"search_results": [1, 2, 3]}
        }
    }
    result = _extract_graphai_output(response)
    assert result == {"search_results": [1, 2, 3]}

def test_extract_graphai_output_with_nested_result():
    """output.resultがある場合、アンラップする"""
    response = {
        "results": {
            "output": {"result": {"data": "value"}}
        }
    }
    result = _extract_graphai_output(response)
    assert result == {"data": "value"}

def test_extract_graphai_output_without_output_node():
    """outputノードがない場合、全resultsを返す"""
    response = {
        "results": {
            "source": {},
            "format_output": {"data": "value"}
        }
    }
    result = _extract_graphai_output(response)
    assert "format_output" in result

def test_extract_graphai_output_with_isresult_node():
    """isResultノードを動的に検出する（Phase 2対応後）"""
    response = {
        "results": {
            "source": {},
            "format_output": {"search_results": [...]}
        },
        "logs": [
            {"nodeId": "format_output", "state": "completed"}
        ]
    }
    result = _extract_graphai_output(response)
    assert "search_results" in result
```

#### 3.1.3 yaml_generator.py

| テストID | テスト内容 | 期待結果 | ファイル |
|---------|----------|---------|---------|
| UT-YG-01 | 生成YAMLに`output`ノードが含まれる | `output`ノードが存在 | `test_yaml_generator.py` |
| UT-YG-02 | `output`ノードに`isResult: true`がある | 属性が設定されている | `test_yaml_generator.py` |

```python
# expertAgent/tests/unit/test_job_generator_v2/test_yaml_generator.py

def test_generated_workflow_has_output_node():
    """生成されたワークフローにoutputノードが含まれる"""
    generator = YAMLGenerator(...)
    yaml_content = generator.generate(...)
    assert "output:" in yaml_content
    assert "isResult: true" in yaml_content
```

---

### 3.2 結合テスト（CI自動実行）

| テストID | テスト内容 | 期待結果 | ファイル |
|---------|----------|---------|---------|
| IT-01 | 単一タスクジョブの実行 | ステータスがSUCCEEDED | `test_single_task_job.py` |
| IT-02 | 2タスクチェーンの実行 | 全タスクがSUCCEEDED | `test_task_chain.py` |
| IT-03 | 3タスクチェーンの実行 | 全タスクがSUCCEEDED | `test_task_chain.py` |
| IT-04 | body_template解決の検証 | 正しいデータがgraphAiServerに送信される | `test_template_resolution.py` |

```python
# expertAgent/tests/integration/test_task_chain.py

@pytest.mark.integration
async def test_two_task_chain_execution():
    """2タスクチェーンが正常に実行される"""
    # Task 0の出力がTask 1に正しく渡されることを検証
    job_id = await create_job_from_master(job_master_id)
    await wait_for_job_completion(job_id, timeout=120)

    tasks = await get_job_tasks(job_id)
    assert len(tasks) == 2
    assert all(t["status"] == "SUCCEEDED" for t in tasks)

    # Task 0の出力がTask 1の入力になっていることを検証
    task_0_output = tasks[0]["output_data"]
    # Task 1がTask 0の出力を正しく受け取ったことを確認

@pytest.mark.integration
async def test_three_task_chain_execution():
    """3タスクチェーンが正常に実行される"""
    job_id = await create_job_from_master(job_master_id)
    await wait_for_job_completion(job_id, timeout=180)

    tasks = await get_job_tasks(job_id)
    assert len(tasks) == 3
    assert all(t["status"] == "SUCCEEDED" for t in tasks)
```

---

### 3.3 受入テスト（ローカル実行）

| テストID | テスト内容 | 期待結果 | ファイル |
|---------|----------|---------|---------|
| AT-01 | Google検索→要約→メール送信チェーン | 全タスク成功、メール送信完了 | `test_issue_342_acceptance.py` |
| AT-02 | 既存単一タスクJob Masterの実行 | 既存動作が維持される | `test_regression_single_task.py` |
| AT-03 | 既存タスクチェーンJob Masterの実行 | 既存動作が維持される | `test_regression_task_chain.py` |

```python
# expertAgent/tests/acceptance/test_issue_342_acceptance.py

@pytest.mark.acceptance
async def test_google_search_summarize_email_chain():
    """Google検索→要約→メール送信のタスクチェーンが成功する"""
    # 1. Job作成
    job_id = await create_job_from_master(
        "jm_01KEH9NMY2WHPPSBFV9W5D2R3V",
        body={"user_input": {"query": "テストクエリ"}}
    )

    # 2. 完了待機
    await wait_for_job_completion(job_id, timeout=300)

    # 3. 全タスクの成功を確認
    tasks = await get_job_tasks(job_id)
    for task in tasks:
        assert task["status"] == "SUCCEEDED", f"Task {task['order']} failed"

    # 4. Task 0の出力にsearch_resultsが含まれることを確認
    assert "search_results" in tasks[0]["output_data"] or \
           any("search" in str(v).lower() for v in tasks[0]["output_data"].values())

    # 5. Task 2の出力にメール送信結果が含まれることを確認
    assert tasks[2]["status"] == "SUCCEEDED"
```

---

## 4. 回帰テスト実行計画

### 4.1 Phase 1 修正後

| テスト種別 | 実行タイミング | 担当 |
|-----------|--------------|------|
| 単体テスト | PR作成時 | CI |
| 結合テスト | PR作成時 | CI |
| 受入テスト | PRマージ前 | 開発者（ローカル） |

**実行コマンド**:
```bash
# 単体テスト
cd expertAgent && uv run pytest tests/unit/test_job_generator_v2/ -v
cd jobqueue && uv run pytest tests/unit/test_worker.py -v

# 結合テスト
cd expertAgent && uv run pytest tests/integration/ -v -m integration

# 受入テスト（ローカル）
make acceptance-test-agent
```

### 4.2 Phase 2 修正後

| テスト種別 | 追加テスト | 理由 |
|-----------|----------|------|
| 単体テスト | isResult検出テスト | worker.py変更 |
| 結合テスト | format_output対応テスト | 出力ノード名の柔軟化 |

### 4.3 Phase 3 修正後

| テスト種別 | 追加テスト | 理由 |
|-----------|----------|------|
| 単体テスト | 静的パラメータ抽出テスト | decomposer.py変更 |
| E2Eテスト | 全タスクチェーンパターン | 全機能の統合検証 |

---

## 5. テスト環境

### 5.1 必要なサービス

| サービス | ポート | 必須 |
|---------|-------|------|
| jobqueue | 8101 | ✅ |
| myVault | 8103 | ✅ |
| expertAgent | 8104 | ✅ |
| graphAiServer | 8105 | ✅ |

### 5.2 環境変数

```bash
# .env.test
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
JOBQUEUE_BASE_URL=http://localhost:8101
MYVAULT_BASE_URL=http://localhost:8103
```

### 5.3 起動手順

```bash
# ハイブリッド起動（推奨）
./scripts/dev-hybrid.sh

# またはDocker起動
make dev-all
```

---

## 6. 合格基準

### 6.1 Phase 1 完了基準

| 項目 | 基準 |
|-----|------|
| 単体テスト | 全テストPASS |
| 結合テスト | 全テストPASS |
| 受入テスト | AT-01, AT-02, AT-03 PASS |
| カバレッジ | 修正コードのカバレッジ90%以上 |

### 6.2 全体完了基準

| 項目 | 基準 |
|-----|------|
| 全テスト | PASS |
| 既存テスト | 回帰なし |
| E2Eテスト | 3タスクチェーン成功 |

---

## 7. リスクと対策

| リスク | 影響 | 対策 |
|-------|-----|------|
| 既存Job Masterの破壊 | 高 | 既存Job Masterの動作確認テスト追加 |
| body_template変更の副作用 | 中 | 単一タスクジョブの回帰テスト |
| isResult検出の誤動作 | 中 | outputノード優先探索で後方互換性確保 |

---

## 8. テスト結果記録

### 8.1 結果記録フォーマット

| 日付 | Phase | テスト種別 | 結果 | 備考 |
|-----|-------|----------|------|------|
| YYYY-MM-DD | 1 | 単体テスト | PASS/FAIL | |
| YYYY-MM-DD | 1 | 結合テスト | PASS/FAIL | |
| YYYY-MM-DD | 1 | 受入テスト | PASS/FAIL | |

### 8.2 失敗時の対応

1. 失敗テストのログを保存
2. 根本原因を特定
3. 修正を実施
4. 再テスト実行
5. 結果を記録

---

## 9. 関連ドキュメント

- `v2-taskchain-root-cause-analysis.md` - 根本原因分析
- `v2-taskchain-remediation-plan.md` - 対策案
- `taskchain-data-contract.md` - データ契約仕様
