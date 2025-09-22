# ブランチ保護設定

このドキュメントでは、MySwiftAgentプロジェクトで推奨されるGitHubブランチ保護設定について説明します。

## 🔒 推奨ブランチ保護設定

### main ブランチ

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Test Suite",
      "Security Scan",
      "Build Release Candidate",
      "QA Tests"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 2,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "require_last_push_approval": true
  },
  "restrictions": {
    "users": [],
    "teams": ["core-team"],
    "apps": ["github-actions"]
  },
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true
}
```

### staging ブランチ

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Test Suite",
      "Integration Tests",
      "Security Scan"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "restrictions": {
    "users": [],
    "teams": ["release-team"],
    "apps": ["github-actions"]
  },
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
```

### develop ブランチ

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Test Suite",
      "Security Scan",
      "Build Check"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
```

## 🛠️ 設定手順

### GitHub UI での設定

1. **リポジトリ設定へ移動**
   - Settings → Branches

2. **ブランチ保護ルール追加**
   - "Add rule" をクリック
   - ブランチ名パターンを入力（例: `main`）

3. **保護設定を有効化**
   - 上記の推奨設定に従って各オプションを設定

### GitHub CLI での設定

```bash
# main ブランチの保護設定
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Test Suite","Security Scan","Build Release Candidate","QA Tests"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":2,"dismiss_stale_reviews":true,"require_code_owner_reviews":true,"require_last_push_approval":true}' \
  --field restrictions='{"users":[],"teams":["core-team"],"apps":["github-actions"]}' \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_conversation_resolution=true

# staging ブランチの保護設定
gh api repos/:owner/:repo/branches/staging/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Test Suite","Integration Tests","Security Scan"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions='{"users":[],"teams":["release-team"],"apps":["github-actions"]}' \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_conversation_resolution=true

# develop ブランチの保護設定
gh api repos/:owner/:repo/branches/develop/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Test Suite","Security Scan","Build Check"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_conversation_resolution=true
```

## 👥 チーム・権限設定

### 推奨チーム構成

1. **core-team**
   - main ブランチへの直接アクセス権限
   - 緊急時の管理者権限オーバーライド可能

2. **release-team**
   - staging ブランチへのアクセス権限
   - リリース管理担当

3. **developers**
   - develop ブランチへのPR作成権限
   - feature ブランチでの開発作業

### CODEOWNERS ファイル

`.github/CODEOWNERS` ファイルを作成して、コードレビューの責任者を定義：

```
# Global owners
* @core-team

# CI/CD workflows
/.github/workflows/ @core-team @devops-team

# Application code
/myscheduler/ @core-team @backend-team

# Infrastructure
/docker/ @devops-team
/kubernetes/ @devops-team

# Documentation
/docs/ @core-team
*.md @core-team
```

## 🚨 緊急時の対応

### ホットフィックス用の一時的権限

緊急時（ホットフィックス）には、以下の手順で一時的に保護を緩和：

1. **緊急承認環境の設定**
   ```yaml
   emergency-approval:
     if: contains(github.ref, 'hotfix/')
     environment: emergency-approval
   ```

2. **管理者による一時的オーバーライド**
   - Settings → Branches → Edit rule
   - "Include administrators" を一時的に無効化
   - 作業完了後に再有効化

## 📋 チェックリスト

### 初期設定

- [ ] main ブランチ保護設定完了
- [ ] staging ブランチ保護設定完了
- [ ] develop ブランチ保護設定完了
- [ ] CODEOWNERS ファイル作成
- [ ] チーム作成・権限設定
- [ ] ステータスチェック設定

### 定期確認

- [ ] 保護設定の有効性確認（月次）
- [ ] チームメンバー権限確認（四半期）
- [ ] ステータスチェック項目見直し（リリース時）
- [ ] 緊急時手順の確認・テスト（年次）

## 🔍 トラブルシューティング

### よくある問題

1. **ステータスチェック失敗**
   ```bash
   # CI状態確認
   gh pr checks

   # 特定ワークフロー再実行
   gh workflow run ci-feature.yml
   ```

2. **レビュー承認不足**
   - 必要な承認者数の確認
   - CODEOWNERS 設定の確認

3. **管理者権限でのオーバーライド**
   ```bash
   # 緊急時の一時的設定変更
   gh api repos/:owner/:repo/branches/main/protection \
     --method PUT \
     --field enforce_admins=false
   ```

### 設定確認コマンド

```bash
# 現在の保護設定確認
gh api repos/:owner/:repo/branches/main/protection

# ブランチ一覧と保護状態
gh api repos/:owner/:repo/branches --jq '.[] | {name: .name, protected: .protected}'

# 最近のPR状態確認
gh pr list --state all --limit 10
```