# 環境変数設定 マイグレーションガイド

このガイドは、旧環境変数管理方式から新ポリシーへの移行手順を説明します。

**新ポリシー:**
- **ローカル開発**: 各プロジェクトディレクトリの `.env` を使用
- **Docker Compose**: プロジェクトルートの `.env.docker` を使用

## 📋 変更概要

### 旧方式

```
MySwiftAgent/
├── .env                    # 開発環境用（オプション）
├── .env.docker            # Docker Compose用（すべての設定が混在）
├── .env.local             # ローカル開発用（廃止）
└── scripts/
    ├── quick-start.sh     # 複雑なフォールバックロジック
    └── dev-start.sh       # 複雑なフォールバックロジック
```

**問題点:**
- 複数の環境変数ファイルが混在し管理が複雑
- フォールバックロジックのバグが多発
- API Keysが.envファイルに平文で保存
- サービス間URLを手動で設定する必要があった
- .env.dockerにすべての設定が詰め込まれていた

### 新方式（現行）

```
MySwiftAgent/
├── .env.docker            # Docker Compose用（統合設定）
├── jobqueue/.env          # ローカル開発用（JobQueue専用設定）
├── myscheduler/.env       # ローカル開発用（MyScheduler専用設定）
├── myVault/.env           # ローカル開発用（MyVault専用設定）
├── expertAgent/.env       # ローカル開発用（ExpertAgent専用設定）
├── graphAiServer/.env     # ローカル開発用（GraphAiServer専用設定）
├── commonUI/.env          # ローカル開発用（CommonUI専用設定）
├── docker-compose.yml     # .env.dockerを読み込み
└── scripts/
    ├── quick-start.sh     # 各プロジェクトの.envを読込
    └── dev-start.sh       # 各プロジェクトの.envを読込
```

**改善点:**
- ✅ **ローカル開発**: 各サービスが独自の.envを持ち、設定が明確
- ✅ **Docker Compose**: .env.dockerで統合管理（プロジェクトルート）
- ✅ サービス間URLは起動スクリプト/docker-composeが自動設定
- ✅ API KeysはMyVaultで暗号化管理（AES-256-GCM）
- ✅ .envファイルには最小限の設定のみ（PORT, LOG_LEVEL, MyVault接続情報）
- ✅ ローカル開発とDocker Composeで環境変数ファイルを分離

## 🔧 マイグレーション手順

### ステップ1: 旧ファイルのバックアップ

```bash
# プロジェクトルートで実行
cd /path/to/MySwiftAgent

# 旧ファイルをバックアップ（念のため保存）
mkdir -p backup/old-env-files
cp .env.docker backup/old-env-files/ 2>/dev/null || true
cp .env.local backup/old-env-files/ 2>/dev/null || true
cp .env backup/old-env-files/ 2>/dev/null || true

echo "✅ Backup completed"
```

### ステップ2: 各プロジェクトの.envファイル作成

各プロジェクトディレクトリに移動し、`.env.example`をコピーして`.env`を作成します。

#### 2.1 MyVault（最優先で設定）

```bash
cd myVault
cp .env.example .env
```

`.env`を開き、以下を設定:

```bash
# ===== マスター暗号化キーの生成 =====
# 以下のコマンドで生成したキーをコピー
python -c "import secrets, base64; print('base64:' + base64.b64encode(secrets.token_bytes(32)).decode())"

# .envに貼り付け
MSA_MASTER_KEY=base64:<生成されたキー>

# ===== サービス認証トークンの生成 =====
# 各サービス用に4つのトークンを生成
python -c "import secrets; print('expertagent:', secrets.token_urlsafe(32))"
python -c "import secrets; print('myscheduler:', secrets.token_urlsafe(32))"
python -c "import secrets; print('jobqueue:', secrets.token_urlsafe(32))"
python -c "import secrets; print('commonui:', secrets.token_urlsafe(32))"

# .envに貼り付け
TOKEN_expertagent=<生成されたトークン>
TOKEN_myscheduler=<生成されたトークン>
TOKEN_jobqueue=<生成されたトークン>
TOKEN_commonui=<生成されたトークン>
```

**重要**: これらのトークンは後で他のサービスの設定でも使用します。

#### 2.2 ExpertAgent

```bash
cd ../expertAgent
cp .env.example .env
```

`.env`を開き、MyVaultで生成したトークンを設定:

```bash
MYVAULT_ENABLED=true
MYVAULT_SERVICE_TOKEN=<MyVaultで生成したexpertagent用トークン>
```

**API Keysの移行:**
旧`.env.docker`に記載していたAPI Keysは、CommonUIのSecretsタブから登録します（ステップ4で実施）。

#### 2.3 CommonUI

```bash
cd ../commonUI
cp .env.example .env
```

`.env`を開き、MyVaultで生成したトークンを設定:

```bash
MYVAULT_ENABLED=true
MYVAULT_SERVICE_TOKEN=<MyVaultで生成したcommonui用トークン>
```

#### 2.4 その他のサービス

```bash
# JobQueue
cd ../jobqueue
cp .env.example .env
# デフォルト設定で問題なければ編集不要

# MyScheduler
cd ../myscheduler
cp .env.example .env
# デフォルト設定で問題なければ編集不要

# GraphAiServer
cd ../graphAiServer
cp .env.example .env
# デフォルト設定で問題なければ編集不要
```

### ステップ3: Docker Compose用.envファイルの作成

Docker Compose起動時に必要な環境変数を`.env.docker`に設定します。

```bash
cd /path/to/MySwiftAgent
```

`.env.docker`を作成（またはすでに存在する場合は編集）:

```bash
# ===== Docker Compose用環境変数 =====
# この.envファイルはMyVaultとExpertAgentの設定に必要

# MyVault設定（myVault/.envと同じ値を設定）
MSA_MASTER_KEY=base64:<myVault/.envと同じ値>
MYVAULT_TOKEN_EXPERTAGENT=<myVault/.envのTOKEN_expertagentと同じ値>
MYVAULT_TOKEN_MYSCHEDULER=<myVault/.envのTOKEN_myschedulerと同じ値>
MYVAULT_TOKEN_JOBQUEUE=<myVault/.envのTOKEN_jobqueueと同じ値>
MYVAULT_TOKEN_COMMONUI=<myVault/.envのTOKEN_commonuiと同じ値>

# ExpertAgent設定
EXPERTAGENT_ADMIN_TOKEN=<管理者用トークン（新規生成）>
MYVAULT_ENABLED=true
MYVAULT_DEFAULT_PROJECT=expertagent
GOOGLE_APIS_DEFAULT_PROJECT=default_project

# GraphAiServer設定
GRAPHAISERVER_ADMIN_TOKEN=<管理者用トークン（新規生成）>

# その他のサービス設定（必要に応じて）
LOG_LEVEL=INFO
MAIL_TO=your-email@example.com
SPREADSHEET_ID=your-spreadsheet-id
```

**トークン生成コマンド:**
```bash
python -c "import secrets; print('EXPERTAGENT_ADMIN_TOKEN:', secrets.token_urlsafe(32))"
python -c "import secrets; print('GRAPHAISERVER_ADMIN_TOKEN:', secrets.token_urlsafe(32))"
```

### ステップ4: API KeysをMyVaultに登録

旧`.env.docker`に記載していたAPI Keysを、CommonUIを通じてMyVaultに登録します。

```bash
# サービス起動
./scripts/quick-start.sh
```

ブラウザで `http://localhost:8601` を開き、以下の手順でAPI Keysを登録:

1. **Secretsタブ**を選択
2. **Project**: `expertagent`を選択（自動選択される）
3. **Add New Secret**をクリック
4. 以下のシークレットを順に登録:

| Secret Key | Value | Description |
|-----------|-------|-------------|
| `OPENAI_API_KEY` | `sk-...` | OpenAI API Key |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Anthropic API Key |
| `GOOGLE_API_KEY` | `AIza...` | Google API Key |
| `SERPER_API_KEY` | `...` | Serper API Key |

5. 各シークレット追加後、**Create Secret**をクリック

### ステップ5: Google APIs認証情報の設定（ExpertAgentのみ）

旧方式では`expertAgent/token/`配下に配置していた`credentials.json`と`token.json`は、引き続き同じ場所に配置します。

```bash
# ファイルが存在するか確認
ls -la expertAgent/token/

# Docker Compose用のマウントポイントも確認
ls -la docker-compose-data/expertagent/token/
```

**ローカル開発**: `expertAgent/token/`に配置
**Docker Compose**: `docker-compose-data/expertagent/token/`に配置

CommonUIの**Google Authタブ**からアップロードすることも可能です。

### ステップ6: 動作確認

#### ローカル開発モードの確認

```bash
# quick-start.shで起動
./scripts/quick-start.sh

# 各サービスのヘルスチェック
curl http://localhost:8101/health  # JobQueue
curl http://localhost:8102/health  # MyScheduler
curl http://localhost:8103/health  # MyVault
curl http://localhost:8104/health  # ExpertAgent
curl http://localhost:8105/health  # GraphAiServer
curl http://localhost:8601/_stcore/health  # CommonUI

# すべて {"status": "healthy"} または 200 OKが返ればOK

# 停止
./scripts/dev-start.sh stop
```

#### Docker Composeモードの確認

```bash
# Docker Composeで起動
docker-compose up -d

# 各サービスのヘルスチェック
curl http://localhost:8001/health  # JobQueue
curl http://localhost:8002/health  # MyScheduler
curl http://localhost:8003/health  # MyVault
curl http://localhost:8004/health  # ExpertAgent
curl http://localhost:8005/health  # GraphAiServer
curl http://localhost:8501/_stcore/health  # CommonUI

# ログ確認
docker-compose logs -f

# 停止
docker-compose down
```

### ステップ7: 旧ファイルの削除（任意）

動作確認が完了したら、旧ファイルを削除できます。

```bash
# 旧ファイルを削除（バックアップ済み）
rm -f .env.local
# .env.dockerは残す（Docker Composeで使用）

# .gitignoreの確認（以下がignore対象であることを確認）
cat .gitignore | grep -E "^\.env$|^.*\.env$"
```

## 🔍 トラブルシューティング

### エラー: "MyVault connection failed"

**原因**: MyVaultのサービストークンが正しく設定されていない

**対策**:
1. `myVault/.env`の`TOKEN_expertagent`を確認
2. `expertAgent/.env`の`MYVAULT_SERVICE_TOKEN`が一致しているか確認
3. MyVaultを再起動: `./scripts/dev-start.sh restart myvault`

### エラー: "Port already in use"

**原因**: 他のプロセスが同じポートを使用している

**対策**:
```bash
# 使用中のポートを確認
lsof -i :8101  # 例: JobQueueのポート

# プロセスを停止
kill <PID>

# または、dev-start.shで全サービス停止
./scripts/dev-start.sh stop
```

### エラー: "API Key not found in MyVault"

**原因**: API KeyがMyVaultに登録されていない

**対策**:
1. CommonUIのSecretsタブを開く
2. Project: `expertagent`を選択
3. 必要なAPI Keys（`OPENAI_API_KEY`等）を登録

### ローカル開発とDocker Composeでポートが重複する

**原因**: 両方のモードを同時に起動している

**対策**:
```bash
# どちらか一方のみを起動する

# ローカル開発モード
./scripts/quick-start.sh

# または Docker Composeモード（ローカル開発を停止してから）
./scripts/dev-start.sh stop
docker-compose up -d
```

## 📊 ポート番号一覧

| サービス | ローカル開発 | Docker Compose |
|---------|------------|---------------|
| JobQueue | 8101 | 8001 (host) → 8000 (container) |
| MyScheduler | 8102 | 8002 (host) → 8000 (container) |
| MyVault | 8103 | 8003 (host) → 8000 (container) |
| ExpertAgent | 8104 | 8004 (host) → 8000 (container) |
| GraphAiServer | 8105 | 8005 (host) → 8000 (container) |
| CommonUI | 8601 | 8501 (host) → 8501 (container) |

## 🔐 セキュリティベストプラクティス

### トークン管理

1. **生成**: `secrets.token_urlsafe(32)`で生成（最低32バイト）
2. **保存**: `.env`ファイルは`.gitignore`で除外されていることを確認
3. **共有**: トークンはSlack/メール等で直接共有せず、1Password等の秘密管理ツールを使用
4. **ローテーション**: 定期的（3ヶ月ごと）にトークンをローテーション

### API Keys

1. **MyVault管理**: すべてのAPI KeysはMyVaultで暗号化保存
2. **プロジェクト分離**: 各サービスは独自のProjectでAPI Keysを管理
3. **最小権限**: API Keysには必要最小限の権限のみ付与
4. **監査ログ**: MyVaultのログで定期的にアクセス履歴を確認

## 📚 関連ドキュメント

- **新ポリシー詳細**: [docs/design/environment-variables.md](../design/environment-variables.md)
- **MyVault統合**: [docs/design/myvault-integration.md](../design/myvault-integration.md)
- **アーキテクチャ**: [docs/design/architecture-overview.md](../design/architecture-overview.md)

## ❓ FAQ

### Q1: 旧`.env.docker`は削除していいですか？

A: いいえ、Docker Composeモードでは`.env.docker`が必要です。ただし、内容は大幅に簡略化されています（主にMyVault関連のトークンのみ）。

### Q2: ローカル開発とDocker Composeで異なる.envファイルが必要ですか？

A: はい、新ポリシーでは異なるファイルを使用します：
- **ローカル開発**: 各プロジェクトの`.env`（例: `expertAgent/.env`）
- **Docker Compose**: プロジェクトルートの`.env.docker`

これにより、各環境で適切な設定を独立して管理できます。ローカル開発のポート番号（8101-8105）とDocker Composeのポート番号（8001-8005）は自動的に切り替わります。

### Q3: API KeysをMyVaultではなく.envで管理したい場合は？

A: `expertAgent/.env`で`MYVAULT_ENABLED=false`に設定し、`.env`に直接API Keysを記載することも可能です。ただし、セキュリティ上MyVaultの使用を強く推奨します。

### Q4: 新しいサービスを追加する場合は？

A: 以下の手順で追加してください:
1. `{service}/.env.example`を作成（ローカル開発用）
2. `docker-compose.yml`に`env_file: - .env.docker`を指定（すべてのサービスで共通）
3. `.env.docker`に新しいサービス用の環境変数を追加
4. `scripts/quick-start.sh`と`scripts/dev-start.sh`の`for project in ...`ループに追加
5. MyVaultで新しいサービス用トークンを生成・登録

### Q5: マイグレーション中にエラーが出た場合は？

A: 以下の手順でロールバックできます:
```bash
# バックアップから復元
cp backup/old-env-files/.env.docker .
cp backup/old-env-files/.env.local .

# 旧起動スクリプトに戻す（git stashまたはcheckout）
git stash
# または
git checkout HEAD -- scripts/quick-start.sh scripts/dev-start.sh

# サービス再起動
./scripts/quick-start.sh
```

## 🎉 マイグレーション完了チェックリスト

- [ ] 旧`.env.docker`と`.env.local`をバックアップした
- [ ] MyVaultのマスター暗号化キーを生成・設定した
- [ ] 各サービスの認証トークンを生成・設定した
- [ ] 各プロジェクトに`.env`ファイルを作成した
- [ ] API KeysをCommonUIからMyVaultに登録した
- [ ] Google APIs認証情報を配置した（ExpertAgentのみ）
- [ ] ローカル開発モードで全サービスが起動できることを確認した
- [ ] Docker Composeモードで全サービスが起動できることを確認した
- [ ] 各サービスのヘルスチェックが成功することを確認した
- [ ] CommonUIから各サービスにアクセスできることを確認した

すべてにチェックが付いたら、マイグレーション完了です！🎊
