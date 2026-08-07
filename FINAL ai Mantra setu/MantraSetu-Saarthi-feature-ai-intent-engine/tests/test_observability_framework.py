"""Comprehensive Unit & Integration Test Suite for Enterprise Observability, Monitoring & Operations Framework v1.0."""

import time
import unittest
from app.observability.alert_manager import AlertManager
from app.observability.anomaly_detector import OperationalAnomalyDetector
from app.observability.dashboard_manager import DashboardManager
from app.observability.health_manager import HealthManager
from app.observability.logging_manager import LoggingManager
from app.observability.metrics_manager import MetricsManager
from app.observability.observability_models import (
    AlertSeverity,
    HealthState,
    LogLevel,
    MetricType,
    ServiceStatus,
)
from app.observability.observability_telemetry import ObservabilityTelemetryEngine
from app.observability.operations_manager import OperationsManager
from app.observability.sla_manager import SLAManager
from app.observability.tracing_manager import TracingManager


class TestMetricsLoggingAndTracing(unittest.TestCase):
    """Test suite for MetricsManager, LoggingManager, and TracingManager."""

    def setUp(self):
        self.metrics_mgr = MetricsManager()
        self.logging_mgr = LoggingManager()
        self.tracing_mgr = TracingManager()

    def test_metrics_collection(self):
        rec = self.metrics_mgr.record_metric("api_requests_total", 1.0, MetricType.COUNTER, {"endpoint": "/puja"})
        self.assertIsNotNone(rec)

        metrics = self.metrics_mgr.get_metric("api_requests_total")
        self.assertEqual(len(metrics), 1)

    def test_structured_logging(self):
        log_entry = self.logging_mgr.log(LogLevel.INFO, "User booked Satyanarayan Puja", trace_id="tr_100")
        self.assertIsNotNone(log_entry)

        search_res = self.logging_mgr.search_logs(level=LogLevel.INFO)
        self.assertGreaterEqual(len(search_res), 1)

    def test_distributed_tracing(self):
        context = self.tracing_mgr.start_trace("PujaBookingWorkflow")
        self.assertIsNotNone(context.trace_id)

        span = self.tracing_mgr.start_span(context, "PanditMatchingSpan")
        self.assertIsNotNone(span.span_id)
        self.tracing_mgr.finish_span(span)


class TestHealthAlertsSLAAndOperations(unittest.TestCase):
    """Test suite for HealthManager, AlertManager, SLAManager, AnomalyDetector, and OperationsManager."""

    def setUp(self):
        self.health_mgr = HealthManager()
        self.alert_mgr = AlertManager()
        self.sla_mgr = SLAManager()
        self.anomaly_detector = OperationalAnomalyDetector()
        self.ops_mgr = OperationsManager()

    def test_health_monitoring_and_aggregation(self):
        self.health_mgr.register_health("MemoryFramework", HealthState.HEALTHY)
        self.health_mgr.register_health("VoiceFramework", HealthState.HEALTHY)

        sys_health = self.health_mgr.get_system_health()
        self.assertEqual(sys_health.state, HealthState.HEALTHY)

    def test_alert_triggering_and_deduplication(self):
        alert1 = self.alert_mgr.trigger_alert("HighLatencyRule", AlertSeverity.WARNING, "P95 > 50ms")
        self.assertIsNotNone(alert1)

        # Trigger duplicate alert rule
        alert2 = self.alert_mgr.trigger_alert("HighLatencyRule", AlertSeverity.WARNING, "P95 > 50ms")
        self.assertIsNone(alert2)

    def test_sla_report_and_anomaly_detection(self):
        report = self.sla_mgr.generate_sla_report(uptime_percentage=99.99, p95_latency_ms=10.0)
        self.assertTrue(report.sla_target_met)

        anomalies = self.anomaly_detector.detect_anomalies([100.0, 150.0, 120.0], error_rate=0.10)
        self.assertGreaterEqual(len(anomalies), 2)

    def test_operations_manager_maintenance_mode(self):
        status = self.ops_mgr.set_maintenance_mode(True)
        self.assertEqual(status, ServiceStatus.MAINTENANCE)

        summary = self.ops_mgr.get_operational_summary()
        self.assertTrue(summary["is_maintenance_mode"])


if __name__ == "__main__":
    unittest.main()
