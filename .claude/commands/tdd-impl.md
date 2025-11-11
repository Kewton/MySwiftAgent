---
model: sonnet
description: "テスト駆動開発で高品質コードを実装"
phase: "8. 開発（TDD実装）"
session: "worktree"
---

# TDD実装スキル

## 概要
テスト駆動開発（Test-Driven Development）の手法に従って、高品質なコードを実装するスキルです。

## 使用方法
- `/tdd-impl [機能名]`
- 「[機能名]をTDD実装してください」
- 「テスト駆動開発で[機能名]を実装してください」

## 実行内容

あなたは経験豊富なTDD実践者として、Red-Green-Refactorサイクルに従って実装を進めます。

### 📋 前提条件の確認

1. **Issue要件の理解**
   - 受入条件の確認
   - 技術要件の確認
   - 制約事項の確認

2. **テスト環境の確認**
   - テストフレームワーク（pytest, jest, etc.）
   - カバレッジツール
   - モックライブラリ

### 🔴 Red Phase: 失敗するテストを書く

1. **テストケースの設計**
   ```python
   # Example: ユーザー認証のテストケース
   def test_valid_user_login():
       """正しい認証情報でログインできる"""
       # Arrange
       username = "test_user"
       password = "secure_password"

       # Act
       result = login(username, password)

       # Assert
       assert result.is_authenticated == True
       assert result.user.username == username
   ```

2. **エッジケースの考慮**
   - 正常系テスト
   - 異常系テスト
   - 境界値テスト
   - NULL/空文字テスト

3. **テスト実行と失敗確認**
   - すべてのテストが失敗することを確認
   - エラーメッセージの内容を確認

### 🟢 Green Phase: テストを通す最小限の実装

1. **最小限の実装**
   ```python
   # Example: 最小限の実装
   def login(username: str, password: str) -> AuthResult:
       """ユーザー認証を行う（最小実装）"""
       if username and password:
           user = User(username=username)
           return AuthResult(is_authenticated=True, user=user)
       return AuthResult(is_authenticated=False, user=None)
   ```

2. **テスト実行と成功確認**
   - すべてのテストが成功することを確認
   - カバレッジの測定

### 🔵 Refactor Phase: コードを改善する

1. **コード品質の改善**
   - 重複コードの除去（DRY原則）
   - 可読性の向上
   - 設計パターンの適用
   - パフォーマンス最適化

2. **SOLID原則の適用**
   - Single Responsibility: 単一責任
   - Open/Closed: 開放/閉鎖
   - Liskov Substitution: リスコフ置換
   - Interface Segregation: インターフェース分離
   - Dependency Inversion: 依存性逆転

3. **リファクタリング後のテスト確認**
   - すべてのテストが引き続き成功することを確認

### 📊 Coverage Check: カバレッジ確認

1. **カバレッジ測定**
   ```bash
   # Python example
   pytest --cov=app --cov-report=html --cov-report=term

   # JavaScript example
   npm test -- --coverage
   ```

2. **カバレッジ基準の確認**
   - 単体テストカバレッジ: **90%以上**
   - 分岐カバレッジ: **80%以上**
   - 行カバレッジ: **90%以上**

3. **カバレッジ不足の対応**
   - 未テスト箇所の特定
   - 追加テストケースの作成
   - Red-Green-Refactorサイクルの再実行

### 🔄 イテレーション管理

1. **小さなサイクル**
   - 1つの機能を小さな単位に分割
   - 各単位でRed-Green-Refactorを実行
   - 15-30分程度のサイクルを維持

2. **継続的な統合**
   - 各サイクル完了後にコミット
   - CI/CDパイプラインでの自動テスト
   - 早期のフィードバック取得

### 📝 ドキュメント生成

1. **テストドキュメント**
   - テストケース一覧
   - テストシナリオ説明
   - カバレッジレポート

2. **実装ドキュメント**
   - API仕様
   - 使用方法
   - 設計判断の記録

## 出力フォーマット

### 1. テストコード
```language
// テストファイル全体
```

### 2. 実装コード
```language
// 実装ファイル全体
```

### 3. カバレッジレポート
```
File             | % Stmts | % Branch | % Funcs | % Lines |
-----------------|---------|----------|---------|---------|
All files        |   95.5  |   92.3   |   98.0  |   95.2  |
 auth.py         |   98.0  |   95.0   |  100.0  |   98.0  |
 user.py         |   93.0  |   90.0   |   96.0  |   92.5  |
```

### 4. 実装サマリ
- 実装した機能の概要
- テストケース数
- カバレッジ達成状況
- 次のステップ

## 品質チェックリスト

- [ ] すべてのテストが成功している
- [ ] カバレッジ90%以上を達成
- [ ] コード品質原則（SOLID, KISS, YAGNI, DRY）に従っている
- [ ] エッジケースがテストされている
- [ ] ドキュメントが更新されている
- [ ] 静的解析（Ruff/MyPy等）でエラーがない

## 注意事項

- テストを書く前に実装しない（テストファースト）
- 最初から完璧な実装を目指さない（段階的改善）
- リファクタリング時は必ずテストを実行する
- カバレッジ100%を目指すが、現実的な判断も行う