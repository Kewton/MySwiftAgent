"""
Integration tests for Issue #150: Auto Recovery Acceptance Tests
全受入条件を検証する統合テスト
"""

import pytest
import time
import subprocess
from pathlib import Path
from scripts.auto_recovery import AutoRecoveryManager, RecoveryConfig
from scripts.metrics_collector import MetricsCollector, AnomalyDetector


class TestAutoRecoveryAcceptance:
    """自動リカバリ機能の受入テスト"""

    @pytest.fixture
    def setup_test_environment(self, tmp_path):
        """テスト環境のセットアップ"""
        history_file = tmp_path / "recovery_history.json"
        config = RecoveryConfig(
            enabled=True,
            max_retries=3,
            retry_interval_seconds=5,
        )
        return {
            "history_file": history_file,
            "config": config,
        }

    def test_acceptance_1_anomaly_detection(self, setup_test_environment):
        """
        受入条件1: サービス異常が自動検知されること

        Given: メトリクス収集が有効化されている
        When: サービスの成功率が80%未満になる
        Then: 異常として検知される
        """
        # Arrange
        collector = MetricsCollector(service_name="jobqueue")
        detector = AnomalyDetector(success_rate_threshold=0.8)

        # Act - 成功率60%のメトリクスを生成
        for _ in range(60):
            collector.record_request(success=True)
        for _ in range(40):
            collector.record_request(success=False)

        metrics = collector.get_metrics()
        is_anomaly = detector.detect_anomaly(metrics)

        # Assert
        assert metrics.success_rate == 0.6
        assert is_anomaly is True, "成功率80%未満で異常検知されるべき"

    def test_acceptance_2_auto_restart_execution(self, setup_test_environment):
        """
        受入条件2: 設定された条件で自動再起動が実行されること

        Given: 自動リカバリが有効化されている
        When: サービス異常が検知される
        Then: サービスが自動的に再起動される
        """
        # Arrange
        config = setup_test_environment["config"]
        manager = AutoRecoveryManager(
            service_name="jobqueue",
            config=config,
        )

        # Act
        action = manager.handle_anomaly()

        # Assert
        assert action.name == "RESTART", "異常検知時に再起動アクションが実行されるべき"
        assert manager.get_restart_count() == 1

    def test_acceptance_3_restart_history_recording(self, setup_test_environment):
        """
        受入条件3: 再起動履歴が記録されること

        Given: 自動リカバリマネージャーが設定されている
        When: サービスが再起動される
        Then: 再起動履歴がファイルに記録される
        """
        # Arrange
        from scripts.auto_recovery import RecoveryHistory, RecoveryAction
        history_file = setup_test_environment["history_file"]
        history = RecoveryHistory(history_file=history_file)

        # Act
        history.record_restart(
            service_name="jobqueue",
            reason="Low success rate: 0.6",
            action=RecoveryAction.RESTART,
        )

        # Assert
        assert history_file.exists(), "履歴ファイルが作成されるべき"
        records = history.get_records(service_name="jobqueue")
        assert len(records) == 1, "再起動履歴が記録されるべき"
        assert records[0]["service_name"] == "jobqueue"
        assert "Low success rate" in records[0]["reason"]

    def test_acceptance_4_infinite_loop_prevention(self, setup_test_environment):
        """
        受入条件4: 無限ループに陥らないこと

        Given: 最大再試行回数が3回に設定されている
        When: 連続して異常が検知される
        Then: 3回再起動後、それ以上の再起動は実行されない
        """
        # Arrange
        config = RecoveryConfig(
            enabled=True,
            max_retries=3,
            retry_interval_seconds=0,  # 間隔チェックを無効化
        )
        manager = AutoRecoveryManager(
            service_name="myscheduler",
            config=config,
        )

        # Act & Assert - 3回まで再起動可能
        manager.handle_anomaly()  # 1回目
        manager.handle_anomaly()  # 2回目
        manager.handle_anomaly()  # 3回目

        assert manager.get_restart_count() == 3

        # 4回目はエラー
        from scripts.auto_recovery import MaxRetriesExceededError
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            manager.handle_anomaly()

        assert "Maximum retries (3) exceeded" in str(exc_info.value)
        assert manager.get_restart_count() == 3, "再起動回数は3回で止まるべき"

    def test_end_to_end_auto_recovery_workflow(self, setup_test_environment):
        """
        エンドツーエンド: メトリクス収集 → 異常検知 → 自動再起動 → 履歴記録

        Given: 自動リカバリシステムが稼働している
        When: サービスで異常が発生する
        Then: 異常検知から再起動、履歴記録まで自動的に実行される
        """
        # Arrange
        from scripts.auto_recovery import RecoveryHistory, RecoveryAction

        collector = MetricsCollector(service_name="expertagent")
        detector = AnomalyDetector(success_rate_threshold=0.8)
        config = setup_test_environment["config"]
        manager = AutoRecoveryManager(
            service_name="expertagent",
            config=config,
        )
        history = RecoveryHistory(
            history_file=setup_test_environment["history_file"]
        )

        # Act - Step 1: 異常なメトリクスを生成
        for _ in range(50):
            collector.record_request(success=True)
        for _ in range(50):
            collector.record_request(success=False)

        metrics = collector.get_metrics()

        # Step 2: 異常検知
        is_anomaly = detector.detect_anomaly(metrics)
        assert is_anomaly is True

        # Step 3: 自動再起動
        action = manager.handle_anomaly()
        assert action == RecoveryAction.RESTART

        # Step 4: 履歴記録
        history.record_restart(
            service_name="expertagent",
            reason=f"Success rate: {metrics.success_rate}",
            action=action,
        )

        # Assert - 全工程が正常に完了
        restart_records = history.get_records(service_name="expertagent")
        assert len(restart_records) == 1
        assert restart_records[0]["action"] == "RESTART"
        assert manager.get_restart_count() == 1

    def test_metrics_persistence(self, tmp_path):
        """
        メトリクスの永続化テスト

        Given: メトリクスが収集されている
        When: メトリクスをファイルに保存する
        Then: メトリクスが永続化される
        """
        # Arrange
        collector = MetricsCollector(service_name="jobqueue")
        metrics_file = tmp_path / "metrics.json"

        # Act
        for _ in range(10):
            collector.record_request(success=True)
            collector.record_response_time(0.5)

        collector.save_to_file(metrics_file)

        # Assert
        assert metrics_file.exists()

        # 再読み込み
        loaded_collector = MetricsCollector.load_from_file(metrics_file)
        loaded_metrics = loaded_collector.get_metrics()

        assert loaded_metrics.total_requests == 10
        assert loaded_metrics.service_name == "jobqueue"

    def test_retry_interval_prevents_rapid_restarts(self, setup_test_environment):
        """
        再試行間隔により急速な再起動を防止

        Given: 再試行間隔が5秒に設定されている
        When: 5秒以内に再度異常が発生する
        Then: 再起動はスキップされる
        """
        # Arrange
        config = setup_test_environment["config"]
        manager = AutoRecoveryManager(
            service_name="graphaiserver",
            config=config,
        )

        # Act
        action1 = manager.handle_anomaly()
        time.sleep(1)  # 1秒待機（5秒未満）
        action2 = manager.handle_anomaly()

        # Assert
        from scripts.auto_recovery import RecoveryAction
        assert action1 == RecoveryAction.RESTART
        assert action2 == RecoveryAction.WAIT, "間隔が短すぎる場合は待機すべき"
        assert manager.get_restart_count() == 1

    def test_recovery_after_success(self, setup_test_environment):
        """
        サービス復旧後のリセット

        Given: 2回再起動が実行されている
        When: サービスが正常に復帰する
        Then: 再起動カウントがリセットされる
        """
        # Arrange
        config = RecoveryConfig(
            enabled=True,
            max_retries=5,
            retry_interval_seconds=0,  # 間隔チェックを無効化
        )
        manager = AutoRecoveryManager(
            service_name="myscheduler",
            config=config,
        )

        # Act
        manager.handle_anomaly()
        manager.handle_anomaly()
        assert manager.get_restart_count() == 2

        # サービス復旧
        manager.reset_on_success()

        # Assert
        assert manager.get_restart_count() == 0, "復旧後はカウントリセットされるべき"
