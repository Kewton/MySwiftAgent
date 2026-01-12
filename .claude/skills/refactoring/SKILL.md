---
name: refactoring
description: |
  コード品質改善、設計パターン適用、技術的負債解消を行うスキル。
  以下のような依頼で自動的に適用されます：
  - 「このコードをリファクタリングして」
  - 「コード品質を改善して」
  - 「重複コードを削除して」
  - 「Repository Patternを適用して」
  - 「複雑度を下げて」
  - 「技術的負債を解消して」
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
model: claude-opus-4-20250514
---

# リファクタリングスキル

コード品質を改善し、SOLID原則に基づく設計パターンを適用して、技術的負債を解消します。

## 適用条件

以下のキーワード・文脈で自動的に適用：
- リファクタリング、コード改善
- 設計パターンの適用（Repository, Factory, Strategy等）
- 重複コードの削除、DRY原則
- 複雑度の削減、SOLID原則
- 技術的負債の解消
- メソッド抽出、クラス分割

## リファクタリング原則

- **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **KISS**: Keep It Simple, Stupid
- **DRY**: Don't Repeat Yourself
- **YAGNI**: You Aren't Gonna Need It

## 実行フロー

### Phase 1: コード品質分析

```bash
# カバレッジ測定
uv run pytest --cov=app --cov-report=term-missing

# 複雑度分析
uv run radon cc app/ -s -a

# 静的解析
uv run ruff check app/
uv run mypy app/
```

### Phase 2: リファクタリング計画

コードスメルの特定：
- 長いメソッド（20行以上）
- 大きなクラス（300行以上）
- 重複コード
- マジックナンバー
- 不適切な命名

### Phase 3: リファクタリング実行

**重要**: 小さなステップで行い、各ステップごとにテストを実行

1. メソッド抽出
2. クラス抽出
3. 重複コード削除
4. 命名改善
5. 設計パターン適用

### Phase 4: テスト追加

目標カバレッジ（90%）達成までテストを追加

### Phase 5: 品質メトリクス再測定

改善前後のメトリクスを比較

## 設計パターン

適用可能なパターン：
- **Repository Pattern**: データアクセス層の抽象化
- **Factory Pattern**: オブジェクト生成の集約
- **Strategy Pattern**: アルゴリズムの切り替え
- **Dependency Injection**: 依存関係の注入

## 完了条件

- すべてのテストが成功
- 品質メトリクスが改善（カバレッジ、複雑度）
- 静的解析エラーがゼロ
- コミットが完了

## 詳細手順

詳細なリファクタリング手順は以下を参照：
`.claude/prompts/refactoring-core.md`
