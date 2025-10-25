# 設計方針: TaskMaster 再利用ロジックの厳密化

**作成日**: 2025-10-24
**ブランチ**: feature/issue/111
**担当**: Claude Code
**Issue**: TaskMaster 再利用時のインターフェース不一致によるループ問題

---

## 📋 要求・要件

### ビジネス要求
- ジョブ生成ワークフローが interface_mismatch エラーでループし続ける問題を解決する
- Validation → interface_definition → master_creation の無限ループを防ぐ

### 機能要件
- TaskMaster 再利用時に interface_id も検証する
- interface_id が異なる場合は新規 TaskMaster を作成する
- 完全に同じ TaskMaster（name, URL, interface_id）の場合のみ再利用する

### 非機能要件
- パフォーマンス: 既存の検索速度を維持（10件以内のリストスキャン）
- セキュリティ: 既存のアクセス制御を維持
- 可用性: 既存のエラーハンドリングを維持

---

## 🏗️ アーキテクチャ設計

### 問題の根本原因

**現状のコード (schema_matcher.py:149-151)**:
```python
async def find_or_create_task_master(self, ...):
    existing = await self.find_task_master_by_name_and_url(name, url)  # ← name + URL のみで検索
    if existing:
        return existing  # ← 古い interface_id を持つ TaskMaster を返す
```

**問題点**:
1. name と URL が一致すれば、interface_id を無視して既存 TaskMaster を返す
2. interface_definition で新しいインターフェースを生成しても、master_creation で古い TaskMaster が再利用される
3. Validation で task_0 の output（古い）と task_1 の input（新しい）が不一致となる
4. interface_definition に戻って再生成 → ループ

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| 検索ロジック | name + URL + interface_id による完全一致 | 既存の検索メソッドを拡張、パフォーマンス影響なし |
| データベース | 変更なし（既存の jobqueue API を使用） | スキーマ変更不要、既存 API で実装可能 |
| エラーハンドリング | 既存のパターンを踏襲 | try-except で None を返す設計を維持 |

### 実装方針

**新規メソッド追加**:
```python
async def find_task_master_by_name_url_and_interfaces(
    self,
    name: str,
    url: str,
    input_interface_id: str,
    output_interface_id: str
) -> dict[str, Any] | None:
    """Find TaskMaster by exact name, URL, and interface IDs match."""
    try:
        result = await self.client.list_task_masters(name=name, page=1, size=10)
        masters = result.get("masters", [])

        for master in masters:
            if (master.get("name") == name
                and master.get("url") == url
                and master.get("input_interface_id") == input_interface_id
                and master.get("output_interface_id") == output_interface_id):
                return master

        return None
    except Exception:
        return None
```

**既存メソッド修正**:
```python
async def find_or_create_task_master(self, ...):
    # 厳密な検索（interface_id も含める）
    existing = await self.find_task_master_by_name_url_and_interfaces(
        name, url, input_interface_id, output_interface_id
    )
    if existing:
        logger.info(f"Reusing existing TaskMaster: {existing['id']}")
        return existing

    # 新規作成
    logger.info(f"Creating new TaskMaster for {name}")
    return await self.client.create_task_master(...)
```

### ディレクトリ構成

変更対象ファイル:
```
expertAgent/
├── aiagent/langgraph/jobTaskGeneratorAgents/utils/
│   └── schema_matcher.py  # 修正対象
└── tests/unit/
    └── test_schema_matcher_strict.py  # 新規追加
```

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: 遵守
  - Single Responsibility: SchemaMatcher はスキーマ検索のみ担当
  - Open-Closed: 新規メソッド追加で拡張、既存コード変更は最小限
  - Liskov Substitution: 既存の戻り値型を維持
  - Interface Segregation: 既存のインターフェースを維持
  - Dependency Inversion: JobqueueClient への依存を維持
- [x] **KISS原則**: 遵守 / シンプルな完全一致検索
- [x] **YAGNI原則**: 遵守 / バージョン管理は導入せず、必要最小限の修正
- [x] **DRY原則**: 遵守 / 検索ロジックを新規メソッドに抽出

### アーキテクチャガイドライン
- [x] architecture-overview.md: 準拠 / utils レイヤーの責務を維持
- [x] レイヤー分離: 維持 / JobqueueClient を経由したデータアクセス

### 設定管理ルール
- [x] 環境変数: 変更なし
- [x] myVault: 変更なし

### 品質担保方針
- [x] 単体テスト: 新規テストで 90%以上を維持予定
- [x] 結合テスト: 既存の E2E テストで検証予定
- [x] Ruff linting: エラーゼロ維持予定
- [x] MyPy type checking: エラーゼロ維持予定

### CI/CD準拠
- [x] PRラベル: `fix` ラベルを付与予定（patch bump）
- [x] コミットメッセージ: `fix(schema_matcher): add interface ID validation to prevent reuse loops`
- [x] pre-push-check-all.sh: 実行予定

### 参照ドキュメント遵守
- [x] CLAUDE.md: 開発ルールに準拠
- [x] DEVELOPMENT_GUIDE.md: 品質担保方針に準拠

### 違反・要検討項目
なし

---

## 📝 設計上の決定事項

### 1. **新規メソッド追加 vs 既存メソッド修正**
**決定**: 新規メソッド `find_task_master_by_name_url_and_interfaces` を追加
**理由**:
- 既存の `find_task_master_by_name_and_url` を使用している箇所があるかもしれない（後方互換性）
- 新規メソッドとして明示的に interface_id 検証を行うことで意図が明確
- テストが容易

### 2. **常に再生成 vs 厳密な再利用判定**
**決定**: 厳密な再利用判定（オプション A）を採用
**理由**:
- データベース肥大化を防ぐ（完全に同じ TaskMaster は再利用）
- パフォーマンスへの影響が最小限
- 将来的なバージョン管理への拡張が容易

### 3. **バージョン管理導入**
**決定**: 今回は導入しない
**理由**:
- YAGNI原則（現時点では不要）
- スキーマ変更のコストが高い
- 現状の問題は厳密化だけで解決可能

### 4. **ログ出力の追加**
**決定**: 再利用時と新規作成時にログを追加
**理由**:
- デバッグ時に挙動を追跡しやすい
- 将来的なパフォーマンス分析に役立つ

---

## 🎯 期待される効果

### 1. **ループ問題の解決**
- ✅ interface_mismatch エラーの永続化を防ぐ
- ✅ Validation → interface_definition の無限ループを防ぐ

### 2. **データ整合性の向上**
- ✅ TaskMaster の interface_id が常に最新状態を反映
- ✅ ワークフロー全体の interface 整合性を保証

### 3. **デバッグ性の向上**
- ✅ ログから再利用/新規作成の判断を追跡可能
- ✅ interface_id の変更履歴を確認可能

---

## 🚧 リスクと対策

| リスク | 影響度 | 対策 |
|-------|-------|------|
| 既存の `find_task_master_by_name_and_url` を使用している箇所がある | 中 | コードベース全体を Grep で検索して確認 |
| interface_id が頻繁に変わると TaskMaster が増加する | 低 | 現状では interface 生成ロジックが安定しているため影響は限定的 |
| 検索パフォーマンスの劣化 | 低 | 既存と同じ検索ロジック（size=10）を使用 |

---

## 📚 参考資料

- [expertAgent ログ分析結果](../../../logs/expertagent.log)
- [schema_matcher.py 現行コード](../../../aiagent/langgraph/jobTaskGeneratorAgents/utils/schema_matcher.py)
- [master_creation.py 現行コード](../../../aiagent/langgraph/jobTaskGeneratorAgents/nodes/master_creation.py)
