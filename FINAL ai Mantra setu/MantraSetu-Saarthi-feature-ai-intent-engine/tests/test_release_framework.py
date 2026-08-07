"""Unit & Integration Test Suite for Enterprise Release Management Framework v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.release import (
    ArtifactManager,
    CompatibilityManager,
    ProductionReadinessEvaluator,
    ReadinessRecommendation,
    ReleaseCertificationEngine,
    ReleasePipeline,
    ReleasePlanner,
    ReleaseReportEngine,
    ReleaseStage,
    ReleaseTelemetryEngine,
    ReleaseValidator,
    RollbackManager,
    SemanticVersion,
    VersionManager,
)


class TestReleaseManagementFramework(unittest.TestCase):
    """Test suite covering versioning, artifact integrity, compatibility, readiness, certification, SLAs, and thread safety."""

    def setUp(self):
        ReleaseTelemetryEngine.reset()
        self.version_mgr = VersionManager()
        self.artifact_mgr = ArtifactManager()
        self.compatibility_mgr = CompatibilityManager()
        self.release_validator = ReleaseValidator()
        self.rollback_mgr = RollbackManager()
        self.planner = ReleasePlanner()
        self.pipeline = ReleasePipeline()
        self.certification_engine = ReleaseCertificationEngine()
        self.readiness_evaluator = ProductionReadinessEvaluator()
        self.report_engine = ReleaseReportEngine()
        self.telemetry = ReleaseTelemetryEngine()

    def test_standard_module_interfaces(self):
        """Verify statistics(), health(), metrics() across all release management modules."""
        modules = [
            self.version_mgr,
            self.artifact_mgr,
            self.compatibility_mgr,
            self.release_validator,
            self.rollback_mgr,
            self.planner,
            self.pipeline,
            self.certification_engine,
            self.readiness_evaluator,
            self.report_engine,
            self.telemetry,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertEqual(health.get("status"), "HEALTHY")

    def test_semantic_version_resolution_performance(self):
        """Verify Version Resolution <1 ms SLA target."""
        start = time.perf_counter()
        ver = self.version_mgr.parse_version("1.2.3-rc.1+build.100")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(ver.major, 1)
        self.assertEqual(ver.minor, 2)
        self.assertEqual(ver.patch, 3)
        self.assertEqual(str(ver), "1.2.3-rc.1+build.100")
        self.assertLess(elapsed_ms, 1.0)

    def test_artifact_integrity_validation_performance(self):
        """Verify Artifact Validation <2 ms SLA target."""
        art = self.artifact_mgr.create_artifact(name="agentos-core", version="1.0.0", payload=b"test_payload_data")

        start = time.perf_counter()
        valid = self.artifact_mgr.verify_artifact_checksum(art.artifact_id, art.checksum_sha256)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertTrue(valid)
        self.assertLess(elapsed_ms, 2.0)

    def test_compatibility_validation_performance(self):
        """Verify Compatibility Validation <3 ms SLA target."""
        start = time.perf_counter()
        res = self.compatibility_mgr.validate_compatibility("1.0.0")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(res["overall_compatibility"], "COMPATIBLE")
        self.assertEqual(res["frameworks_validated_count"], 15)
        self.assertLess(elapsed_ms, 3.0)

    def test_production_readiness_scoring_performance(self):
        """Verify Production Readiness Evaluation <5 ms SLA target."""
        start = time.perf_counter()
        score = self.readiness_evaluator.evaluate(
            integration_passed=True,
            compatibility_passed=True,
            regression_passed=True,
            performance_passed=True,
            deployment_passed=True,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(score.overall_score, 100.0)
        self.assertEqual(score.grade, "A+")
        self.assertEqual(score.recommendation, ReadinessRecommendation.READY_FOR_RELEASE)
        self.assertLess(elapsed_ms, 5.0)

    def test_release_report_generation_performance(self):
        """Verify Release Report Generation <3 ms SLA target."""
        start = time.perf_counter()
        report = self.report_engine.generate_release_report("1.0.0", ReleaseStage.GENERAL_AVAILABILITY)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertIsNotNone(report.report_id)
        self.assertEqual(report.version_string, "1.0.0")
        self.assertEqual(report.readiness_score.overall_score, 100.0)
        self.assertGreater(len(report.release_notes), 0)
        self.assertLess(elapsed_ms, 3.0)

    def test_release_certification_and_rollback(self):
        cert = self.certification_engine.issue_certificate("1.0.0", 100.0)
        self.assertEqual(cert.release_version, "1.0.0")
        self.assertEqual(len(cert.signature_hash), 64)

        rollback = self.rollback_mgr.generate_rollback_plan("0.9.0")
        self.assertEqual(rollback.target_version, "0.9.0")
        self.assertGreater(len(rollback.recovery_steps), 0)

    def test_release_pipeline_execution(self):
        report = self.pipeline.execute_release_pipeline("1.0.0", ReleaseStage.GENERAL_AVAILABILITY)
        self.assertEqual(report.readiness_score.overall_score, 100.0)

    def test_thread_safety(self):
        def worker(i: int):
            pip = ReleasePipeline()
            _ = pip.execute_release_pipeline(f"1.0.{i}")

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(16)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
