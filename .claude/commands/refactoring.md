# リファクタリングスキル

## 概要
コード品質の改善、設計パターンの適用、技術的負債の解消を支援するスキルです。

## 使用方法
- `/refactoring [対象コード]`
- 「このコードをリファクタリングしてください」

## 実行内容

あなたは経験豊富なソフトウェアエンジニアです。以下の観点からリファクタリングを実施してください：

### 1. コード品質分析

#### Code Smells の検出
- [ ] **長いメソッド**: 20行を超えるメソッド
- [ ] **大きなクラス**: 責任が多すぎるクラス
- [ ] **重複コード**: DRY原則違反
- [ ] **長いパラメータリスト**: 3個を超える引数
- [ ] **データの群れ**: 一緒に使われるデータ
- [ ] **基本データ型への執着**: ドメインオブジェクトの不足
- [ ] **switch文**: ポリモーフィズムで置換可能
- [ ] **並行して変更されるクラス**: 結合度が高い
- [ ] **特性の横恋慕**: 他クラスのデータに依存
- [ ] **メッセージの連鎖**: デメテルの法則違反

#### 複雑度メトリクス
```
循環的複雑度: X
認知的複雑度: Y
ネストの深さ: 最大Z層
```

### 2. リファクタリング戦略

#### 適用するリファクタリング手法

**メソッドレベル**
- [ ] メソッドの抽出（Extract Method）
- [ ] メソッドのインライン化（Inline Method）
- [ ] 一時変数の削除（Replace Temp with Query）
- [ ] パラメータオブジェクトの導入（Introduce Parameter Object）

**クラスレベル**
- [ ] クラスの抽出（Extract Class）
- [ ] クラスのインライン化（Inline Class）
- [ ] 委譲の隠蔽（Hide Delegate）
- [ ] 仲介者の除去（Remove Middle Man）

**データレベル**
- [ ] フィールドのカプセル化（Encapsulate Field）
- [ ] データ値のオブジェクト化（Replace Data Value with Object）
- [ ] 配列のオブジェクト化（Replace Array with Object）

**条件式**
- [ ] 条件式の分解（Decompose Conditional）
- [ ] 条件式の統合（Consolidate Conditional Expression）
- [ ] ガード節による入れ子の除去（Replace Nested Conditional with Guard Clauses）

### 3. 設計パターンの適用

#### 推奨パターン
```python
# Before: 問題のあるコード
[元のコード]

# After: パターン適用後
[改善されたコード]
```

適用パターン:
- [ ] Factory Pattern
- [ ] Strategy Pattern
- [ ] Observer Pattern
- [ ] Decorator Pattern
- [ ] Repository Pattern

### 4. SOLID原則への準拠

#### 違反の修正
| 原則 | 違反内容 | 修正方法 | 優先度 |
|------|---------|---------|--------|
| SRP | [違反内容] | [修正方法] | High |
| OCP | [違反内容] | [修正方法] | Medium |
| LSP | [違反内容] | [修正方法] | Low |
| ISP | [違反内容] | [修正方法] | Medium |
| DIP | [違反内容] | [修正方法] | High |

### 5. パフォーマンス最適化

#### ボトルネック分析
- 時間計算量: O(n) → O(log n)
- 空間計算量: O(n) → O(1)
- データベースクエリ: N+1問題の解決

#### 最適化手法
- [ ] キャッシング導入
- [ ] 遅延評価（Lazy Evaluation）
- [ ] メモ化（Memoization）
- [ ] 並列処理

### 6. テスタビリティ向上

#### 依存性注入
```python
# Before: ハードコードされた依存
class Service:
    def __init__(self):
        self.repo = ConcreteRepository()

# After: 依存性注入
class Service:
    def __init__(self, repo: RepositoryInterface):
        self.repo = repo
```

#### モック可能な設計
- インターフェースの抽出
- 抽象クラスの導入
- ファクトリーパターンの使用

### 7. 実装手順

#### Step-by-Step リファクタリング
1. **準備**
   - [ ] 既存テストの確認
   - [ ] テストカバレッジ確認
   - [ ] ベースラインメトリクス記録

2. **実施**
   - [ ] 小さな変更を1つずつ実施
   - [ ] 各ステップでテスト実行
   - [ ] コミット（各ステップごと）

3. **検証**
   - [ ] 全テストパス確認
   - [ ] パフォーマンステスト
   - [ ] コードレビュー

### 8. 結果サマリー

#### Before/After 比較
| メトリクス | Before | After | 改善率 |
|-----------|--------|-------|--------|
| 行数 | XXX | YYY | -ZZ% |
| 循環的複雑度 | XX | YY | -ZZ% |
| テストカバレッジ | XX% | YY% | +ZZ% |
| 重複コード | XX% | YY% | -ZZ% |

#### 主な改善点
1. [改善点1の説明]
2. [改善点2の説明]
3. [改善点3の説明]

#### 技術的負債の削減
- 削減された負債: [内容]
- 残存する負債: [内容]
- 今後の改善提案: [内容]

## Codex CLI 連携（MCP経由）

大規模なリファクタリングの場合、Codex CLIを使用：

```bash
# MCP経由でCodex CLIを実行
codex refactor \
  --target "path/to/file" \
  --pattern "extract-method" \
  --safe-mode
```

## 出力フォーマット

PRの説明文として使用可能なMarkdown形式。Before/Afterのコード比較、改善内容の説明を含む。

## モデル設定
- model: sonnet（効率的な処理のため）
- temperature: 0.2（一貫性のあるリファクタリングのため）
- tools: Codex CLI（MCP経由で実コード変更）