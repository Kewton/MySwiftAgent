# Issue #143 動作確認ガイド

このドキュメントは、Issue #143で実装したエラーハンドリングとロールバック機能の動作確認方法を説明します。

## 🎯 確認する機能

1. エラートラップとロールバック機構
2. ポート競合検出と解決提案
3. `--force`オプション
4. クリーンアップ処理
5. エラーメッセージとカタログ

---

## ✅ 事前準備

### 1. すべてのサービスを停止

```bash
./scripts/unified-start.sh stop
```

### 2. PIDファイルのクリーンアップ

```bash
rm -f /tmp/myswiftagent/*.pid
```

---

## 📋 テストケース

### テスト1: 基本機能テスト

**目的**: 実装したすべての基本機能が正しく動作することを確認

```bash
# テストスクリプトを実行
./tests/manual-test.sh 2>&1 | grep -E "(PASS|FAIL)" | head -20
```

**期待される結果**:
```
✓ PASS: unified-start.sh exists
✓ PASS: common.sh exists
✓ PASS: process-manager.sh exists
✓ PASS: error-catalog.sh exists (NEW)
✓ PASS: unified-start.sh is executable
✓ PASS: common.sh sources without errors
✓ PASS: process-manager.sh sources without errors
✓ PASS: error-catalog.sh sources without errors (NEW)
✓ PASS: EXIT_SUCCESS is defined
✓ PASS: EXIT_DEPENDENCY_ERROR is defined (NEW)
✓ PASS: EXIT_PORT_CONFLICT is defined (NEW)
✓ PASS: EXIT_SERVICE_START_FAILED is defined (NEW)
✓ PASS: EXIT_PARTIAL_STARTUP_FAILED is defined (NEW)
✓ PASS: get_error_message function works (NEW)
✓ PASS: get_error_resolution function works (NEW)
✓ PASS: --force option is documented in help (NEW)
✓ PASS: Script accepts --force option (NEW)
```

---

### テスト2: ポート競合検出

**目的**: ポート競合が正しく検出され、適切なエラーメッセージが表示されることを確認

**手順**:

```bash
# 1. ポート8003を占有（myVaultのポート）
nc -l 8003 &
NC_PID=$!
echo "ncプロセス起動 (PID: $NC_PID)"

# 2. unified-start.shを実行
./scripts/unified-start.sh start 2>&1 | head -50

# 3. クリーンアップ
kill $NC_PID
```

**期待される結果**:
```
WARNING: myvault: Port 8003 is in use
Conflicting process:
  PID:     [数値]
  Command: nc
  User:    [ユーザー名]
ERROR: myvault: Port 8003 is in use. Use --force to kill conflicting processes

═══════════════════════════════════════════════════════════
How to resolve:
Resolve port conflicts:
  1. Stop the conflicting process manually
  2. Use './scripts/unified-start.sh start --force' to kill conflicting processes
  3. Check if another instance of services is running
═══════════════════════════════════════════════════════════
```

**確認ポイント**:
- ✅ ポート競合が検出される
- ✅ 競合プロセスの詳細情報（PID、コマンド、ユーザー）が表示される
- ✅ エラーコード2（PORT_CONFLICT）が使用される
- ✅ 解決方法が提示される（`--force`オプション）

---

### テスト3: --forceオプション

**目的**: `--force`オプションで競合プロセスが自動的に終了され、起動が成功することを確認

**手順**:

```bash
# 1. ポートを占有
nc -l 8003 &
NC_PID=$!
echo "ncプロセス起動 (PID: $NC_PID)"
sleep 1

# 2. ポートが占有されていることを確認
lsof -i:8003 | grep LISTEN

# 3. --forceオプション付きで起動
./scripts/unified-start.sh start --force 2>&1 | head -60

# 4. ncプロセスが終了したことを確認
ps -p $NC_PID || echo "ncプロセスは終了しました"

# 5. クリーンアップ
./scripts/unified-start.sh stop
```

**期待される結果**:
```
INFO: myvault: Force mode enabled - killing process(es) on port 8003...
SUCCESS: myvault: Port 8003 freed
[myvault] Started successfully (PID: [数値], Port: 8003)
```

**確認ポイント**:
- ✅ `--force`オプションが認識される
- ✅ 競合プロセスが自動的に終了される
- ✅ サービスが正常に起動する

---

### テスト4: ロールバック機構（手動割り込み）

**目的**: Ctrl+C で割り込んだ時に、起動済みサービスが正しくロールバックされることを確認

**手順**:

```bash
# 1. サービスを起動開始
./scripts/unified-start.sh start

# 2. 数秒後にCtrl+Cで割り込む（Layer 1の起動中に実行）
#    ※ ターミナルで手動でCtrl+Cを押してください

# 3. ロールバックメッセージを確認
# 4. サービスが停止していることを確認
./scripts/unified-start.sh status
```

**期待される結果**:
```
═══════════════════════════════════════════════════════════
  INTERRUPTED - Cleaning up started services
═══════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════
  ROLLBACK: Stopping [N] started service(s)
═══════════════════════════════════════════════════════════

[service-name] Rolling back...
[service-name]: Stopped

Rollback completed - all started services stopped

═══════════════════════════════════════════════════════════
           ERROR REPORT
═══════════════════════════════════════════════════════════
Error Code: 130
Message: Operation interrupted by user
```

**確認ポイント**:
- ✅ 割り込みが検出される
- ✅ ロールバック処理が実行される
- ✅ 起動済みサービスがすべて停止される
- ✅ エラーコード130（USER_INTERRUPTED）が使用される
- ✅ システムがクリーンな状態になる

---

### テスト5: サービス起動失敗時のロールバック

**目的**: サービスディレクトリが存在しない場合、ロールバックが実行されることを確認

**準備**: テスト用の一時的な設定変更

```bash
# unified-start.shを一時的にバックアップして編集
cp scripts/unified-start.sh scripts/unified-start.sh.bak

# 存在しないディレクトリを指定（テスト用）
# LAYER2_SERVICES の graphaiserver のパスを一時的に変更
sed -i.test 's|graphAiServer|graphAiServer_NOTEXIST|' scripts/unified-start.sh

# テスト実行
./scripts/unified-start.sh start 2>&1 | grep -A 20 "ROLLBACK"

# 元に戻す
mv scripts/unified-start.sh.bak scripts/unified-start.sh
```

**期待される結果**:
```
ERROR: graphaiserver: Directory not found: [path]/graphAiServer_NOTEXIST

═══════════════════════════════════════════════════════════
  ROLLBACK: Stopping [N] started service(s)
═══════════════════════════════════════════════════════════

[Previously started services are stopped in reverse order]

Error Code: 3
Message: Service failed to start
```

**確認ポイント**:
- ✅ ディレクトリ不在エラーが検出される
- ✅ ロールバックが自動実行される
- ✅ 先に起動したサービスが停止される
- ✅ エラーコード3（SERVICE_START_FAILED）またはエラーコード4（DIRECTORY_NOT_FOUND）が使用される

---

### テスト6: クリーンアップ処理

**目的**: 古いPIDファイルが自動的にクリーンアップされることを確認

**手順**:

```bash
# 1. テスト用のstale PIDファイルを作成
mkdir -p /tmp/myswiftagent
echo "999999" > /tmp/myswiftagent/test-service.pid

# 2. 起動時にクリーンアップされることを確認
./scripts/unified-start.sh start 2>&1 | grep -A 2 "Cleaning stale PID"

# 3. PIDファイルが削除されたことを確認
ls /tmp/myswiftagent/test-service.pid 2>/dev/null || echo "✓ stale PIDファイルは削除されました"

# 4. クリーンアップ
./scripts/unified-start.sh stop
```

**期待される結果**:
```
INFO: Cleaning stale PID file for: test-service
```

**確認ポイント**:
- ✅ 古いPIDファイルが検出される
- ✅ 自動的に削除される
- ✅ 起動処理が継続される

---

### テスト7: エラーメッセージとヘルプ

**目的**: エラーカタログとヘルプメッセージが正しく表示されることを確認

**手順**:

```bash
# 1. ヘルプメッセージを表示
./scripts/unified-start.sh --help

# 2. --forceオプションが記載されているか確認
./scripts/unified-start.sh --help | grep -A 2 "force"

# 3. エラーコードの確認
bash -c "source scripts/unified-lib/error-catalog.sh; echo 'EXIT_PORT_CONFLICT='$EXIT_PORT_CONFLICT; get_error_message $EXIT_PORT_CONFLICT"
```

**期待される結果**:
```
OPTIONS:
    --force    Force start by killing any processes on required ports

EXIT_PORT_CONFLICT=2
Port conflict detected
```

---

## 🔍 総合動作確認

すべてのテストを一度に確認するには、以下のスクリプトを実行します：

```bash
# 総合テストスクリプト（手動実行推奨）
cat > /tmp/comprehensive-test.sh << 'EOF'
#!/bin/bash

echo "=========================================="
echo "  Issue #143 総合動作確認"
echo "=========================================="
echo ""

# テスト1: 基本機能
echo "テスト1: 基本機能テスト"
./tests/manual-test.sh 2>&1 | grep -c "PASS" && echo "✓ 基本機能テスト完了"
echo ""

# テスト2: 構文チェック
echo "テスト2: 構文チェック"
bash -n scripts/unified-start.sh && echo "✓ unified-start.sh 構文OK"
bash -n scripts/unified-lib/error-catalog.sh && echo "✓ error-catalog.sh 構文OK"
bash -n scripts/unified-lib/process-manager.sh && echo "✓ process-manager.sh 構文OK"
bash -n scripts/unified-lib/common.sh && echo "✓ common.sh 構文OK"
echo ""

# テスト3: ヘルプメッセージ
echo "テスト3: ヘルプメッセージ"
./scripts/unified-start.sh --help | grep -q "force" && echo "✓ --forceオプションがヘルプに記載されている"
echo ""

# テスト4: エラーコード定義
echo "テスト4: エラーコード定義"
bash -c "source scripts/unified-lib/error-catalog.sh; \
  [ -n \"\$EXIT_PORT_CONFLICT\" ] && echo '✓ EXIT_PORT_CONFLICT定義済み'; \
  [ -n \"\$EXIT_SERVICE_START_FAILED\" ] && echo '✓ EXIT_SERVICE_START_FAILED定義済み'; \
  [ -n \"\$EXIT_PARTIAL_STARTUP_FAILED\" ] && echo '✓ EXIT_PARTIAL_STARTUP_FAILED定義済み'"
echo ""

echo "=========================================="
echo "  総合テスト完了"
echo "=========================================="
EOF

chmod +x /tmp/comprehensive-test.sh
/tmp/comprehensive-test.sh
```

---

## 📊 受入条件チェックリスト

実際の動作確認後、以下のチェックリストを使用して受入条件を確認してください：

- [ ] **起動失敗時に起動済みサービスが自動停止される**
  - テスト2、4、5で確認

- [ ] **エラーの原因が明確に表示される**
  - テスト2、4、7で確認

- [ ] **ポート競合が検出され、解決方法が提示される**
  - テスト2、3で確認

- [ ] **異常終了後もシステムがクリーンな状態になる**
  - テスト4、6で確認

---

## 🐛 トラブルシューティング

テスト中に問題が発生した場合：

1. **すべてのサービスを停止**
   ```bash
   ./scripts/unified-start.sh stop
   ```

2. **PIDファイルを手動削除**
   ```bash
   rm -f /tmp/myswiftagent/*.pid
   ```

3. **ポートをクリーンアップ**
   ```bash
   for port in 8001 8002 8003 8004 8005 5173 8501; do
       lsof -ti:$port && kill -9 $(lsof -ti:$port) || true
   done
   ```

4. **ログを確認**
   ```bash
   tail -50 logs/[service-name].log
   ```

---

## 📝 まとめ

すべてのテストが成功すれば、Issue #143の実装は正常に動作していることが確認できます。

詳細なトラブルシューティング情報は [unified-start-troubleshooting.md](./unified-start-troubleshooting.md) を参照してください。
