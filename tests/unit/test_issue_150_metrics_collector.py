"""
Unit tests for Issue #150: Metrics Collection
受入条件: サービス異常が自動検知されること
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List
from scripts.metrics_collector import (
    MetricsCollector,
    ServiceMetrics,
    HealthStatus,
    AnomalyDetector,
)


class TestMetricsCollector:
    """メトリクス収集機能のテスト"""

    def test_collect_response_time_metrics(self):
        """
        受入条件: サービス異常が自動検知されること
        Given: メトリクスコレクターが初期化されている
        When: サービスのレスポンス時間を記録する
        Then: レスポンス時間が正しく記録される
        """
        # Arrange
        collector = MetricsCollector(service_name="jobqueue")

        # Act
        collector.record_response_time(response_time=0.5)
        collector.record_response_time(response_time=0.3)
        collector.record_response_time(response_time=0.4)

        # Assert
        metrics = collector.get_metrics()
        assert metrics.avg_response_time == pytest.approx(0.4, rel=0.1)
        assert metrics.total_requests == 3

    def test_collect_success_rate_metrics(self):
        """
        受入条件: サービス異常が自動検知されること
        Given: メトリクスコレクターが初期化されている
        When: 成功/失敗のリクエストを記録する
        Then: 成功率が正しく計算される
        """
        # Arrange
        collector = MetricsCollector(service_name="myscheduler")

        # Act
        collector.record_request(success=True)
        collector.record_request(success=True)
        collector.record_request(success=False)
        collector.record_request(success=True)

        # Assert
        metrics = collector.get_metrics()
        assert metrics.success_rate == 0.75  # 3/4
        assert metrics.total_requests == 4
        assert metrics.failed_requests == 1

    def test_metrics_time_window(self):
        """
        Given: 5分間のタイムウィンドウが設定されている
        When: 古いメトリクスと新しいメトリクスを記録する
        Then: タイムウィンドウ外の古いメトリクスは除外される
        """
        # Arrange
        collector = MetricsCollector(
            service_name="expertagent",
            time_window_minutes=5
        )

        # Act
        old_time = datetime.now() - timedelta(minutes=10)
        collector.record_request(success=True, timestamp=old_time)
        collector.record_request(success=True)
        collector.record_request(success=False)

        # Assert
        metrics = collector.get_metrics()
        assert metrics.total_requests == 2  # 古いデータは除外

    def test_health_status_calculation(self):
        """
        受入条件: サービス異常が自動検知されること
        Given: メトリクスが収集されている
        When: ヘルスステータスを計算する
        Then: 成功率に基づいて正しいステータスが返される
        """
        # Arrange
        collector = MetricsCollector(service_name="jobqueue")

        # Act - 高成功率 (>=90%)
        for _ in range(95):
            collector.record_request(success=True)
        for _ in range(5):
            collector.record_request(success=False)

        # Assert
        assert collector.get_health_status() == HealthStatus.HEALTHY

        # Act - 中程度の成功率 (70-90%)
        collector.clear()
        for _ in range(75):
            collector.record_request(success=True)
        for _ in range(25):
            collector.record_request(success=False)

        # Assert
        assert collector.get_health_status() == HealthStatus.DEGRADED

        # Act - 低成功率（<70%、異常）
        collector.clear()
        for _ in range(50):
            collector.record_request(success=False)
        for _ in range(50):
            collector.record_request(success=True)

        # Assert
        assert collector.get_health_status() == HealthStatus.UNHEALTHY


class TestAnomalyDetector:
    """異常検知アルゴリズムのテスト"""

    def test_detect_low_success_rate_anomaly(self):
        """
        受入条件: サービス異常が自動検知されること
        Given: 成功率の閾値が80%に設定されている
        When: 成功率が80%未満になる
        Then: 異常として検知される
        """
        # Arrange
        detector = AnomalyDetector(success_rate_threshold=0.8)
        metrics = ServiceMetrics(
            service_name="jobqueue",
            success_rate=0.7,
            total_requests=100,
            failed_requests=30,
        )

        # Act
        is_anomaly = detector.detect_anomaly(metrics)

        # Assert
        assert is_anomaly is True

    def test_detect_high_response_time_anomaly(self):
        """
        受入条件: サービス異常が自動検知されること
        Given: レスポンス時間の閾値が2秒に設定されている
        When: 平均レスポンス時間が2秒を超える
        Then: 異常として検知される
        """
        # Arrange
        detector = AnomalyDetector(response_time_threshold=2.0)
        metrics = ServiceMetrics(
            service_name="myscheduler",
            avg_response_time=3.5,
            total_requests=50,
        )

        # Act
        is_anomaly = detector.detect_anomaly(metrics)

        # Assert
        assert is_anomaly is True

    def test_no_anomaly_when_metrics_healthy(self):
        """
        Given: 正常なメトリクス
        When: 異常検知を実行する
        Then: 異常なしと判定される
        """
        # Arrange
        detector = AnomalyDetector(
            success_rate_threshold=0.8,
            response_time_threshold=2.0
        )
        metrics = ServiceMetrics(
            service_name="expertagent",
            success_rate=0.95,
            avg_response_time=0.5,
            total_requests=100,
        )

        # Act
        is_anomaly = detector.detect_anomaly(metrics)

        # Assert
        assert is_anomaly is False

    def test_consecutive_failures_detection(self):
        """
        受入条件: サービス異常が自動検知されること
        Given: 連続失敗回数の閾値が3回に設定されている
        When: 3回連続で失敗する
        Then: 異常として検知される
        """
        # Arrange
        detector = AnomalyDetector(consecutive_failures_threshold=3)

        # Act & Assert
        assert detector.check_consecutive_failures(success=False) is False  # 1回目
        assert detector.check_consecutive_failures(success=False) is False  # 2回目
        assert detector.check_consecutive_failures(success=False) is True   # 3回目（検知）

        # 成功でリセット
        assert detector.check_consecutive_failures(success=True) is False
        assert detector.check_consecutive_failures(success=False) is False  # カウントリセット


class TestMetricsPersistence:
    """メトリクスの永続化のテスト"""

    def test_save_and_load_metrics(self, tmp_path):
        """
        Given: メトリクスが収集されている
        When: ファイルに保存して再読み込みする
        Then: メトリクスが正しく復元される
        """
        # Arrange
        from pathlib import Path
        metrics_file = tmp_path / "metrics.json"
        collector = MetricsCollector(service_name="jobqueue")

        # 10件の成功リクエストを記録
        for _ in range(10):
            collector.record_request(success=True)
            collector.record_response_time(0.5)

        # Act
        collector.save_to_file(metrics_file)

        # Assert
        assert metrics_file.exists()

        # 再読み込み
        loaded_collector = MetricsCollector.load_from_file(metrics_file)
        loaded_metrics = loaded_collector.get_metrics()

        assert loaded_metrics.total_requests == 10
        assert loaded_metrics.service_name == "jobqueue"


class TestServiceMetrics:
    """ServiceMetricsデータクラスのテスト"""

    def test_service_metrics_initialization(self):
        """
        Given: サービスメトリクスを初期化する
        When: 初期値を設定する
        Then: 正しく初期化される
        """
        # Arrange & Act
        metrics = ServiceMetrics(
            service_name="jobqueue",
            success_rate=0.98,
            avg_response_time=0.45,
            total_requests=200,
            failed_requests=4,
        )

        # Assert
        assert metrics.service_name == "jobqueue"
        assert metrics.success_rate == 0.98
        assert metrics.avg_response_time == 0.45
        assert metrics.total_requests == 200
        assert metrics.failed_requests == 4

    def test_service_metrics_to_dict(self):
        """
        Given: ServiceMetricsオブジェクト
        When: 辞書形式に変換する
        Then: 全フィールドが辞書に含まれる
        """
        # Arrange
        metrics = ServiceMetrics(
            service_name="myscheduler",
            success_rate=0.90,
            total_requests=100,
        )

        # Act
        metrics_dict = metrics.to_dict()

        # Assert
        assert "service_name" in metrics_dict
        assert "success_rate" in metrics_dict
        assert "total_requests" in metrics_dict
        assert metrics_dict["service_name"] == "myscheduler"
