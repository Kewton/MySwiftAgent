# Bug Investigation Report: dev-start.sh stop コマンド PID ファイル問題

**調査日時**: 2025-11-16T00:08:36+09:00
**重要度**: Medium
**ステータス**: 調査完了

---

## エグゼクティブサマリー

`./scripts/dev-start.sh stop` コマンドが全サービスで「PID file not found」エラーを報告し、サービスを停止できない問題を調査しました。調査の結果、以下の主要な問題点が判明しました：

1. **実行中のサービスが dev-start.sh 経由で起動されていない**（PPID=1）
2. **PIDファイルが作成されていない**（valkey.pid のみ存在）
3. **ログファイルがすべて空**（0バイト）
4. **Dockerデーモンが停止している**

この問題は、スクリプトのPID管理メカニズムの脆弱性と、Docker依存性の不適切な処理に起因しています。

---

## 根本原因分析

### 主要な原因

**サービスが dev-start.sh スクリプト経由で起動されていないため、PIDファイルが作成されない**

### 技術的詳細

#### 1. サービスプロセスの親プロセスがinit（PID=1）

```bash
$ ps -p 72747,64978 -o pid,ppid,command
PID   PPID COMMAND
72747    1 .../myVault/.venv/bin/python3 .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8003
64978    1 .../commonUI/.venv/bin/python3 .venv/bin/streamlit run Home.py --server.port 8501 --server.headless true
```

**影響**: PPID=1 は親プロセスが終了したことを意味し、スクリプトのnohupプロセスが予期せず終了したか、手動起動されたことを示唆

#### 2. PIDディレクトリの状態

```bash
$ ls -lht /Users/maenokota/share/work/github_kewton/MySwiftAgent/.pids/
-rw-r--r--  1 maenokota  staff  5B Nov 15 23:49 valkey.pid
```

**影響**: MyVault、CommonUI、その他すべてのサービスのPIDファイルが存在しない

#### 3. すべてのログファイルが空（0バイト）

```bash
commonui.log (0 bytes, Nov 16 00:07)
myvault.log (0 bytes, Nov 16 00:07)
... (他のログも同様)
```

**影響**: dev-start.sh の start コマンドは実行されたが、サービスは正常に起動しなかった、またはログがリダイレクトされていない

#### 4. Dockerデーモン接続エラー

```
Cannot connect to the Docker daemon at unix:///Users/maenokota/.docker/run/docker.sock. Is the docker daemon running?
```

**影響**: Valkey（Docker経由で起動）が起動できず、Redis依存のサービスに影響

---

## 特定された問題点

### ISSUE-001: PIDファイル作成のタイミング問題 [HIGH]

**問題**: `start_service` 関数（L432-436）で `nohup` 起動後に `$!` でPIDを取得してPIDファイルに保存しているが、nohupプロセスが即座に終了する場合、子プロセス（実際のサービス）のPIDが記録されない

**該当コード**:
```bash
# scripts/dev-start.sh:432-436
nohup bash -c "$start_command" > "$log_file" 2>&1 &
local service_pid=$!

# Save PID
echo $service_pid > "$pid_file"
```

**リスク**: PIDファイルに記録されたPIDが実際のサービスプロセスのPIDと一致しない

### ISSUE-002: Docker依存性の明示的なチェック不足 [MEDIUM]

**問題**: Valkey起動前にDockerデーモンの接続確認を行っているが、失敗時の処理が不十分

**該当コード**: `scripts/dev-start.sh:851-884`

**リスク**: Docker未起動時に全体の起動が失敗し、適切なフォールバックがない

### ISSUE-003: ログファイルへのリダイレクト失敗 [LOW]

**問題**: `nohup` 実行時のログリダイレクト（`> $log_file 2>&1`）が期待通りに動作していない

**該当コード**: `scripts/dev-start.sh:432`

**リスク**: デバッグ情報が失われ、問題解決が困難になる

### ISSUE-004: stop_service関数のPIDファイル依存 [HIGH]

**問題**: `stop_service` 関数（L456-487）はPIDファイルの存在を前提としており、ファイルがない場合は何もせずに終了

**該当コード**:
```bash
# scripts/dev-start.sh:456-487
stop_service() {
    local name=$1
    local pid_file=$2

    if [[ -f "$pid_file" ]]; then
        # ... 停止処理
    else
        print_info "$name: PID file not found"
    fi
}
```

**リスク**: 実際に稼働中のプロセスを検出・停止する仕組みがなく、開発者が手動でプロセスをkillする必要がある

---

## 実行可能な解決策

### SOL-001: ポートベースのプロセス検出機能の追加 [HIGH] 🎯

**優先度**: 高（即座対応）
**予想工数**: 2-3時間

**概要**: `stop_service` 関数を拡張し、PIDファイルが存在しない場合でもポート番号からプロセスを検出して停止できるようにする

**実装手順**:
1. `stop_service` 関数にポート番号パラメータを追加
2. PIDファイルがない場合、`lsof -ti:{port}` でプロセスを検出
3. 検出したPIDに対してSIGTERMを送信
4. 10秒待機後も稼働していればSIGKILLを送信

**コード例**:
```bash
stop_service() {
    local name=$1
    local pid_file=$2
    local port=$3  # 新規追加

    local pid_to_stop=""

    # Try PID file first
    if [[ -f "$pid_file" ]]; then
        pid_to_stop=$(cat "$pid_file")
    # Fallback to port-based detection
    elif [[ -n "$port" ]]; then
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

**期待される効果**: PIDファイルの有無に関わらず、ポート占有プロセスを確実に停止できる

---

### SOL-002: PIDファイル作成の確実性向上 [HIGH] 🎯

**優先度**: 高（根本対策）
**予想工数**: 3-4時間

**概要**: nohup起動後、実際の子プロセスのPIDを確実に取得・記録する仕組みを実装

**実装手順**:
1. nohup起動後、ポート監視で実際のプロセスPIDを取得
2. `lsof -ti:{port}` で実PIDを取得してPIDファイルに保存
3. `wait_for_service` 成功後にPIDファイルの内容を検証

**コード例**:
```bash
# Start the service
nohup bash -c "$start_command" > "$log_file" 2>&1 &
local service_pid=$!

# Wait for service to bind to port
local attempt=0
while [[ $attempt -lt 30 ]]; do
    local actual_pid=$(lsof -ti:$port 2>/dev/null)
    if [[ -n "$actual_pid" ]]; then
        echo $actual_pid > "$pid_file"
        print_info "$name: PID $actual_pid recorded to $pid_file"
        break
    fi
    sleep 1
    ((attempt++))
done

if [[ ! -f "$pid_file" ]]; then
    print_error "$name: Failed to create PID file"
    return 1
fi
```

**期待される効果**: サービス起動時に必ずPIDファイルが作成され、stop時に利用可能になる

---

### SOL-003: Docker起動前チェックの強化 [MEDIUM]

**優先度**: 中（根本対策）
**予想工数**: 2-3時間

**概要**: Dockerデーモンの接続確認を起動前に実施し、失敗時の明確なエラーメッセージと回避策を提示

**実装手順**:
1. Docker依存サービス起動前に `docker info` でデーモン接続確認
2. 接続失敗時、ユーザーに明確なエラーメッセージを表示
3. `--skip-docker` オプションでDocker依存を回避可能にする

**コード例**:
```bash
check_docker_availability() {
    if ! command -v docker &> /dev/null; then
        return 1
    fi
    if ! docker info >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

# In start command
if [[ "$skip_docker" != true ]] && check_docker_availability; then
    # Start Valkey via Docker
else
    print_warning "Docker not available, using external Redis/Valkey"
    print_info "Set REDIS_URL or VALKEY_URL in environment to connect to external server"
fi
```

---

### SOL-004: ログ出力の診断機能追加 [MEDIUM]

**優先度**: 中（品質向上）
**予想工数**: 1-2時間

**概要**: ログファイルが空の場合の原因を診断し、デバッグ情報を提供

**実装手順**:
1. サービス起動後、ログファイルサイズをチェック
2. 0バイトの場合、プロセスが実際に稼働しているか確認
3. デバッグモードで stdout/stderr を端末に出力するオプション追加

---

### SOL-005: status コマンドの改善 [LOW]

**優先度**: 低（品質向上）
**予想工数**: 1-2時間

**概要**: PIDファイルに依存せず、ポートベースでサービス稼働状況を確認

**コード例**:
```bash
check_service_status() {
    local name=$1
    local pid_file=$2
    local port=$3

    local pid_from_file=""
    local pid_from_port=""

    [[ -f "$pid_file" ]] && pid_from_file=$(cat "$pid_file")
    pid_from_port=$(lsof -ti:$port 2>/dev/null)

    if [[ -n "$pid_from_file" && "$pid_from_file" == "$pid_from_port" ]]; then
        print_success "$name: Running (PID: $pid_from_file, Port: $port)"
    elif [[ -n "$pid_from_port" ]]; then
        print_warning "$name: Running but PID file mismatch (Port PID: $pid_from_port, File: ${pid_from_file:-none})"
    else
        print_error "$name: Not running"
    fi
}
```

---

## 推奨アプローチ

### Phase 1: 即座対応（1-2日）

**目的**: stopコマンドが動作しない問題を最優先で解決

**タスク**:
- ✅ **SOL-001**: ポートベースのプロセス検出機能の実装（stop強化）
- ✅ **SOL-005**: statusコマンドの改善（現状把握の改善）

### Phase 2: 根本対策（3-5日）

**目的**: PIDファイル管理の信頼性を向上させ、Docker依存の問題を解消

**タスク**:
- ✅ **SOL-002**: PIDファイル作成の確実性向上
- ✅ **SOL-003**: Docker起動前チェックの強化

### Phase 3: 品質向上（1-2日）

**目的**: デバッグ効率を向上させ、将来の問題解決を迅速化

**タスク**:
- ✅ **SOL-004**: ログ出力の診断機能追加

---

## テスト計画

### ユニットテスト
- `stop_service` 関数: PIDファイルあり/なしの両ケース
- `stop_service` 関数: ポート検出による停止
- `check_service_status` 関数: PIDファイルとポート状態の不一致検出

### 統合テスト
- `dev-start.sh start -> stop` のフルサイクル
- Docker未起動時の起動スクリプト動作
- 手動起動サービスの stopコマンドによる停止

### リグレッションテスト
- 既存の正常起動ケースの動作確認
- 複数サービス同時起動・停止
- ログファイルの正常記録確認

---

## エビデンス

### 実行中のプロセス

| サービス | PID | PPID | ポート | 起動時刻 |
|---------|-----|------|-------|----------|
| MyVault | 72747 | 1 | 8003 | Sat Nov 15 23:55:09 2025 |
| CommonUI | 64978 | 1 | 8501 | Sat Nov 15 23:55:09 2025 |

### PIDファイル状態

| ファイル | 内容 | 更新時刻 |
|---------|------|----------|
| valkey.pid | 8239 | Nov 15 23:49 |
| **その他すべて** | **存在しない** | - |

### ログファイル状態

すべてのログファイルが **0バイト**（Nov 16 00:07更新）:
- commonui.log
- expertagent.log
- graphaiserver.log
- jobqueue.log
- myscheduler.log
- myvault.log
- myagentdesk.log
- valkey.log
- setup.log

---

## 追加観察事項

1. **サービスがPPID=1で稼働**: 手動起動またはnohupの親プロセス終了が発生
2. **ログファイルが0バイト**: dev-start.shのstartコマンドは実行されたが、サービスは別の方法で起動された可能性
3. **Dockerデーモン停止**: 複数のエラーの起点となっている可能性

---

## 関連ファイル

- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/scripts/dev-start.sh`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/.pids/`
- `/Users/maenokota/share/work/github_kewton/MySwiftAgent/logs/`

---

## 次のステップ

1. **SOL-001とSOL-005を即座に実装**して、stopコマンドとstatusコマンドを修正
2. **ユーザーに確認**: サービスはどのように起動されたのか？（手動 or スクリプト）
3. **Dockerデーモンの再起動手順を確認**し、ドキュメント化
4. **SOL-002、SOL-003を実装**してPID管理とDocker依存の根本対策
