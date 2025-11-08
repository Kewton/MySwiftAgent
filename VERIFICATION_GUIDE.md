# Issue #142 ヘルスチェック機能 動作確認ガイド

## 📝 確認項目チェックリスト

### ✅ Phase 1: 単体テスト

```bash
# ヘルスチェックモジュールのテストを実行
./tests/scripts/test_health_check.sh
```

**期待結果:**
```
✅ All tests passed!
Total tests run:     12
Tests passed:        12
Tests failed:        0
Pass rate:           100%
```

---

### ✅ Phase 2: ヘルプメッセージの確認

```bash
./scripts/unified-start.sh --help
```

**確認ポイント:**
- [ ] `health` コマンドが COMMANDS セクションに表示される
- [ ] `--timeout N` オプションが OPTIONS セクションに表示される
- [ ] `--health-check-only` オプションが OPTIONS セクションに表示される
- [ ] `--skip-health-check` オプションが OPTIONS セクションに表示される
- [ ] 使用例に health コマンドの例が含まれている

---

### ✅ Phase 3: サービス起動とヘルスチェック

#### 3-1. 通常起動（自動ヘルスチェック付き）

```bash
./scripts/unified-start.sh start
```

**期待される動作:**

1. **サービスの起動**
   ```
   Layer 1 (Infrastructure) started
   Layer 2 (Middleware) started
   Layer 3 (Application) started
   All services started successfully
   ```

2. **自動ヘルスチェック実行**
   ```
   Running health checks (timeout: 30s)...

   Waiting for myvault to become healthy...
   ✅ myvault: Service is healthy (0.XXXs response time)

   Waiting for jobqueue to become healthy...
   ✅ jobqueue: Service is healthy (0.XXXs response time)

   ... (他のサービス)

   All services are healthy
   ```

3. **確認コマンド**
   ```bash
   # 全サービスが起動していることを確認
   ./scripts/unified-start.sh status
   ```

#### 3-2. ヘルスチェックのみ実行

```bash
# サービスが既に起動している状態で
./scripts/unified-start.sh health

# または
./scripts/unified-start.sh --health-check-only
```

**期待される出力:**
```
Checking myvault health...
  ✅ myvault: Process running (PID: XXXX)
  ✅ myvault: Port 8003 is listening
  ✅ myvault: Health endpoint responding (0.XXXs)
  ℹ️  myvault: Service status: healthy

Checking jobqueue health...
  ✅ jobqueue: Process running (PID: XXXX)
  ✅ jobqueue: Port 8001 is listening
  ✅ jobqueue: Health endpoint responding (0.XXXs)

... (他のサービス)

Health Check Summary:
  ✅ Passed: 5
```

#### 3-3. カスタムタイムアウトでの起動

```bash
# 60秒のタイムアウトで起動
./scripts/unified-start.sh start --timeout 60
```

**確認ポイント:**
- [ ] "timeout: 60s" と表示される
- [ ] 60秒まで待機する（タイムアウトまで到達しなければOK）

#### 3-4. ヘルスチェックをスキップして起動

```bash
# まず停止
./scripts/unified-start.sh stop

# ヘルスチェックなしで起動
./scripts/unified-start.sh start --skip-health-check
```

**期待される動作:**
- [ ] サービスは起動する
- [ ] "Running health checks..." のメッセージが表示されない
- [ ] すぐに完了する

---

### ✅ Phase 4: エラー時の動作確認

#### 4-1. サービス停止時のヘルスチェック

```bash
# サービスを停止
./scripts/unified-start.sh stop

# ヘルスチェックを実行
./scripts/unified-start.sh health
```

**期待される出力:**
```
Checking myvault health...
  ❌ myvault: Process not running

Checking jobqueue health...
  ❌ jobqueue: Process not running

... (全てのサービスでエラー)

Health Check Summary:
  ✅ Passed: 0
  ❌ Failed: 5

❌ Some services failed health checks
```

#### 4-2. タイムアウトの確認

```bash
# 非常に短いタイムアウトで起動（サービス停止状態で）
./scripts/unified-start.sh start --timeout 1
```

**期待される動作:**
- [ ] サービス起動は行われる
- [ ] ヘルスチェックで「Still waiting...」メッセージが表示される
- [ ] 約1秒後にタイムアウトする
- [ ] "Timeout waiting for service to become healthy" エラーが表示される

---

### ✅ Phase 5: 実際の使用シナリオ

#### シナリオ1: 開発環境でのクイックスタート

```bash
# 1. サービスを起動
./scripts/unified-start.sh start

# 2. すべて健全か確認
./scripts/unified-start.sh health

# 3. 作業終了後に停止
./scripts/unified-start.sh stop
```

#### シナリオ2: テスト前の健全性確認

```bash
# テスト実行前にヘルスチェック
if ./scripts/unified-start.sh --health-check-only; then
    echo "Services are healthy, running tests..."
    # テストを実行
else
    echo "Services are unhealthy, aborting tests"
    exit 1
fi
```

#### シナリオ3: CI/CDパイプラインでの使用

```bash
# サービス起動（長めのタイムアウト）
./scripts/unified-start.sh start --timeout 60

# ステータス確認
./scripts/unified-start.sh status

# ヘルスチェック
./scripts/unified-start.sh health

# テスト実行...

# クリーンアップ
./scripts/unified-start.sh stop
```

---

## 🔍 トラブルシューティング

### 問題1: ヘルスチェックが常に失敗する

**原因:**
- サービスに `/health` エンドポイントがない
- サービスの起動が遅い

**解決策:**
```bash
# タイムアウトを増やす
./scripts/unified-start.sh start --timeout 60

# または、個別にサービスを確認
./scripts/unified-start.sh status

# ログを確認
tail -f logs/myvault.log
```

### 問題2: "curl not available" 警告

**原因:**
- curl がインストールされていない

**解決策:**
```bash
# macOS
brew install curl

# Ubuntu/Debian
sudo apt-get install curl
```

### 問題3: 一部のサービスがスキップされる

**原因:**
- commonUI と myAgentDesk は `/health` エンドポイントがないため、HTTPヘルスチェックからは除外される
- これは正常な動作

**確認:**
```bash
# status コマンドではすべてのサービスが表示される
./scripts/unified-start.sh status
```

---

## 📊 動作確認完了チェックシート

全ての項目を確認したら ✅ を付けてください：

### 基本機能
- [ ] 単体テストが100%パスする
- [ ] ヘルプに新機能が記載されている
- [ ] `start` コマンドで自動ヘルスチェックが実行される
- [ ] `health` コマンドが動作する
- [ ] `--health-check-only` オプションが動作する

### オプション機能
- [ ] `--timeout` オプションでタイムアウトを変更できる
- [ ] `--skip-health-check` でヘルスチェックをスキップできる
- [ ] タイムアウト時に適切なエラーメッセージが表示される

### エラーハンドリング
- [ ] サービス停止時にエラーが表示される
- [ ] タイムアウト時に適切に処理される
- [ ] エラー時の終了コードが非ゼロになる

### 出力品質
- [ ] 色付きの出力が表示される (✅ ⚠️ ❌)
- [ ] 進捗状況が5秒ごとに表示される
- [ ] レスポンス時間が表示される
- [ ] サマリーが最後に表示される

---

## 🎯 最小限の動作確認（クイックチェック）

時間がない場合は、この3つだけでも確認してください：

```bash
# 1. テスト実行
./tests/scripts/test_health_check.sh

# 2. ヘルプ確認
./scripts/unified-start.sh --help | grep health

# 3. サービス起動とヘルスチェック
./scripts/unified-start.sh start
# → 自動的にヘルスチェックが実行され、結果が表示されることを確認
```

---

## 📞 サポート

問題が発生した場合：

1. **ログを確認**: `logs/*.log`
2. **ステータス確認**: `./scripts/unified-start.sh status`
3. **詳細ドキュメント**: `docs/scripts/health-check-spec.md`
4. **Issue報告**: GitHub Issues に報告

---

**確認完了日:** ___________
**確認者:** ___________
**結果:** ✅ 合格 / ❌ 不合格
