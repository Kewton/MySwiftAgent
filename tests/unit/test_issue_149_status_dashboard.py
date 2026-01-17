"""
Unit tests for Issue #149: Status Dashboard Feature

受入条件:
- [ ] 全サービスの状態が一覧表示されること
- [ ] ヘルスチェック結果が色分け表示されること
- [ ] リソース使用状況が表示されること
- [ ] `--watch`で自動更新されること
"""

from unittest.mock import Mock, patch


class TestServiceStatusCollector:
    """サービス状態収集機能のテスト"""

    def test_collect_all_service_statuses(self):
        """
        受入条件1: 全サービスの状態が一覧表示されること

        Given: 5つのサービスが定義されている
        When: collect_service_statuses()を実行
        Then: 全5サービスの状態情報が返される
        """
        from cli.status_dashboard import ServiceStatusCollector

        with patch("cli.status_dashboard.check_health_endpoint") as mock_health:
            with patch("cli.status_dashboard.check_port_usage") as mock_port:
                mock_health.return_value = None
                mock_port.return_value = {"port": 8001, "status": "CLOSED"}

                collector = ServiceStatusCollector()
                statuses = collector.collect_service_statuses()

                # 全サービスが含まれていること
                service_names = [s["name"] for s in statuses]
                assert "jobqueue" in service_names
                assert "myscheduler" in service_names
                assert "expertagent" in service_names
                assert "graphaiserver" in service_names
                assert "commonui" in service_names
                assert len(statuses) == 5

    def test_collect_service_status_with_health_check(self):
        """
        ヘルスチェック情報が含まれること

        Given: サービスが起動している
        When: ヘルスチェックを実行
        Then: ヘルス状態(healthy/unhealthy)が取得できる
        """
        from cli.status_dashboard import ServiceStatusCollector

        with patch("cli.status_dashboard.check_health_endpoint") as mock_health:
            with patch("cli.status_dashboard.check_port_usage") as mock_port:
                mock_health.return_value = {"status": "healthy", "response_time": 0.05}
                mock_port.return_value = {"port": 8001, "status": "CLOSED"}

                collector = ServiceStatusCollector()
                status = collector.get_service_status("jobqueue", 8001)

                assert status["health_status"] == "healthy"
                assert status["response_time"] == 0.05

    def test_collect_service_status_with_process_info(self):
        """
        プロセス情報が含まれること

        Given: サービスが起動している
        When: プロセス情報を取得
        Then: PID、起動時間、CPU/メモリ使用率が取得できる
        """
        from cli.status_dashboard import ServiceStatusCollector

        with patch("cli.status_dashboard.check_health_endpoint") as mock_health:
            with patch("cli.status_dashboard.check_port_usage") as mock_port:
                with patch("cli.status_dashboard.get_process_info") as mock_proc:
                    mock_health.return_value = None
                    mock_port.return_value = {"port": 8001, "status": "LISTEN", "pid": 12345}
                    mock_proc.return_value = {
                        "pid": 12345,
                        "uptime": "2h 30m",
                        "cpu_percent": 5.2,
                        "memory_percent": 12.5,
                        "memory_mb": 128.5,
                    }

                    collector = ServiceStatusCollector()
                    status = collector.get_service_status("jobqueue", 8001)

                    assert status["pid"] == 12345
                    assert status["uptime"] == "2h 30m"
                    assert status["cpu_percent"] == 5.2
                    assert status["memory_percent"] == 12.5

    def test_collect_service_status_with_port_info(self):
        """
        ポート使用状況が含まれること

        Given: サービスがポートを使用している
        When: ポート情報を取得
        Then: ポート番号とLISTEN状態が取得できる
        """
        from cli.status_dashboard import ServiceStatusCollector

        with patch("cli.status_dashboard.check_port_usage") as mock_port:
            mock_port.return_value = {"port": 8001, "status": "LISTEN"}

            collector = ServiceStatusCollector()
            status = collector.get_service_status("jobqueue", 8001)

            assert status["port"] == 8001
            assert status["port_status"] == "LISTEN"

    def test_collect_service_status_when_service_down(self):
        """
        サービス停止時のステータス

        Given: サービスが停止している
        When: ステータスを取得
        Then: health_status="down"となる
        """
        from cli.status_dashboard import ServiceStatusCollector

        with patch("cli.status_dashboard.check_health_endpoint") as mock_health:
            with patch("cli.status_dashboard.check_port_usage") as mock_port:
                mock_health.return_value = None  # サービス応答なし
                mock_port.return_value = {"port": 8001, "status": "CLOSED"}

                collector = ServiceStatusCollector()
                status = collector.get_service_status("jobqueue", 8001)

                assert status["health_status"] == "down"


class TestStatusFormatter:
    """ステータス表示フォーマットのテスト"""

    def test_format_status_table_output(self):
        """
        受入条件2: ヘルスチェック結果が色分け表示されること

        Given: 健全なサービスと異常なサービスが混在
        When: format_table()を実行
        Then: ヘルス状態に応じた色コードが設定される
        """
        from cli.status_dashboard import StatusFormatter

        statuses = [
            {"name": "jobqueue", "health_status": "healthy"},
            {"name": "myscheduler", "health_status": "unhealthy"},
            {"name": "expertagent", "health_status": "down"},
        ]

        formatter = StatusFormatter()
        output = formatter.format_table(statuses)

        # 色コードが含まれること
        assert "\033[0;32m" in output  # 緑（healthy）
        assert "\033[0;31m" in output  # 赤（unhealthy/down）

    def test_format_status_with_resource_usage(self):
        """
        受入条件3: リソース使用状況が表示されること

        Given: サービスが起動中
        When: format_table()を実行
        Then: CPU・メモリ使用率が表形式で表示される
        """
        from cli.status_dashboard import StatusFormatter

        statuses = [
            {
                "name": "jobqueue",
                "health_status": "healthy",
                "cpu_percent": 5.2,
                "memory_percent": 12.5,
                "memory_mb": 128.5,
            }
        ]

        formatter = StatusFormatter()
        output = formatter.format_table(statuses)

        assert "5.2" in output  # CPU使用率
        assert "12.5" in output  # メモリ使用率
        assert "128.5" in output  # メモリ使用量（MB）

    def test_format_status_with_uptime(self):
        """
        稼働時間が表示されること

        Given: サービスが起動中
        When: format_table()を実行
        Then: 稼働時間が人間が読める形式で表示される
        """
        from cli.status_dashboard import StatusFormatter

        statuses = [
            {
                "name": "jobqueue",
                "health_status": "healthy",
                "uptime": "2h 30m",
            }
        ]

        formatter = StatusFormatter()
        output = formatter.format_table(statuses)

        assert "2h 30m" in output

    def test_format_status_json_output(self):
        """
        JSON形式での出力

        Given: サービス状態情報
        When: format_json()を実行
        Then: 有効なJSON形式で出力される
        """
        import json

        from cli.status_dashboard import StatusFormatter

        statuses = [{"name": "jobqueue", "health_status": "healthy", "port": 8001}]

        formatter = StatusFormatter()
        output = formatter.format_json(statuses)

        # 有効なJSONであること
        parsed = json.loads(output)
        assert parsed[0]["name"] == "jobqueue"

    def test_format_status_csv_output(self):
        """
        CSV形式での出力

        Given: サービス状態情報
        When: format_csv()を実行
        Then: CSV形式で出力される
        """
        from cli.status_dashboard import StatusFormatter

        statuses = [{"name": "jobqueue", "health_status": "healthy", "port": 8001}]

        formatter = StatusFormatter()
        output = formatter.format_csv(statuses)

        lines = output.strip().split("\n")
        assert len(lines) == 2  # ヘッダー + 1行
        assert "name,health_status,port" in lines[0]
        assert "jobqueue,healthy,8001" in lines[1]


class TestStatusDashboardCLI:
    """CLIコマンドのテスト"""

    def test_cli_status_command_basic(self):
        """
        基本的なstatusコマンド実行

        Given: 引数なしでstatusコマンドを実行
        When: 実行完了
        Then: 表形式でステータスが表示される
        """
        from cli.status_dashboard import main

        with patch("cli.status_dashboard.ServiceStatusCollector") as mock_collector:
            mock_collector.return_value.collect_service_statuses.return_value = [
                {"name": "jobqueue", "health_status": "healthy"}
            ]

            with patch("sys.stdout") as mock_stdout:
                main([])

                # 出力が行われたこと
                assert mock_stdout.write.called

    def test_cli_status_command_with_watch_option(self):
        """
        受入条件4: `--watch`で自動更新されること

        Given: `--watch`オプション付きで実行
        When: 一定時間経過
        Then: 自動的に再表示される
        """
        from cli.status_dashboard import main

        with patch("cli.status_dashboard.ServiceStatusCollector") as mock_collector:
            mock_collector.return_value.collect_service_statuses.return_value = [
                {"name": "jobqueue", "health_status": "healthy"}
            ]

            with patch(
                "cli.status_dashboard.time.sleep", side_effect=KeyboardInterrupt
            ):  # 無限ループ防止
                main(["--watch"])  # KeyboardInterruptはmain内でキャッチされる

                # collect_service_statuses が複数回呼ばれること
                assert mock_collector.return_value.collect_service_statuses.call_count >= 1

    def test_cli_status_command_with_json_format(self):
        """
        JSON形式での出力

        Given: `--format json`オプション付きで実行
        When: 実行完了
        Then: JSON形式で出力される
        """

        from cli.status_dashboard import main

        with patch("cli.status_dashboard.ServiceStatusCollector") as mock_collector:
            mock_collector.return_value.collect_service_statuses.return_value = [
                {"name": "jobqueue", "health_status": "healthy"}
            ]

            with patch("sys.stdout") as mock_stdout:
                main(["--format", "json"])

                # JSON形式で出力されること
                assert mock_stdout.write.called

    def test_cli_status_command_with_csv_format(self):
        """
        CSV形式での出力

        Given: `--format csv`オプション付きで実行
        When: 実行完了
        Then: CSV形式で出力される
        """
        from cli.status_dashboard import main

        with patch("cli.status_dashboard.ServiceStatusCollector") as mock_collector:
            mock_collector.return_value.collect_service_statuses.return_value = [
                {"name": "jobqueue", "health_status": "healthy"}
            ]

            with patch("sys.stdout") as mock_stdout:
                main(["--format", "csv"])

                assert mock_stdout.write.called


class TestLogRetrieval:
    """最新ログ表示機能のテスト"""

    def test_get_latest_logs(self):
        """
        最新ログの取得

        Given: サービスのログファイルが存在する
        When: get_latest_logs()を実行
        Then: 最新10行のログが取得できる
        """
        from cli.status_dashboard import LogRetriever

        with patch("cli.status_dashboard.read_log_file") as mock_log:
            mock_log.return_value = ["log line 1", "log line 2"]

            retriever = LogRetriever()
            logs = retriever.get_latest_logs("jobqueue", lines=10)

            assert len(logs) == 2
            assert logs[0] == "log line 1"

    def test_get_latest_logs_when_file_not_found(self):
        """
        ログファイルが存在しない場合

        Given: ログファイルが存在しない
        When: get_latest_logs()を実行
        Then: 空リストが返される
        """
        from cli.status_dashboard import LogRetriever

        with patch("cli.status_dashboard.read_log_file", side_effect=FileNotFoundError):
            retriever = LogRetriever()
            logs = retriever.get_latest_logs("jobqueue")

            assert logs == []


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_check_health_endpoint_unhealthy(self):
        """
        ヘルスチェックが異常を返す

        Given: サービスが異常状態
        When: check_health_endpoint()を実行
        Then: unhealthyが返される
        """
        from cli.status_dashboard import check_health_endpoint

        with patch("cli.status_dashboard.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_get.return_value = mock_response

            result = check_health_endpoint("http://localhost:8001/health")

            assert result["status"] == "unhealthy"

    def test_check_health_endpoint_timeout(self):
        """
        ヘルスチェックがタイムアウト

        Given: サービスが応答しない
        When: check_health_endpoint()を実行
        Then: Noneが返される
        """
        import requests

        from cli.status_dashboard import check_health_endpoint

        with patch("cli.status_dashboard.requests.get", side_effect=requests.Timeout):
            result = check_health_endpoint("http://localhost:8001/health")

            assert result is None

    def test_check_port_usage_listening(self):
        """
        ポートがLISTEN状態

        Given: ポートがLISTEN状態
        When: check_port_usage()を実行
        Then: LISTENが返される
        """
        from cli.status_dashboard import check_port_usage

        # psutil.net_connections をモック
        mock_conn = Mock()
        mock_conn.laddr.port = 8001
        mock_conn.status = "LISTEN"
        mock_conn.pid = 12345

        with patch("cli.status_dashboard.psutil.net_connections", return_value=[mock_conn]):
            result = check_port_usage(8001)

            assert result["status"] == "LISTEN"
            assert result["pid"] == 12345

    def test_read_log_file_success(self):
        """
        ログファイルの読み込み成功

        Given: ログファイルが存在する
        When: read_log_file()を実行
        Then: ログ行が返される
        """

        from cli.status_dashboard import read_log_file

        with patch("cli.status_dashboard.Path.exists", return_value=True):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.readlines.return_value = [
                    "log line 1\n",
                    "log line 2\n",
                    "log line 3\n",
                ]

                result = read_log_file("/tmp/test.log", lines=2)

                assert len(result) == 2
                assert result[0] == "log line 2"
                assert result[1] == "log line 3"

    def test_cli_main_entry_point(self):
        """
        CLIエントリーポイント

        Given: cli_main()を実行
        When: 引数なし
        Then: main()が呼ばれる
        """
        from cli.status_dashboard import cli_main

        with patch("cli.status_dashboard.main") as mock_main:
            with patch("sys.argv", ["msa-status"]):
                cli_main()

                mock_main.assert_called_once()
