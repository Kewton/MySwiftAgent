# バグ修正レポート: Priority型不整合によるテスト失敗

## 概要

| 項目 | 値 |
|------|-----|
| **バグID** | 20260126_priority_type_mismatch |
| **関連Issue** | #402 (topological_sort導入) |
| **影響テスト数** | 11件 |
| **報告日** | 2026-01-26 |
| **ステータス** | 完了 |

---

## 不具合内容

### エラー詳細

```
ValueError: invalid literal for int() with base 10: 'high'
  File topological_sort.py, line 72, in priority:
    return int(self._dict.get('priority', 5))
```

### 影響を受けたテスト

| テストファイル | 失敗テスト数 |
|---------------|-------------|
| test_master_creation_node.py | 7 |
| test_node_contracts.py | 3 |
| test_job_generator_endpoints.py | 1 |
| **合計** | **11** |

---

## 根本原因分析（5 Whys）

| Why | 質問 | 回答 |
|-----|------|------|
| Why 1 | なぜValueErrorが発生するか？ | `topological_sort.py`の`priority`プロパティが`int('high')`を実行 |
| Why 2 | なぜint('high')が呼ばれるか？ | `mock_helpers.py`が`priority='high'`(文字列)を返すが、`topological_sort.py`はint型を期待 |
| Why 3 | なぜ型の不整合が存在するか？ | Issue #402で`topological_sort.py`が追加された際、`mock_helpers.py`が更新されなかった |
| Why 4 | なぜmock_helpers.pyが更新されなかったか？ | Issue #402のTDD実行時に`test_master_creation_node.py`等が実行されなかった |
| **Why 5** | **なぜこれらのテストが実行されなかったか？** | **PM Auto-Devワークフローが「関連テストのみ」を実行し、変更影響を受ける既存テストを検出・実行していなかった** |

### 根本原因

1. **技術的原因**: `mock_helpers.py`の`priority`フィールドが文字列型だが、`topological_sort.py`は整数型を期待
2. **プロセス的原因**: Issue実装時にリグレッションテスト（全テスト実行）が行われていない
3. **組織的原因**: PM Auto-Devワークフローに変更影響分析と変更影響テストのフェーズがない

---

## 修正内容

### 1. mock_helpers.py の修正（即時対応）

**ファイル**: `expertAgent/tests/utils/mock_helpers.py`

```python
# Before:
"priority": "high" if i == 1 else "medium",

# After:
"priority": 1 if i == 1 else 5,  # Integer: 1=high, 5=medium (default)
```

**テスト結果**: 33/33 passed

---

### 2. PM Auto-Devワークフロー改善（再発防止策）

**ファイル**: `.claude/commands/pm-auto-dev.md`

**追加内容**: Phase 2.9「変更影響テスト実行」を新設

```markdown
### Phase 2.9: 変更影響テスト実行【必須】（Issue #402教訓）

**目的**: TDD実装で変更したファイルに依存する既存テストを自動検出・実行し、
意図しない破壊を早期発見します。

#### 手順:
1. TDD実装で変更されたファイルを特定
2. 変更ファイルをimportしているテストを自動検出
3. 依存テストをすべて実行
4. 全単体テストを実行（推奨）
```

---

### 3. CLAUDE.md リグレッションテスト必須化（再発防止策）

**ファイル**: `CLAUDE.md`

**追加内容**:

1. Issue完遂チェックリストに「変更影響テスト全パス」を追加
2. 新セクション「変更影響テスト必須化ルール（Issue #402教訓）」を追加

```markdown
## 変更影響テスト必須化ルール（Issue #402教訓）

### 必須ルール
| チェック項目 | 実行タイミング | 確認コマンド |
|-------------|---------------|-------------|
| **変更影響テスト実行** | TDD完了後、受入テスト前 | 下記参照 |
| **全単体テストパス** | Issue完了前 | `uv run pytest tests/unit/ -v` |
```

---

### 4. CI設定確認（既存で対応済み）

**ファイル**: `.github/workflows/ci-feature.yml`

**確認結果**: PRマージ前に全テストが実行される設定が既に存在

```yaml
- name: Run tests with coverage
  run: uv run pytest tests/ -v --cov=app --cov-report=xml --ignore=tests/acceptance
```

---

## 成果物チェックリスト

| 成果物 | ステータス | 備考 |
|--------|----------|------|
| mock_helpers.py 修正 | ✅ 完了 | priority型を整数に変更 |
| pm-auto-dev.md 更新 | ✅ 完了 | Phase 2.9 追加 |
| CLAUDE.md 更新 | ✅ 完了 | 変更影響テストルール追加 |
| CI設定確認 | ✅ 確認済 | 既存で全テスト実行対応 |
| テスト全パス | ✅ 確認済 | 33/33 passed |
| 静的解析 | ✅ 確認済 | Ruff: All checks passed |

---

## 再発防止の効果

### Before（Issue #402時点）

```
Phase 2: TDD実装
  ↓
Phase 3: 受入テスト ← 関連テストのみ実行、既存テストは未実行
  ↓
マージ → 11件のテスト失敗が後で発覚
```

### After（本修正後）

```
Phase 2: TDD実装
  ↓
Phase 2.9: 変更影響テスト実行【新設】
  - 変更ファイルに依存するテストを自動検出
  - 全単体テストを実行
  ↓
Phase 3: 受入テスト
  ↓
マージ → 変更影響による失敗は事前に検出
```

---

## 学習事項

1. **モックデータと実装の型整合性**: テストヘルパーのモックデータは、実装コードが期待する型と一致させる必要がある
2. **変更影響の波及**: 1つのファイル変更が、直接参照していない多数のテストに影響を与えることがある
3. **TDDの限界**: TDDで新規テストを書いても、既存テストへの影響は検出できない
4. **ワークフローの重要性**: 開発プロセスに「変更影響テスト」を組み込むことで、リグレッションを防止できる

---

## 次のステップ

1. [ ] 本修正をコミット
2. [ ] PRを作成してレビュー依頼
3. [ ] マージ後、他のIssue開発でPhase 2.9が正しく動作することを確認

---

_報告日: 2026-01-26_
_報告者: Claude Code (PM Auto-Dev)_
