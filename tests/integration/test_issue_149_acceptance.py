"""
Acceptance tests for Issue #149: Status Dashboard Feature

受入条件:
- [ ] 全サービスの状態が一覧表示されること
- [ ] ヘルスチェック結果が色分け表示されること
- [ ] リソース使用状況が表示されること
- [ ] `--watch`で自動更新されること
"""

import pytest
from unittest.mock import Mock, patch
import subprocess


class TestAcceptanceCriteria:
    """受入条件のテスト"""

    def test_acceptance_01_display_all_services(self):
        """
        受入条件1: 全サービスの状態が一覧表示されること

        Given: StatusDashboardCLIツールが利用可能
        When: statusコマンドを実行
        Then: 全5サービス(jobqueue, myscheduler, expertagent, graphaiserver, commonui)が一覧表示される
        """
        from cli.status_dashboard import ServiceStatusCollector

        with patch("cli.status_dashboard.check_health_endpoint") as mock_health:
            with patch("cli.status_dashboard.check_port_usage") as mock_port:
                mock_health.return_value = {"status": "healthy", "response_time": 0.01}
                mock_port.return_value = {"port": 8001, "status": "LISTEN", "pid": 12345}

                collector = ServiceStatusCollector()
                statuses = collector.collect_service_statuses()

                # 全5サービスが含まれていること
                service_names = [s["name"] for s in statuses]
                assert "jobqueue" in service_names, "jobqueue が一覧に含まれていない"
                assert "myscheduler" in service_names, "myscheduler が一覧に含まれていない"
                assert "expertagent" in service_names, "expertagent が一覧に含まれていない"
                assert (
                    "graphaiserver" in service_names
                ), "graphaiserver が一覧に含まれていない"
                assert "commonui" in service_names, "commonui が一覧に含まれていない"
                assert len(statuses) == 5, f"サービス数が5でない: {len(statuses)}"

    def test_acceptance_02_health_check_colored_display(self):
        """
        受入条件2: ヘルスチェック結果が色分け表示されること

        Given: 健全なサービスと異常なサービスが混在
        When: ステータスをフォーマットして表示
        Then: 健全=緑、異常=赤で色分け表示される
        """
        from cli.status_dashboard import StatusFormatter

        statuses = [
            {"name": "jobqueue", "health_status": "healthy"},
            {"name": "myscheduler", "health_status": "unhealthy"},
            {"name": "expertagent", "health_status": "down"},
        ]

        formatter = StatusFormatter()
        output = formatter.format_table(statuses)

        # 緑色コードが含まれること（healthy）
        assert (
            "\033[0;32m" in output
        ), "健全なサービスに対する緑色コードが含まれていない"

        # 赤色コードが含まれること（unhealthy/down）
        assert "\033[0;31m" in output, "異常なサービスに対する赤色コードが含まれていない"

        # 各サービス名が含まれること
        assert "jobqueue" in output, "jobqueue が出力に含まれていない"
        assert "myscheduler" in output, "myscheduler が出力に含まれていない"
        assert "expertagent" in output, "expertagent が出力に含まれていない"

    def test_acceptance_03_resource_usage_display(self):
        """
        受入条件3: リソース使用状況が表示されること

        Given: サービスが起動中でリソース情報が取得可能
        When: ステータスをフォーマットして表示
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
                "uptime": "2h 30m",
            }
        ]

        formatter = StatusFormatter()
        output = formatter.format_table(statuses)

        # リソース使用率が含まれること
        assert "5.2" in output, "CPU使用率が含まれていない"
        assert "12.5" in output, "メモリ使用率が含まれていない"
        assert "128.5" in output, "メモリ使用量（MB）が含まれていない"
        assert "2h 30m" in output, "稼働時間が含まれていない"

    def test_acceptance_04_watch_mode_auto_update(self):
        """
        受入条件4: `--watch`で自動更新されること

        Given: `--watch`オプション付きで実行
        When: 一定時間経過後にKeyboardInterrupt
        Then: 複数回ステータスが取得・表示される
        """
        from cli.status_dashboard import main

        with patch("cli.status_dashboard.ServiceStatusCollector") as mock_collector:
            mock_collector.return_value.collect_service_statuses.return_value = [
                {"name": "jobqueue", "health_status": "healthy"}
            ]

            # 2回目のsleepでKeyboardInterruptを発生させる
            sleep_count = [0]

            def side_effect_sleep(seconds):
                sleep_count[0] += 1
                if sleep_count[0] >= 2:
                    raise KeyboardInterrupt

            with patch("cli.status_dashboard.time.sleep", side_effect=side_effect_sleep):
                # KeyboardInterruptは main内でキャッチされる
                main(["--watch"])

                # collect_service_statuses が複数回呼ばれたことを確認
                call_count = (
                    mock_collector.return_value.collect_service_statuses.call_count
                )
                assert (
                    call_count >= 2
                ), f"collect_service_statusesの呼び出し回数が2回未満: {call_count}"

    def test_acceptance_json_output_format(self):
        """
        追加機能: JSON形式での出力

        Given: `--format json`オプション付きで実行
        When: ステータスを取得
        Then: 有効なJSON形式で出力される
        """
        from cli.status_dashboard import main
        import json

        with patch("cli.status_dashboard.ServiceStatusCollector") as mock_collector:
            mock_collector.return_value.collect_service_statuses.return_value = [
                {"name": "jobqueue", "health_status": "healthy", "port": 8001}
            ]

            with patch("sys.stdout") as mock_stdout:
                main(["--format", "json"])

                # stdout.writeが呼ばれたことを確認
                assert mock_stdout.write.called, "stdout.writeが呼ばれていない"

                # 書き込まれた内容を取得
                written_content = "".join(
                    [call[0][0] for call in mock_stdout.write.call_args_list]
                )

                # 有効なJSONであることを確認
                try:
                    parsed = json.loads(written_content.strip())
                    assert isinstance(parsed, list), "JSONがリスト形式でない"
                    assert len(parsed) > 0, "JSONが空"
                    assert parsed[0]["name"] == "jobqueue", "サービス名が不正"
                except json.JSONDecodeError as e:
                    pytest.fail(f"JSONパースエラー: {e}")

    def test_acceptance_csv_output_format(self):
        """
        追加機能: CSV形式での出力

        Given: `--format csv`オプション付きで実行
        When: ステータスを取得
        Then: CSV形式で出力される
        """
        from cli.status_dashboard import main

        with patch("cli.status_dashboard.ServiceStatusCollector") as mock_collector:
            mock_collector.return_value.collect_service_statuses.return_value = [
                {"name": "jobqueue", "health_status": "healthy", "port": 8001}
            ]

            with patch("sys.stdout") as mock_stdout:
                main(["--format", "csv"])

                # stdout.writeが呼ばれたことを確認
                assert mock_stdout.write.called, "stdout.writeが呼ばれていない"

                # 書き込まれた内容を取得
                written_content = "".join(
                    [call[0][0] for call in mock_stdout.write.call_args_list]
                )

                # CSVヘッダーが含まれること
                assert "name" in written_content, "CSVヘッダーにnameが含まれていない"
                assert (
                    "health_status" in written_content
                ), "CSVヘッダーにhealth_statusが含まれていない"

                # CSVデータが含まれること
                assert "jobqueue" in written_content, "CSVデータにjobqueueが含まれていない"
                assert (
                    "healthy" in written_content
                ), "CSVデータにhealthyが含まれていない"


class TestEndToEndScenario:
    """エンドツーエンドシナリオテスト"""

    def test_e2e_full_workflow(self):
        """
        エンドツーエンド: 完全なワークフロー

        Given: CLIツールが利用可能
        When: 以下の一連の操作を実行
          1. 通常モードでステータス表示
          2. JSON形式でステータス出力
          3. CSV形式でステータス出力
        Then: すべての操作が正常に完了する
        """
        from cli.status_dashboard import main, ServiceStatusCollector

        mock_statuses = [
            {
                "name": "jobqueue",
                "health_status": "healthy",
                "port": 8001,
                "cpu_percent": 5.0,
                "memory_percent": 10.0,
            },
            {
                "name": "myscheduler",
                "health_status": "healthy",
                "port": 8002,
                "cpu_percent": 3.0,
                "memory_percent": 8.0,
            },
        ]

        with patch("cli.status_dashboard.ServiceStatusCollector") as mock_collector:
            mock_collector.return_value.collect_service_statuses.return_value = (
                mock_statuses
            )

            # 1. 通常モードでステータス表示
            with patch("sys.stdout") as mock_stdout:
                main([])
                assert mock_stdout.write.called

            # 2. JSON形式でステータス出力
            with patch("sys.stdout") as mock_stdout:
                main(["--format", "json"])
                assert mock_stdout.write.called

            # 3. CSV形式でステータス出力
            with patch("sys.stdout") as mock_stdout:
                main(["--format", "csv"])
                assert mock_stdout.write.called
