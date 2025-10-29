# Phase 3 作業状況: ガードレール設定

**Phase名**: GitHub Branch Protection Rules設定
**作業日**: 2025-10-29
**所要時間**: 20分

---

## 📝 実装内容

### 目的
GitHub Branch Protection Rulesを設定し、CLAUDE.mdの標準マージフロー（L60-61, L89）を強制する。

### 設定内容

#### 1. mainブランチ保護設定（最も厳格）

**設定JSON**:
```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI - Main Branch Quality Check"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
```

**実行コマンド**:
```bash
gh api repos/Kewton/MySwiftAgent/branches/main/protection \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  --input /tmp/branch-protection-main.json
```

**結果**: ✅ 成功

**有効化された保護**:
- ✅ **PR必須**: 直pushが禁止される
- ✅ **レビュー1名必須**: PR承認が必要
- ✅ **CI/CD必須**: "CI - Main Branch Quality Check"ワークフロー成功が必須
- ✅ **最新状態必須**: ブランチをmainの最新状態に保つ必要あり
- ✅ **管理者も例外なし**: 管理者も保護ルールに従う
- ✅ **Force push禁止**: 履歴の書き換え禁止
- ✅ **ブランチ削除禁止**: 誤削除を防止

#### 2. stagingブランチ保護設定（中程度）

**設定JSON**:
```json
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
```

**実行コマンド**:
```bash
gh api repos/Kewton/MySwiftAgent/branches/staging/protection \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  --input /tmp/branch-protection-staging.json
```

**結果**: ✅ 成功

**有効化された保護**:
- ✅ **PR推奨**: required_approving_review_count=0により、レビューなしPR可能
- ✅ **管理者も例外なし**: 管理者も保護ルールに従う
- ✅ **Force push禁止**: 履歴の書き換え禁止
- ✅ **ブランチ削除禁止**: 誤削除を防止
- ❌ **CI/CD不要**: 迅速なUATサイクルを優先

#### 3. release/*ブランチ保護設定（保留）

**状況**: ⚠️ **未実装**

**理由**: GitHub REST APIでワイルドカードブランチ（`release/*`）の保護設定が困難

**代替案**:
1. **GitHub Web UIから手動設定**: Settings > Branches > Add branch protection rule > `release/*`
2. **個別ブランチ保護**: release/v1.0.0, release/v2.0.0等を個別に保護（非推奨）
3. **rulesets API使用**: GitHub Rulesets API（新機能）を使用（調査必要）

**Phase 4で対応**: 検証時にGitHub Web UIから手動設定を実施予定

---

## 🐛 発生した課題

### 課題1: gh apiコマンドの引数エラー

**エラー内容**:
```
accepts 1 arg(s), received 13
```

**原因**: gh apiコマンドに直接パラメータを渡す方法が誤っていた

**解決策**: JSONファイルを作成し、`--input`オプションで読み込む方法に変更

**結果**: ✅ 解決

---

### 課題2: release/*ワイルドカードブランチの保護

**課題内容**: GitHub REST APIでワイルドカードブランチの保護設定が不可能

**調査結果**:
- GitHub REST API (`/branches/{branch}/protection`) はワイルドカードをサポートしていない
- 個別ブランチ名（例: `release/v1.0.0`）のみ指定可能
- GitHub Rulesets API（Beta）がワイルドカードをサポート予定

**対応方針**:
- Phase 4で検証時に、GitHub Web UIから手動設定
- 将来的にRulesets APIへの移行を検討

**状態**: ⚠️ **Phase 4で対応予定**

---

## 💡 技術的決定事項

### 決定1: stagingブランチのレビュー要件を0に設定

**判断**: `required_approving_review_count: 0`

**理由**:
1. **迅速なUATサイクル**: stagingはUAT用のため、レビューなしで迅速にマージ可能
2. **PR経由は強制**: レビュー不要でもPR作成は必須（トレーサビリティ確保）
3. **mainで品質担保**: mainへのマージ時に厳密なレビュー・CI/CDチェックを実施

**リスク**: 低（UAT用途のため、品質リスクは限定的）

### 決定2: CI/CDステータスチェックをmainのみ必須

**判断**: stagingはCI/CDステータスチェックを不要とする

**理由**:
1. **開発速度優先**: stagingへの迅速なデプロイを優先
2. **mainで最終チェック**: 本番環境（main）へのマージ時に厳密にチェック
3. **既存ワークフロー維持**: staging pushトリガーは既にコメントアウト済み（deploy-staging.yml）

### 決定3: enforce_adminsを全ブランチで有効化

**判断**: main, stagingともに`enforce_admins: true`

**理由**:
- CLAUDE.md L92-94: 例外対応は「チーム責任者の承認と事前周知」が必要
- 管理者も保護ルールに従うことで、透明性とトレーサビリティを確保

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] SOLID原則: N/A（インフラ設定）
- [x] KISS原則: 遵守 / シンプルなBranch Protection設定
- [x] YAGNI原則: 遵守 / 必要最小限の保護（developは保護しない、stagingはCI/CD不要）
- [x] DRY原則: N/A

### アーキテクチャガイドライン
- [x] CLAUDE.md ブランチ戦略: 完全準拠
  - ✅ L60-61: PRを通じて行うことを厳守
  - ✅ L89: 直push禁止
  - ✅ L92-94: 管理者も例外なし（enforce_admins=true）

### 設定管理ルール
- [x] 環境変数: N/A
- [x] myVault: N/A

### 品質担保方針
- [x] 単体テスト: N/A（インフラ設定）
- [x] 結合テスト: N/A
- [x] Ruff linting: N/A
- [x] MyPy type checking: N/A

### CI/CD準拠
- [x] PRラベル: `ci` ラベル予定
- [x] コミットメッセージ: `ci: setup branch protection rules` を予定

### 違反・要検討項目
- ⚠️ **release/*ブランチ保護未実装**: Phase 4で手動設定予定

---

## 📊 進捗状況

### Phase 3 完了事項
- [x] mainブランチ保護設定（完全実装）
- [x] stagingブランチ保護設定（完全実装）
- [ ] release/*ブランチ保護設定（Phase 4で対応）

### 全体進捗
- **Phase 1**: ✅ 完了（staging同期確認）
- **Phase 2**: ✅ 完了（develop同期）
- **Phase 3**: ⚠️ **90%完了**（release/*未実装）
- **Phase 4**: ⏳ 次のステップ（検証・ドキュメント作成）

**進捗率**: 70% (2.9/4 Phases完了)

---

## 🎯 成功基準達成状況

| 成功基準 | 目標 | 実績 | 達成 |
|---------|------|------|------|
| main保護設定 | PR+Review+CI/CD必須 | 設定完了 | ✅ |
| staging保護設定 | PR推奨 | 設定完了 | ✅ |
| release/*保護設定 | PR必須 | 未実装 | ⚠️ Phase 4対応 |
| enforce_admins | 全ブランチ有効 | 設定完了 | ✅ |

**Phase 3: 90%成功** ⚠️

---

## 📚 参考資料

### GitHub公式ドキュメント
- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Managing a branch protection rule](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- [GitHub REST API - Branch Protection](https://docs.github.com/en/rest/branches/branch-protection)
- [GitHub Rulesets (Beta)](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)

### プロジェクト内部ドキュメント
- [work-plan.md](./work-plan.md#phase-3-ガードレール設定1時間)
- [design-policy.md](./design-policy.md#決定2-mainブランチのみレビュー必須)

---

## ➡️ 次のステップ

**Phase 4: 検証・ドキュメント作成**

次のPhaseでは、以下を実施します：

1. **mainへの直push拒否を検証**
2. **stagingへの直push拒否を検証**
3. **release/*ブランチ保護をGitHub Web UIから手動設定**
4. **final-report.md作成**

**所要時間**: 約30分
