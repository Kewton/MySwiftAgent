# Quick Fix Guide: dev-start.sh stop コマンド修正

**問題**: `./scripts/dev-start.sh stop` が PID ファイルを見つけられず、サービスを停止できない

**緊急回避策（今すぐ使える）**:

## 1. 手動でサービスを停止する

```bash
# MyVault を停止
lsof -ti:8003 | xargs kill -TERM

# CommonUI を停止
lsof -ti:8501 | xargs kill -TERM

# ExpertAgent を停止
lsof -ti:8004 | xargs kill -TERM

# GraphAiServer を停止
lsof -ti:8005 | xargs kill -TERM

# MyScheduler を停止
lsof -ti:8002 | xargs kill -TERM

# JobQueue を停止
lsof -ti:8001 | xargs kill -TERM

# MyAgentDesk を停止
lsof -ti:8000 | xargs kill -TERM
```

## 2. 一括停止スクリプト（コピペで使える）

```bash
#!/bin/bash
# 全サービスを停止するヘルパースクリプト

PORTS=(8000 8001 8002 8003 8004 8005 8501)
NAMES=("MyAgentDesk" "JobQueue" "MyScheduler" "MyVault" "ExpertAgent" "GraphAiServer" "CommonUI")

for i in "${!PORTS[@]}"; do
    PORT="${PORTS[$i]}"
    NAME="${NAMES[$i]}"

    PID=$(lsof -ti:$PORT 2>/dev/null)
    if [[ -n "$PID" ]]; then
        echo "🛑 Stopping $NAME (PID: $PID, Port: $PORT)..."
        kill -TERM $PID 2>/dev/null || true
        sleep 1

        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            echo "⚠️  Force killing $NAME..."
            kill -KILL $PID 2>/dev/null || true
        fi
        echo "✅ $NAME stopped"
    else
        echo "ℹ️  $NAME not running on port $PORT"
    fi
done

# Stop Valkey Docker container
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^myswiftagent-valkey$"; then
    echo "🛑 Stopping Valkey Docker container..."
    docker stop myswiftagent-valkey 2>/dev/null || true
    docker rm myswiftagent-valkey 2>/dev/null || true
    echo "✅ Valkey stopped"
fi

echo "🎉 All services stopped"
```

**使い方**:
```bash
# ファイルに保存
cat > /tmp/stop-all-services.sh << 'EOF'
[上記のスクリプトをコピー]
EOF

# 実行権限を付与
chmod +x /tmp/stop-all-services.sh

# 実行
/tmp/stop-all-services.sh
```

---

## 3. 現在の状態確認（ポートベース）

```bash
#!/bin/bash
# サービス状態確認スクリプト

PORTS=(8000 8001 8002 8003 8004 8005 8501 6379)
NAMES=("MyAgentDesk" "JobQueue" "MyScheduler" "MyVault" "ExpertAgent" "GraphAiServer" "CommonUI" "Valkey")

echo "Service Status Check:"
echo "===================="

for i in "${!PORTS[@]}"; do
    PORT="${PORTS[$i]}"
    NAME="${NAMES[$i]}"

    PID=$(lsof -ti:$PORT 2>/dev/null)
    if [[ -n "$PID" ]]; then
        CMD=$(ps -p $PID -o command= 2>/dev/null | head -c 60)
        echo "✅ $NAME: Running (PID: $PID, Port: $PORT)"
        echo "   └─ $CMD..."
    else
        echo "❌ $NAME: Not running (Port: $PORT)"
    fi
done
```

**使い方**:
```bash
# ファイルに保存
cat > /tmp/check-services.sh << 'EOF'
[上記のスクリプトをコピー]
EOF

# 実行権限を付与
chmod +x /tmp/check-services.sh

# 実行
/tmp/check-services.sh
```

---

## 4. dev-start.sh への即時パッチ（推奨）

### stop_service 関数を修正する

**ファイル**: `/Users/maenokota/share/work/github_kewton/MySwiftAgent/scripts/dev-start.sh`

**変更箇所**: 456-487行目の `stop_service` 関数

**修正内容**:

```bash
# Stop a service
stop_service() {
    local name=$1
    local pid_file=$2
    local port=$3  # 新規: ポート番号を追加

    local pid_to_stop=""

    # Try PID file first
    if [[ -f "$pid_file" ]]; then
        pid_to_stop=$(cat "$pid_file")
        if ! kill -0 $pid_to_stop 2>/dev/null; then
            print_warning "$name: PID file exists but process not running"
            rm -f "$pid_file"
            pid_to_stop=""
        fi
    fi

    # Fallback to port-based detection
    if [[ -z "$pid_to_stop" && -n "$port" ]]; then
        pid_to_stop=$(lsof -ti:$port 2>/dev/null)
        if [[ -n "$pid_to_stop" ]]; then
            print_warning "$name: PID file not found, detected via port $port (PID: $pid_to_stop)"
        fi
    fi

    if [[ -n "$pid_to_stop" ]]; then
        print_service "🛑" "$name" "Stopping service (PID: $pid_to_stop)..."
        kill -TERM $pid_to_stop 2>/dev/null || true

        # Wait for graceful shutdown
        local attempts=0
        while kill -0 $pid_to_stop 2>/dev/null && [[ $attempts -lt 10 ]]; do
            sleep 1
            ((attempts++))
        done

        # Force kill if still running
        if kill -0 $pid_to_stop 2>/dev/null; then
            print_warning "$name: Force stopping..."
            kill -KILL $pid_to_stop 2>/dev/null || true
        fi

        print_success "$name: Stopped"
    else
        print_info "$name: Not running"
    fi

    rm -f "$pid_file"
}
```

### stop コマンドの呼び出しを修正する

**変更箇所**: 997-1030行目の `stop` コマンド部分

**修正内容**: 各 `stop_service` 呼び出しにポート番号を追加

```bash
stop)
    print_step "Stopping all services..."
    if [[ -z "$service_filter" || "$service_filter" == "myagentdesk" ]]; then
        stop_service "MyAgentDesk" "$MYAGENTDESK_PID" $MYAGENTDESK_PORT  # ← ポート追加
    fi
    if [[ -z "$service_filter" || "$service_filter" == "commonui" ]]; then
        stop_service "CommonUI" "$COMMONUI_PID" $COMMONUI_PORT  # ← ポート追加
    fi
    if [[ -z "$service_filter" || "$service_filter" == "graphaiserver" ]]; then
        stop_service "GraphAiServer" "$GRAPHAISERVER_PID" $GRAPHAISERVER_PORT  # ← ポート追加
    fi
    if [[ -z "$service_filter" || "$service_filter" == "expertagent" ]]; then
        stop_service "ExpertAgent" "$EXPERTAGENT_PID" $EXPERTAGENT_PORT  # ← ポート追加
    fi
    if [[ -z "$service_filter" || "$service_filter" == "myvault" ]]; then
        stop_service "MyVault" "$MYVAULT_PID" $MYVAULT_PORT  # ← ポート追加
    fi
    if [[ -z "$service_filter" || "$service_filter" == "myscheduler" ]]; then
        stop_service "MyScheduler" "$MYSCHEDULER_PID" $MYSCHEDULER_PORT  # ← ポート追加
    fi
    if [[ -z "$service_filter" || "$service_filter" == "jobqueue" ]]; then
        stop_service "JobQueue" "$JOBQUEUE_PID" $JOBQUEUE_PORT  # ← ポート追加
    fi
    # ... (Valkey処理は変更なし)
    ;;
```

---

## 5. パッチ適用手順

```bash
# 1. バックアップを作成
cp /Users/maenokota/share/work/github_kewton/MySwiftAgent/scripts/dev-start.sh \
   /Users/maenokota/share/work/github_kewton/MySwiftAgent/scripts/dev-start.sh.backup

# 2. エディタで修正
# 上記の修正内容を適用

# 3. テスト
./scripts/dev-start.sh status  # 現状確認
./scripts/dev-start.sh stop    # 停止テスト
./scripts/dev-start.sh start   # 起動テスト
```

---

## 6. 修正後の確認方法

```bash
# サービス起動
./scripts/dev-start.sh start

# 状態確認（PIDファイルの有無をチェック）
ls -la /Users/maenokota/share/work/github_kewton/MySwiftAgent/.pids/

# サービス停止（修正後は成功するはず）
./scripts/dev-start.sh stop

# すべてのサービスが停止したか確認
./scripts/dev-start.sh status
```

---

## トラブルシューティング

### Docker デーモンが起動していない

```bash
# Docker Desktop を起動
open -a Docker

# Docker デーモン状態確認
docker info

# または Colima を使用している場合
colima start
```

### サービスが停止できない場合

```bash
# 強制停止（最終手段）
pkill -f "uvicorn app.main:app"
pkill -f "streamlit run Home.py"
pkill -f "npm.*dev"
```

### PIDファイルを手動でクリーンアップ

```bash
rm -f /Users/maenokota/share/work/github_kewton/MySwiftAgent/.pids/*.pid
```

---

## 詳細な調査結果

完全な調査レポートは以下を参照:
- JSON: `/Users/maenokota/share/work/github_kewton/MySwiftAgent/dev-reports/bug-fix/20251116_000836/investigation-result.json`
- Markdown: `/Users/maenokota/share/work/github_kewton/MySwiftAgent/dev-reports/bug-fix/20251116_000836/investigation-summary.md`
