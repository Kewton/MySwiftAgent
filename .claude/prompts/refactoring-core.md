# リファクタリングコアプロンプト

このプロンプトは、スラッシュコマンドとサブエージェントの両方から実行されます。

---

## 入力情報の取得

### スラッシュコマンドモードの場合

ユーザーから対話的に以下の情報を取得してください：

```bash
# Issue情報を取得
gh issue view {issue_number} --json number,title,body
```

- Issue番号
- リファクタリング対象（ファイル、クラス、関数など）
- 現在の品質メトリクス（カバレッジ、複雑度など）
- 適用する設計パターン（あれば）

### サブエージェントモードの場合

コンテキストファイルから情報を取得してください：

```bash
# 最新のコンテキストファイルを探す
CONTEXT_FILE=$(find dev-reports/*/issue/*/pm-auto-dev/iteration-*/refactor-context.json 2>/dev/null | sort -V | tail -1)

if [ -z "$CONTEXT_FILE" ]; then
    echo "❌ Error: refactor-context.json not found"
    exit 1
fi

echo "📂 Context file: $CONTEXT_FILE"
cat "$CONTEXT_FILE"
```

コンテキストファイル構造:
```json
{
  "issue_number": 166,
  "refactor_targets": [
    "app/services/database.py",
    "app/models/job.py"
  ],
  "quality_metrics": {
    "before_coverage": 85.0,
    "complexity_score": 12
  },
  "design_patterns_to_apply": [
    "Repository Pattern",
    "Dependency Injection"
  ],
  "improvement_goals": [
    "カバレッジを90%以上に向上",
    "循環的複雑度を10以下に削減",
    "重複コードの削除"
  ]
}
```

---

## リファクタリング実行フロー

### Phase 1: コード品質分析

現在のコード品質を分析します。

#### カバレッジ測定
```bash
uv run pytest --cov=app --cov-report=json --cov-report=term-missing
```

#### 複雑度分析
```bash
# Radon（循環的複雑度）
uv run radon cc app/ -s -a

# Radon（保守性指数）
uv run radon mi app/ -s
```

#### コードスメル検出
```bash
# Ruff（Linter）
uv run ruff check app/

# MyPy（型チェック）
uv run mypy app/
```

分析結果を記録します。

---

### Phase 2: リファクタリング計画

改善すべき箇所を特定し、リファクタリング計画を立てます。

#### コードスメルの特定
- 長いメソッド（20行以上）
- 大きなクラス（300行以上）
- 重複コード
- マジックナンバー
- 不適切な命名

#### 設計パターンの適用検討
- Repository Pattern（データアクセス層の抽象化）
- Factory Pattern（オブジェクト生成の集約）
- Strategy Pattern（アルゴリズムの切り替え）
- Dependency Injection（依存関係の注入）

---

### Phase 3: リファクタリング実行

**重要**: リファクタリングは小さなステップで行い、**各ステップごとにテストを実行**してください。

#### ステップ1: メソッド抽出

長いメソッドを小さなメソッドに分割：

```python
# Before
def process_job(job_id: str) -> None:
    # 50行の長いメソッド
    ...

# After
def process_job(job_id: str) -> None:
    job = _fetch_job(job_id)
    _validate_job(job)
    _execute_job(job)
    _update_status(job)

def _fetch_job(job_id: str) -> Job:
    ...

def _validate_job(job: Job) -> None:
    ...
```

**テスト実行**:
```bash
uv run pytest tests/unit/test_job_processor.py -v
```

#### ステップ2: クラス抽出

大きなクラスを責任ごとに分割：

```python
# Before
class JobService:
    def fetch_job(self): ...
    def validate_job(self): ...
    def execute_job(self): ...
    def send_notification(self): ...  # 別の責任

# After
class JobService:
    def __init__(self, notifier: Notifier):
        self.notifier = notifier

    def fetch_job(self): ...
    def validate_job(self): ...
    def execute_job(self): ...

class Notifier:
    def send_notification(self): ...
```

**テスト実行**:
```bash
uv run pytest tests/unit/test_job_service.py -v
```

#### ステップ3: 重複コード削除

共通処理を関数/クラスに抽出：

```python
# Before
def process_job_a():
    # 共通処理
    ...

def process_job_b():
    # 共通処理（重複）
    ...

# After
def _common_processing():
    ...

def process_job_a():
    _common_processing()
    ...

def process_job_b():
    _common_processing()
    ...
```

**テスト実行**:
```bash
uv run pytest tests/unit/ -v
```

#### ステップ4: 命名改善

意図を明確に表す命名に変更：

```python
# Before
def proc(d):  # 不明瞭
    ...

# After
def process_job_data(job_data: Dict[str, Any]) -> None:  # 明確
    ...
```

#### ステップ5: 設計パターン適用

Repository Patternの例：

```python
# Before: 直接DBアクセス
class JobService:
    def get_job(self, job_id: str) -> Job:
        return db.query(Job).filter_by(id=job_id).first()

# After: Repository Pattern
class JobRepository:
    def find_by_id(self, job_id: str) -> Optional[Job]:
        return db.query(Job).filter_by(id=job_id).first()

class JobService:
    def __init__(self, repo: JobRepository):
        self.repo = repo

    def get_job(self, job_id: str) -> Job:
        return self.repo.find_by_id(job_id)
```

**テスト実行**:
```bash
uv run pytest tests/unit/test_job_service.py -v
uv run pytest tests/unit/test_job_repository.py -v
```

---

### Phase 4: テスト追加

リファクタリングでカバーされていないコードにテストを追加：

```bash
# カバレッジ確認
uv run pytest --cov=app --cov-report=term-missing

# 未カバー箇所にテストを追加
```

目標カバレッジ（90%）を達成するまでテストを追加してください。

---

### Phase 5: 品質メトリクス再測定

リファクタリング後の品質を測定します：

```bash
# カバレッジ
uv run pytest --cov=app --cov-report=json

# 複雑度
uv run radon cc app/ -s -a

# 静的解析
uv run ruff check app/
uv run mypy app/
```

改善前後のメトリクスを比較します。

---

### Phase 6: Commit

リファクタリングをコミットします：

```bash
git add .
git commit -m "$(cat <<'EOF'
refactor(app): apply Repository Pattern and improve code quality

Apply Repository Pattern to separate data access layer and improve
overall code maintainability.

Improvements:
- Extract JobRepository from JobService
- Split large methods into smaller, focused functions
- Remove code duplication in job processing logic
- Improve naming clarity (proc → process_job_data)

Quality Metrics:
- Coverage: 85% → 92%
- Cyclomatic Complexity: 12 → 8
- Ruff errors: 5 → 0
- MyPy errors: 2 → 0

Resolves #166

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 出力

### スラッシュコマンドモードの場合

ターミナルに結果を表示してください：

```
✅ リファクタリング完了

## リファクタリング内容
- Repository Patternの適用
- 長いメソッドの分割
- 重複コードの削除
- 命名の改善

## 品質メトリクス改善
| 指標 | Before | After | 改善 |
|------|--------|-------|------|
| Coverage | 85.0% | 92.0% | +7.0% ✅ |
| Complexity | 12 | 8 | -4 ✅ |
| Ruff errors | 5 | 0 | -5 ✅ |
| MyPy errors | 2 | 0 | -2 ✅ |

## ファイル変更
- app/services/database.py (リファクタリング)
- app/repositories/job_repository.py (新規)
- tests/unit/test_job_repository.py (新規)

## Commits
- abc1234: refactor(app): apply Repository Pattern and improve code quality
```

### サブエージェントモードの場合

結果ファイルをJSON形式で作成してください：

```bash
# 結果ファイルパスを決定
RESULT_FILE=$(dirname "$CONTEXT_FILE")/refactor-result.json
```

Writeツールで以下の内容を作成:

```json
{
  "status": "success",
  "quality_metrics": {
    "before_coverage": 85.0,
    "after_coverage": 92.0,
    "before_complexity": 12,
    "after_complexity": 8
  },
  "refactorings_applied": [
    "Repository Pattern適用",
    "長いメソッドの分割",
    "重複コードの削除",
    "命名の改善"
  ],
  "files_changed": [
    "app/services/database.py",
    "app/repositories/job_repository.py",
    "tests/unit/test_job_repository.py"
  ],
  "static_analysis": {
    "ruff_errors_before": 5,
    "ruff_errors_after": 0,
    "mypy_errors_before": 2,
    "mypy_errors_after": 0
  },
  "commits": [
    "abc1234: refactor(app): apply Repository Pattern and improve code quality"
  ],
  "message": "リファクタリング完了。品質メトリクス大幅改善。"
}
```

**重要**: 結果ファイルが作成されたことを報告してください。

---

## エラーハンドリング

### テストが失敗した場合

```json
{
  "status": "failed",
  "error": "リファクタリング後にテストが失敗しました",
  "failed_tests": [
    "test_job_service: AssertionError"
  ],
  "message": "リファクタリングを見直してください"
}
```

### 品質目標未達成の場合

```json
{
  "status": "partial_success",
  "quality_metrics": {
    "after_coverage": 88.0,
    "target_coverage": 90.0
  },
  "message": "カバレッジ目標90%に達していません（現在: 88.0%）"
}
```

---

## リファクタリング原則

1. **小さなステップで進める** - 各ステップでテストを実行
2. **テストを先に書く** - 新しいクラス/関数にはテストを追加
3. **SOLID原則を守る** - 単一責任、開放/閉鎖、リスコフ置換、インターフェース分離、依存性逆転
4. **KISS原則** - シンプルに保つ
5. **DRY原則** - 重複を避ける

---

## 完了条件

以下をすべて満たすこと：

- ✅ すべてのテストが成功
- ✅ 品質メトリクスが改善
- ✅ 目標カバレッジ達成
- ✅ 静的解析エラーがゼロ
- ✅ コミットが完了（スラッシュコマンドモード）
- ✅ 結果ファイルが作成済み（サブエージェントモード）
