# 恒久的な修正の推奨事項

**日時**: 2025-11-17 00:45
**バグID**: 20251117_000953

---

## 🎯 現状

### 修正内容
- `myVault/app/api/secrets.py`の`get_secret`関数に型チェックを実装
- SQLiteのLargeBinary型がhex文字列として保存される仕様に対応
- bytesとstringの両方を処理できるよう実装

### 現在の問題点
`docker cp`によるファイルコピーは一時的な対処療法であり、以下の問題があります：
- コンテナ再起動時に修正が失われる可能性
- Dockerイメージは元のコードを含んでいる
- 本番環境へのデプロイ時に修正が反映されない

---

## ✅ 推奨する恒久的な解決策

### 方法1: Dockerイメージの再ビルド（推奨）

#### 手順
```bash
# myVaultサービスのイメージを再ビルド
docker-compose build myvault

# サービスを再起動
docker-compose up -d myvault
```

#### メリット
- 修正がイメージに永続化される
- 本番環境へのデプロイが可能
- コンテナ再起動時も修正が維持される

#### 実施タイミング
- **優先度**: 高
- **推奨実施時期**: 次回デプロイ前

---

### 方法2: Volume Mount（開発環境のみ）

#### 設定方法
`docker-compose.yml`に以下を追加：

```yaml
services:
  myvault:
    volumes:
      - ./myVault/app:/app/app  # 開発時のみ
```

#### メリット
- コード変更が即座に反映される
- 開発サイクルが高速化

#### デメリット
- **本番環境では使用不可**
- パフォーマンスが若干低下する可能性

#### 実施タイミング
- **優先度**: 中
- **推奨実施時期**: ローカル開発環境の改善時

---

## 📋 実施チェックリスト

### 即座に実施すべき事項
- [ ] Dockerイメージの再ビルド
- [ ] 再ビルド後の動作確認
- [ ] コンテナ再起動テスト

### 将来的に検討すべき事項
- [ ] CI/CDパイプラインでの自動ビルド
- [ ] 開発環境用docker-compose.dev.yml の作成
- [ ] Volume mountによる開発環境の改善

---

## 🔍 検証方法

### イメージ再ビルド後の確認
```bash
# 1. コンテナ内のコードを確認
docker exec myswiftagent-myvault cat /app/app/api/secrets.py | grep -A 10 "isinstance(db_secret.encrypted_value, bytes)"

# 2. APIテスト
curl -s "http://localhost:8003/api/secrets/default_test/GOOGLE_API_KEY" \
  -H "X-Service: commonui" \
  -H "X-Token: L8Z7mbEqJLHITqXn6SnOBOYZnmnfnSpC8Lebetpvmu8"

# 3. コンテナ再起動テスト
docker restart myswiftagent-myvault
sleep 5
# 再度APIテスト実行
```

### 期待される結果
- ✅ `isinstance`による型チェックコードが存在する
- ✅ APIが正常にレスポンスを返す
- ✅ 再起動後もAPIが正常に動作する

---

## 📊 影響範囲

### 変更対象
- `myVault/app/api/secrets.py` のみ

### 影響を受けるサービス
- myVault API
- commonUI（Edit Secret機能）
- expertAgent（シークレット取得機能）
- graphAiServer（シークレット取得機能）

### リスク評価
- **リスクレベル**: 低
- **理由**: 既に修正は実装済みで、動作確認も完了している

---

**以上**
