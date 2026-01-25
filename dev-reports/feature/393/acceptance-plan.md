# 受入テスト計画書

**Issue**: #393
**作成日**: 2026-01-22
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #393
- **タイトル**: Tech Debt: Issue #361 Phase 2 未完了 - workflow_gen ディレクトリの削除
- **プロジェクト**: expertAgent
- **タイプ**: 内部リファクタリング（技術的負債解消）

### 参照ドキュメント
- Issue: #393
- 設計方針書: `expertAgent/dev-reports/feature/issue/393/design-policy.md`
- 作業計画書: `expertAgent/dev-reports/feature/issue/393/work-plan.md`

### リファクタリングの概要
`workflow_gen/workflow_registrar.py` の `update_task_master_body_template_taskflow` 関数を `registration/task_master_utils.py` に移動し、インポートパスを更新する。

---

## 2. 単体テスト結果レビュー

**注**: PRE-TDD フェーズのため、TDD実装後に更新されます。

### カバレッジ
- 現在: TDD実装後に確認
- 目標: 90%
- 判定: TDD実装後に判定

### テスト品質評価（TDD実装後に更新）
| 指標 | 値 | 判定 |
|------|-----|------|
| 総テスト数 | - | - |
| 影響テスト数 | 2ファイル | - |
| 新規テスト数 | - | - |

### TDD実装で確認すべき項目
1. `task_master_utils.py` の単体テスト
2. 後方互換性の re-export テスト
3. 既存テストのインポートパス更新後の動作

---

## 3. 受入条件分析

### AC-1: 関数の移動
- **原文**: `update_task_master_body_template_taskflow` 関数が `registration/task_master_utils.py` に移動されている
- **分類**: 機能要件（リファクタリング）
- **テスト方法**: コード構造確認 + インポート確認
- **モック使用**: 不可
- **検証ポイント**:
  1. `registration/task_master_utils.py` が存在する
  2. 関数が正しく定義されている
  3. 関数が正しくインポートできる

### AC-2: インポートパス更新
- **原文**: 全ての import パスが新しい場所を参照している
- **分類**: 機能要件（リファクタリング）
- **テスト方法**: grep による検索 + インポートテスト
- **モック使用**: 不可
- **検証ポイント**:
  1. `workflow_gen/workflow.py` のインポートパスが更新済み
  2. テストファイルのインポートパスが更新済み
  3. 旧パスへの参照が残っていない（re-export以外）

### AC-3: 後方互換性
- **原文**: 後方互換性の re-export が `workflow_gen/workflow_registrar.py` に実装されている（DeprecationWarning 付き）
- **分類**: 機能要件
- **テスト方法**: Python インポートテスト
- **モック使用**: 不可
- **検証ポイント**:
  1. 旧パスからのインポートが動作する
  2. DeprecationWarning が発生する
  3. 関数は正常に動作する

### AC-4: 全テストパス
- **原文**: 全テスト（単体・結合）がパスする
- **分類**: 非機能要件（品質保証）
- **テスト方法**: pytest実行
- **モック使用**: 該当なし
- **検証ポイント**:
  1. 単体テストがすべてパス
  2. 結合テストがすべてパス
  3. skipped テストがないこと

### AC-5: 静的解析
- **原文**: 静的解析エラーがない
- **分類**: 非機能要件（コード品質）
- **テスト方法**: Ruff, MyPy 実行
- **モック使用**: 該当なし
- **検証ポイント**:
  1. Ruff エラーが 0 件
  2. MyPy エラーが 0 件

---

## 4. 設計方針検証

### DP-1: ファイル配置の整合性
- **設計方針**: `update_task_master_body_template_taskflow` 関数は TaskFlow V2 関連のため `registration/` ディレクトリに配置
- **検証方法**: ファイル構造確認
- **テスト項目**:
  1. `registration/task_master_utils.py` が存在すること
  2. 関数が正しく定義されていること
  3. `registration/__init__.py` でエクスポートされていること

### DP-2: 設定値の取得元
- **設計方針**: `JOBQUEUE_API_URL` は `settings` モジュールから取得
- **検証方法**: コード確認
- **テスト項目**:
  1. `task_master_utils.py` で `settings` モジュールからインポートしていること
  2. 環境変数のフォールバック値が正しいこと（`http://localhost:8001`）

### DP-3: 後方互換性の実装
- **設計方針**: 旧パスからのインポートは DeprecationWarning を出力しつつ動作を維持
- **検証方法**: Python インポートテスト
- **テスト項目**:
  1. `workflow_registrar.py` に re-export が存在すること
  2. DeprecationWarning が適切なメッセージで発生すること
  3. 関数呼び出しが正常に動作すること

---

## 5. デッドコード検証計画

### F-1: update_task_master_body_template_taskflow
- **ファイル**: `registration/task_master_utils.py`
- **種別**: function
- **期待される呼び出し元**:
  - `workflow_gen/workflow.py`
  - テストファイル
- **検証方法**:
  ```bash
  # 呼び出し箇所を確認
  grep -rn "update_task_master_body_template_taskflow" --include="*.py" expertAgent/
  ```
- **E2Eでの確認方法**:
  - Job Generator V2 API を実行し、TaskMaster の body_template が更新されることを確認
  - ただし、リファクタリングIssueのため、既存機能の動作確認がメイン

### F-2: JOBQUEUE_API_URL 定数
- **ファイル**: `registration/task_master_utils.py`
- **種別**: constant
- **期待される呼び出し元**: `update_task_master_body_template_taskflow` 関数内
- **検証方法**:
  ```bash
  grep -rn "JOBQUEUE_API_URL" --include="*.py" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/
  ```
- **E2Eでの確認方法**: 関数実行時に JobQueue API に正しくアクセスできることで間接確認

---

## 6. テスト環境

### リファクタリングIssueのテスト方法

このIssueは内部リファクタリングであり、外部インターフェースに変更はありません。
受入テストは以下の方法で実施します：

1. **静的検証**: コード構造・インポートパスの確認
2. **自動テスト**: 単体・結合テストの実行
3. **後方互換性テスト**: Python インポートテスト

### 必須サービス（E2E確認が必要な場合）
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| expertAgent | http://localhost:8004 | GET /health |
| jobqueue | http://localhost:8001 | GET /health |

### 起動コマンド（E2E確認が必要な場合）

```bash
# 1. 既存サービスを停止
./scripts/dev-hybrid.sh stop --local-only

# 2. ローカルモードでサービスを起動
./scripts/dev-hybrid.sh start --local-only
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| JOBQUEUE_API_URL | JobQueue API URL | No (default: http://localhost:8001) |

---

## 7. テスト項目

### TC-001: 新規ファイル存在確認
- **テスト観点**: 関数が正しい場所に移動されたか
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 静的検証
- **テスト方法**: ファイルシステム確認
- **前提条件**:
  1. TDD実装が完了している
- **テスト手順**:
  1. `registration/task_master_utils.py` の存在確認
  2. 関数定義の存在確認
- **期待結果**:
  - ファイルが存在する
  - `update_task_master_body_template_taskflow` 関数が定義されている
- **検証コマンド**:
  ```bash
  # ファイル存在確認
  ls expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py

  # 関数定義確認
  grep -n "async def update_task_master_body_template_taskflow" \
    expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py
  ```
- **pytestメソッド**: N/A（静的検証）

### TC-002: インポートパス更新確認
- **テスト観点**: 全ての参照箇所が新パスを使用しているか
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-1
- **テスト種別**: 静的検証
- **テスト方法**: grep検索
- **前提条件**:
  1. TDD実装が完了している
- **テスト手順**:
  1. 新パスからのインポート箇所を確認
  2. 旧パスからのインポート箇所を確認（re-export以外）
- **期待結果**:
  - `workflow_gen/workflow.py` が新パスを使用
  - テストファイルが新パスを使用
  - 旧パスへの直接参照がない（re-export除く）
- **検証コマンド**:
  ```bash
  # 新パスの使用確認
  grep -rn "from.*registration.*task_master_utils.*import.*update_task_master_body_template_taskflow" \
    --include="*.py" expertAgent/

  # 旧パスの使用確認（re-export以外）
  grep -rn "from.*workflow_gen.*workflow_registrar.*import.*update_task_master_body_template_taskflow" \
    --include="*.py" expertAgent/ | grep -v "workflow_registrar.py"
  ```
- **pytestメソッド**: N/A（静的検証）

### TC-003: 後方互換性の動作確認
- **テスト観点**: 旧パスからのインポートが DeprecationWarning 付きで動作するか
- **関連する受入条件**: AC-3
- **関連する設計方針**: DP-3
- **テスト種別**: 単体テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了している
- **テスト手順**:
  1. 旧パスからインポート
  2. DeprecationWarning の発生確認
  3. 関数が正常にインポートされることを確認
- **期待結果**:
  - DeprecationWarning が発生
  - 警告メッセージに移行先パスが含まれる
  - 関数は正常に使用可能
- **Pythonテストコード**:
  ```python
  import warnings

  def test_backward_compatibility_deprecation_warning():
      with warnings.catch_warnings(record=True) as w:
          warnings.simplefilter("always")
          from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
              update_task_master_body_template_taskflow
          )
          assert len(w) == 1
          assert issubclass(w[-1].category, DeprecationWarning)
          assert "registration.task_master_utils" in str(w[-1].message)
          assert update_task_master_body_template_taskflow is not None
  ```
- **pytestメソッド**: `test_backward_compatibility_deprecation_warning`

### TC-004: 単体テスト全パス確認
- **テスト観点**: 既存テストが変更後も正常に動作するか
- **関連する受入条件**: AC-4
- **関連する設計方針**: N/A
- **テスト種別**: 自動テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了している
  2. インポートパスが更新されている
- **テスト手順**:
  1. expertAgent の単体テストを実行
  2. 結果を確認
- **期待結果**:
  - 全テストがパス
  - skipped が 0
  - failures が 0
- **実行コマンド**:
  ```bash
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
    uv run pytest tests/unit/ -v --tb=short
  ```
- **pytestメソッド**: N/A（テストスイート実行）

### TC-005: 結合テスト全パス確認
- **テスト観点**: 結合テストが変更後も正常に動作するか
- **関連する受入条件**: AC-4
- **関連する設計方針**: N/A
- **テスト種別**: 自動テスト
- **テスト方法**: pytest
- **前提条件**:
  1. TDD実装が完了している
  2. インポートパスが更新されている
- **テスト手順**:
  1. expertAgent の結合テストを実行
  2. 結果を確認
- **期待結果**:
  - 全テストがパス
  - skipped が 0
  - failures が 0
- **実行コマンド**:
  ```bash
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
    uv run pytest tests/integration/ -v --tb=short
  ```
- **pytestメソッド**: N/A（テストスイート実行）

### TC-006: 静的解析エラー確認
- **テスト観点**: コード品質が維持されているか
- **関連する受入条件**: AC-5
- **関連する設計方針**: N/A
- **テスト種別**: 静的解析
- **テスト方法**: Ruff, MyPy
- **前提条件**:
  1. TDD実装が完了している
- **テスト手順**:
  1. Ruff を実行
  2. MyPy を実行
- **期待結果**:
  - Ruff エラー: 0件
  - MyPy エラー: 0件
- **実行コマンド**:
  ```bash
  # Ruff
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
    uv run ruff check aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py

  # MyPy
  cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/expertAgent && \
    uv run mypy aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py
  ```
- **pytestメソッド**: N/A（静的解析）

### TC-007: 設定値取得確認
- **テスト観点**: JOBQUEUE_API_URL が settings モジュールから正しく取得されているか
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-2
- **テスト種別**: 静的検証
- **テスト方法**: コード確認
- **前提条件**:
  1. TDD実装が完了している
- **テスト手順**:
  1. `task_master_utils.py` で settings モジュールからインポートしていることを確認
  2. フォールバック値が正しいことを確認
- **期待結果**:
  - `from aiagent.langgraph.jobGeneratorV2.workflows.common import settings` が存在
  - `JOBQUEUE_API_URL = settings.JOBQUEUE_API_URL or "http://localhost:8001"` が存在
- **検証コマンド**:
  ```bash
  grep -n "from.*common import settings" \
    expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py

  grep -n "JOBQUEUE_API_URL.*settings.*localhost:8001" \
    expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/task_master_utils.py
  ```
- **pytestメソッド**: N/A（静的検証）

### TC-008: registration/__init__.py エクスポート確認
- **テスト観点**: 関数が正しくエクスポートされているか
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1
- **テスト種別**: 静的検証
- **テスト方法**: コード確認
- **前提条件**:
  1. TDD実装が完了している
- **テスト手順**:
  1. `registration/__init__.py` でエクスポートされていることを確認
- **期待結果**:
  - `update_task_master_body_template_taskflow` が `__all__` に含まれる
  - または適切にインポート・エクスポートされている
- **検証コマンド**:
  ```bash
  grep -n "update_task_master_body_template_taskflow" \
    expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/__init__.py
  ```
- **pytestメソッド**: N/A（静的検証）

---

## 8. テスト実行計画

### 実行順序

1. **静的検証**（TC-001, TC-002, TC-007, TC-008）
   - ファイル存在確認
   - インポートパス確認
   - コード構造確認

2. **静的解析**（TC-006）
   - Ruff 実行
   - MyPy 実行

3. **自動テスト**（TC-003, TC-004, TC-005）
   - 後方互換性テスト
   - 単体テスト
   - 結合テスト

### 成功基準

- [x] TC-001: 新規ファイルが存在し、関数が定義されている
- [x] TC-002: 全インポートパスが更新されている
- [x] TC-003: 後方互換性の DeprecationWarning が動作する
- [x] TC-004: 全単体テストがパス
- [x] TC-005: 全結合テストがパス
- [x] TC-006: 静的解析エラーが 0 件
- [x] TC-007: 設定値が正しく取得されている
- [x] TC-008: エクスポートが正しく設定されている

---

## 9. 補足事項

### リファクタリングIssueの特性

このIssueは内部リファクタリングであり、以下の特性があります：

1. **外部インターフェース変更なし**: API の入出力に変更はない
2. **機能変更なし**: 既存機能の動作に変更はない
3. **後方互換性維持**: 旧パスからのインポートも DeprecationWarning 付きで動作

### E2E テストの位置づけ

本Issueでは、以下の理由によりE2Eテストは必須ではありません：

1. 外部インターフェースに変更がない
2. 既存の単体・結合テストで十分カバーされている
3. 静的検証でリファクタリングの正確性を確認できる

ただし、万が一動作に問題がある場合は、work-plan.md に記載の L3 受入テストを実行してください。

### 将来の作業

- `workflow_gen/` ディレクトリの完全整理は別 Issue（未起票）で対応予定
- 後方互換性の re-export は将来的に削除予定（DeprecationWarning で事前通知済み）

---

## 10. チェックリスト

### TDD実装前（PRE-TDD）
- [x] 受入条件を分析済み
- [x] 設計方針との整合性確認項目を作成済み
- [x] デッドコード検証計画を作成済み
- [x] テスト項目を作成済み

### TDD実装後（POST-TDD）
- [ ] 単体テスト結果をレビュー済み
- [ ] カバレッジ目標達成を確認済み
- [ ] 全テスト項目を実行済み
- [ ] 全テスト項目がパス

---

**計画作成完了**: 2026-01-22
**次のステップ**: TDD実装フェーズへ進む
