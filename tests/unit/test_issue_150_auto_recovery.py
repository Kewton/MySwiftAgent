"""
Unit tests for Issue #150: Auto Recovery
受入条件:
- 設定された条件で自動再起動が実行されること
- 再起動履歴が記録されること
- 無限ループに陥らないこと
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from scripts.auto_recovery import (
    AutoRecoveryManager,
    RecoveryAction,
    RecoveryHistory,
    RecoveryConfig,
    MaxRetriesExceededError,
)


class TestAutoRecoveryManager:
    """自動リカバリマネージャーのテスト"""

    def test_auto_restart_on_anomaly_detection(self):
        """
        受入条件: 設定された条件で自動再起動が実行されること
        Given: 自動リカバリが有効化されている
        When: サービス異常が検知される
        Then: サービスが自動的に再起動される
        """
        # Arrange
        config = RecoveryConfig(
            enabled=True,
            max_retries=3,
            retry_interval_seconds=5,
        )
        manager = AutoRecoveryManager(
            service_name="jobqueue",
            config=config,
        )

        # Act
        action = manager.handle_anomaly()

        # Assert
        assert action == RecoveryAction.RESTART
        assert manager.get_restart_count() == 1

    def test_no_restart_when_disabled(self):
        """
        Given: 自動リカバリが無効化されている
        When: サービス異常が検知される
        Then: 再起動は実行されない
        """
        # Arrange
        config = RecoveryConfig(enabled=False)
        manager = AutoRecoveryManager(
            service_name="myscheduler",
            config=config,
        )

        # Act
        action = manager.handle_anomaly()

        # Assert
        assert action == RecoveryAction.ALERT_ONLY
        assert manager.get_restart_count() == 0

    def test_max_retries_prevention(self):
        """
        受入条件: 無限ループに陥らないこと
        Given: 最大再試行回数が3回に設定されている
        When: 3回再起動を試行する
        Then: 4回目の試行時にエラーが発生する
        """
        # Arrange
        config = RecoveryConfig(
            enabled=True,
            max_retries=3,
            retry_interval_seconds=0,  # 間隔チェックを無効化
        )
        manager = AutoRecoveryManager(
            service_name="expertagent",
            config=config,
        )

        # Act & Assert
        manager.handle_anomaly()  # 1回目
        manager.handle_anomaly()  # 2回目
        manager.handle_anomaly()  # 3回目

        # 4回目はエラー
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            manager.handle_anomaly()

        assert "Maximum retries (3) exceeded" in str(exc_info.value)
        assert manager.get_restart_count() == 3

    def test_retry_interval_enforcement(self):
        """
        Given: 再試行間隔が60秒に設定されている
        When: 60秒以内に再度異常が発生する
        Then: 再起動はスキップされる
        """
        # Arrange
        config = RecoveryConfig(
            enabled=True,
            retry_interval_seconds=60,
        )
        manager = AutoRecoveryManager(
            service_name="graphaiserver",
            config=config,
        )

        # Act
        action1 = manager.handle_anomaly()
        action2 = manager.handle_anomaly()  # すぐに再実行

        # Assert
        assert action1 == RecoveryAction.RESTART
        assert action2 == RecoveryAction.WAIT  # 間隔が短すぎるため待機
        assert manager.get_restart_count() == 1  # 1回のみ

    def test_restart_count_reset_after_success(self):
        """
        Given: 再起動が2回実行されている
        When: サービスが正常に復帰する
        Then: 再起動カウントがリセットされる
        """
        # Arrange
        config = RecoveryConfig(
            enabled=True,
            max_retries=5,
            retry_interval_seconds=0,  # 間隔チェックを無効化
        )
        manager = AutoRecoveryManager(service_name="jobqueue", config=config)

        # Act
        manager.handle_anomaly()
        manager.handle_anomaly()
        assert manager.get_restart_count() == 2

        manager.reset_on_success()

        # Assert
        assert manager.get_restart_count() == 0


class TestRecoveryHistory:
    """再起動履歴記録のテスト"""

    def test_record_restart_history(self, tmp_path):
        """
        受入条件: 再起動履歴が記録されること
        Given: 履歴ファイルのパスが指定されている
        When: サービス再起動が実行される
        Then: 再起動履歴がファイルに記録される
        """
        # Arrange
        history_file = tmp_path / "recovery_history.json"
        history = RecoveryHistory(history_file=history_file)

        # Act
        history.record_restart(
            service_name="jobqueue",
            reason="Low success rate (0.6)",
            action=RecoveryAction.RESTART,
        )

        # Assert
        assert history_file.exists()
        records = history.get_records(service_name="jobqueue")
        assert len(records) == 1
        assert records[0]["service_name"] == "jobqueue"
        assert records[0]["reason"] == "Low success rate (0.6)"
        assert records[0]["action"] == "RESTART"

    def test_multiple_restart_records(self, tmp_path):
        """
        受入条件: 再起動履歴が記録されること
        Given: 複数のサービス再起動が発生する
        When: 各再起動を記録する
        Then: 全ての履歴が時系列順に保存される
        """
        # Arrange
        history_file = tmp_path / "recovery_history.json"
        history = RecoveryHistory(history_file=history_file)

        # Act
        history.record_restart(
            service_name="jobqueue",
            reason="High response time",
            action=RecoveryAction.RESTART,
        )
        history.record_restart(
            service_name="myscheduler",
            reason="Consecutive failures",
            action=RecoveryAction.RESTART,
        )

        # Assert
        all_records = history.get_all_records()
        assert len(all_records) == 2
        assert all_records[0]["service_name"] == "jobqueue"
        assert all_records[1]["service_name"] == "myscheduler"

    def test_get_restart_count_by_service(self, tmp_path):
        """
        Given: 複数サービスの再起動履歴がある
        When: 特定サービスの再起動回数を取得する
        Then: そのサービスの再起動回数が返される
        """
        # Arrange
        history_file = tmp_path / "recovery_history.json"
        history = RecoveryHistory(history_file=history_file)

        # Act
        history.record_restart("jobqueue", "reason1", RecoveryAction.RESTART)
        history.record_restart("jobqueue", "reason2", RecoveryAction.RESTART)
        history.record_restart("myscheduler", "reason3", RecoveryAction.RESTART)

        # Assert
        assert history.get_restart_count("jobqueue") == 2
        assert history.get_restart_count("myscheduler") == 1
        assert history.get_restart_count("expertagent") == 0

    def test_get_recent_restarts(self, tmp_path):
        """
        Given: 過去1時間以内の再起動履歴がある
        When: 最近の再起動履歴を取得する
        Then: 指定期間内の履歴のみが返される
        """
        # Arrange
        history_file = tmp_path / "recovery_history.json"
        history = RecoveryHistory(history_file=history_file)

        # Act
        old_time = datetime.now() - timedelta(hours=2)
        history.record_restart(
            "jobqueue",
            "old restart",
            RecoveryAction.RESTART,
            timestamp=old_time,
        )
        history.record_restart(
            "jobqueue",
            "recent restart",
            RecoveryAction.RESTART,
        )

        # Assert
        recent = history.get_recent_restarts(
            service_name="jobqueue",
            hours=1
        )
        assert len(recent) == 1
        assert recent[0]["reason"] == "recent restart"

    def test_clear_old_history(self, tmp_path):
        """
        Given: 古い再起動履歴がある
        When: 保持期間を超えた履歴を削除する
        Then: 古い履歴が削除される
        """
        # Arrange
        history_file = tmp_path / "recovery_history.json"
        history = RecoveryHistory(history_file=history_file)

        old_time = datetime.now() - timedelta(days=31)
        history.record_restart(
            "jobqueue",
            "old",
            RecoveryAction.RESTART,
            timestamp=old_time,
        )
        history.record_restart("jobqueue", "recent", RecoveryAction.RESTART)

        # Act
        history.clear_old_records(retention_days=30)

        # Assert
        all_records = history.get_all_records()
        assert len(all_records) == 1
        assert all_records[0]["reason"] == "recent"

    def test_load_existing_history_file(self, tmp_path):
        """
        Given: 既存の履歴ファイルがある
        When: RecoveryHistoryを初期化する
        Then: 既存の履歴が読み込まれる
        """
        # Arrange
        history_file = tmp_path / "recovery_history.json"

        # 最初のインスタンスで履歴を作成
        history1 = RecoveryHistory(history_file=history_file)
        history1.record_restart("jobqueue", "restart 1", RecoveryAction.RESTART)
        history1.record_restart("myscheduler", "restart 2", RecoveryAction.RESTART)

        # Act - 新しいインスタンスで既存ファイルを読み込み
        history2 = RecoveryHistory(history_file=history_file)

        # Assert
        loaded_records = history2.get_all_records()
        assert len(loaded_records) == 2
        assert loaded_records[0]["service_name"] == "jobqueue"
        assert loaded_records[1]["service_name"] == "myscheduler"


class TestRecoveryConfig:
    """リカバリ設定のテスト"""

    def test_default_config(self):
        """
        Given: デフォルト設定でRecoveryConfigを作成
        When: 設定値を確認する
        Then: デフォルト値が設定されている
        """
        # Arrange & Act
        config = RecoveryConfig()

        # Assert
        assert config.enabled is True
        assert config.max_retries == 3
        assert config.retry_interval_seconds == 60

    def test_custom_config(self):
        """
        Given: カスタム設定でRecoveryConfigを作成
        When: 設定値を確認する
        Then: カスタム値が設定されている
        """
        # Arrange & Act
        config = RecoveryConfig(
            enabled=False,
            max_retries=5,
            retry_interval_seconds=120,
        )

        # Assert
        assert config.enabled is False
        assert config.max_retries == 5
        assert config.retry_interval_seconds == 120

    def test_config_validation(self):
        """
        Given: 不正な設定値
        When: RecoveryConfigを作成する
        Then: バリデーションエラーが発生する
        """
        # Assert
        with pytest.raises(ValueError) as exc_info:
            RecoveryConfig(max_retries=-1)

        assert "max_retries must be positive" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info2:
            RecoveryConfig(retry_interval_seconds=-1)

        assert "retry_interval_seconds must be non-negative" in str(exc_info2.value)
