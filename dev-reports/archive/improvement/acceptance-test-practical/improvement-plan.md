# 受入テスト実践化 改善計画

## 概要

`/pm-auto-dev` で実行される受入テストが静的解析にとどまり実践的でない問題を解決するため、開発規約関連ドキュメントとプロンプトをブラッシュアップする。

## 背景・問題

### 現状の問題

`/pm-auto-dev` Phase 3「受入テスト」が以下の問題を抱えている：

1. **コードレビュー形式のテスト**: 「Line XXにYYYが存在する」という確認のみ
2. **静的解析への過度な依存**: Ruff/MyPy パス = 受入テスト完了と誤解
3. **E2Eテスト未実行**: 「テストファイルが存在する」ことの確認で完了
4. **サービス起動なしで完了**: 実際の動作確認が行われない

### 定量分析（43件のacceptance-result.json分析）

| カテゴリ | 件数 | 割合 |
|---------|------|------|
| 完全に静的解析のみ | 約25件 | 58% |
| 静的解析 + 単体テスト結果引用 | 約12件 | 28% |
| 実際のAPI/サービス動作確認あり | 約6件 | 14% |

---

## 改善方針

### 核心：GitHub Actions実行可否による分類

| レベル | 実行環境 | 内容 | 担当Phase |
|--------|----------|------|-----------|
| L1 単体テスト | CI (GitHub Actions) | モック使用、外部依存なし | Phase 2 (TDD) |
| L2 結合テスト | CI (GitHub Actions) | Docker Compose、テスト用サービス | Phase 2 (TDD) |
| **L3 開発者受入テスト** | **ローカル (APIキー必要)** | **実サービス起動、外部API連携** | **Phase 3 (受入テスト)【必須】** |
| L4 PO受入テスト | 手動 | UX/UI検証 | ユーザー確認 |

### 重要決定事項

- **L3（ローカル受入テスト）は原則必須**
- スキップ可能な条件：`docs-only`, `internal`, `test-only`, `ci-only` ラベル付与時のみ

---

## 改善対象ファイル

### 優先度：高

| ファイル | 改善内容 |
|---------|---------|
| `.claude/prompts/acceptance-test-core.md` | L2/L3の明確な分離、L3テスト例の追加、サービス起動必須化 |
| `.claude/commands/pm-auto-dev.md` | Phase 3の役割をL3必須として明確化 |

### 優先度：中

| ファイル | 改善内容 |
|---------|---------|
| `docs/claude/08-issue-split.md` | 受入基準の2層構造を「CI vs ローカル」に統一 |
| `.claude/agents/acceptance-test-agent.md` | L3テストの具体的手順追加 |

---

## 具体的な改善内容

### 1. acceptance-test-core.md の改善

#### 追加するセクション

```markdown
## テストレベルの分類

### CI検証（GitHub Actions実行可能）- Phase 2で実施
- 単体テスト（モック使用）
- 結合テスト（テストDB使用）
- 静的解析（Ruff/MyPy）

### ローカル受入テスト（APIキー必要）- Phase 3で実施【必須】
- 実際のサービス起動
- 外部API連携確認
- E2Eシナリオ実行
```

#### 追加するL3テスト例

```python
# tests/acceptance/test_issue_{number}_acceptance.py
import pytest
import requests

@pytest.mark.acceptance
class TestIssueXXXAcceptance:
    """
    ローカル受入テスト（APIキー必要）

    前提条件:
    - サービスが起動していること (./scripts/dev-start.sh)
    - .env に必要なAPIキーが設定されていること
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = "http://localhost:8104"
        # ヘルスチェック
        response = requests.get(f"{self.base_url}/health")
        assert response.status_code == 200, "サービスが起動していません"

    def test_scenario_1_real_api_call(self):
        """シナリオ1: 実際のAPIエンドポイントで期待する応答が得られる"""
        response = requests.post(
            f"{self.base_url}/v1/endpoint",
            json={"param": "value"}
        )
        assert response.status_code == 200
        assert "expected_field" in response.json()

    def test_scenario_2_external_service_integration(self):
        """シナリオ2: 外部サービス連携が正常動作する"""
        # 実際のLLM API、Langfuse、Valkey等との連携確認
        pass
```

### 2. pm-auto-dev.md の改善

#### Phase 3 の説明を強化

```markdown
### Phase 3: 受入テスト【L3必須】

**重要**: このフェーズはローカル環境でのみ実行可能です。

#### 前提条件
- サービスが起動していること
- .env に必要なAPIキーが設定されていること
- 外部サービス（Langfuse, Valkey等）が利用可能であること

#### 実行内容
1. サービス起動確認（ヘルスチェック）
2. E2Eシナリオ実行（実際のAPI呼び出し）
3. 外部サービス連携確認
4. エビデンス収集（ログ、レスポンス）

#### スキップ条件
以下のラベルが付与されている場合のみスキップ可能：
- `docs-only`: ドキュメントのみの変更
- `internal`: 内部リファクタリング
- `test-only`: テストコードのみの変更
- `ci-only`: CI/CD設定のみの変更
```

### 3. 08-issue-split.md の改善

#### 受入基準の2層構造を修正

```markdown
## 受入基準の2層構造

### 🤖 CI検証基準（GitHub Actions）
Phase 2 (TDD) で自動検証される基準

#### 品質基準
- [ ] 単体テストカバレッジ 90%以上
- [ ] 結合テストカバレッジ 50%以上
- [ ] Ruff/MyPy エラーゼロ

#### 機能テスト（モック使用）
- [ ] API正常系テスト
- [ ] API異常系テスト
- [ ] バリデーションエラー確認

---

### 🔐 ローカル受入基準（APIキー必要）【原則必須】
Phase 3 (受入テスト) で検証される基準

#### 動作確認
- [ ] 実際のサービス起動で動作確認
- [ ] APIエンドポイントが期待する応答を返す
- [ ] ログが適切に出力される

#### 外部連携確認
- [ ] LLM API連携が正常動作（該当する場合）
- [ ] Langfuse連携が正常動作（該当する場合）
- [ ] Valkey連携が正常動作（該当する場合）

#### スキップ条件
以下のラベルが付与されている場合のみスキップ可能：
- `docs-only`, `internal`, `test-only`, `ci-only`
```

### 4. acceptance-test-agent.md の改善

#### L3テスト実行手順を追加

```markdown
## L3受入テスト実行手順

### Step 1: サービス起動
```bash
./scripts/dev-start.sh
# または
make dev-all
```

### Step 2: ヘルスチェック
```bash
curl -sf http://localhost:8104/health
curl -sf http://localhost:8103/health  # myVault
```

### Step 3: E2Eシナリオ実行
```bash
# 受入テスト実行
uv run pytest tests/acceptance/test_issue_{number}_acceptance.py -v

# または手動でAPIを叩く
curl -X POST http://localhost:8104/v1/endpoint \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

### Step 4: エビデンス収集
- APIレスポンスのスクリーンショット/ログ
- サービスログの確認
- 外部サービス連携の確認（Langfuseトレース等）
```

---

## 実装計画

### Phase 1: コアプロンプト改善
1. `.claude/prompts/acceptance-test-core.md` の改善
2. `.claude/commands/pm-auto-dev.md` の改善

### Phase 2: ドキュメント改善
3. `docs/claude/08-issue-split.md` の改善
4. `.claude/agents/acceptance-test-agent.md` の改善

### Phase 3: 検証
5. 改善後のプロンプトで `/pm-auto-dev` を実行し、L3テストが適切に実行されることを確認

---

## 成功基準

- [ ] `/pm-auto-dev` Phase 3 で実際のサービス起動確認が行われる
- [ ] acceptance-result.json に `practical_api_test` タイプのテストが含まれる
- [ ] ローカル受入テストがスキップされる場合、明確な理由（ラベル）が記録される

---

## 参考：良い受入テストの例（Issue #240）

```json
{
  "scenario_id": "AC-PRACTICAL-1",
  "scenario": "Practical API Test - 404 Error with Improved Message via Real HTTP Request",
  "type": "practical_api_test",
  "command": "curl -s http://localhost:8104/v1/marp-report/nonexistent-job-id-12345",
  "result": "passed",
  "evidence": "HTTP 404 returned with response: {\"detail\":\"Job not found or expired...\"}"
}
```

---

作成日: 2024-12-08
