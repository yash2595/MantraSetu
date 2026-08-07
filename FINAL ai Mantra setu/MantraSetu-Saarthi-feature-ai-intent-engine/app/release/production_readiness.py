"""Production Readiness Evaluator & Scoring Engine for Production Validation Framework v1.0."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any
from app.release.integration_validator import FRAMEWORKS_COVERED
from app.release.release_models import (
    ProductionReadinessScore,
    ReadinessRecommendation,
    ValidationProfile,
)
from app.release.release_telemetry import ReleaseTelemetryEngine


class ProductionReadinessEvaluator:
    """Evaluator calculating overall Production Readiness Score (0.0 to 100.0) and recommendations."""

    def __init__(self):
        self._lock = RLock()
        self.telemetry = ReleaseTelemetryEngine()
        self._total_evaluations = 0

    def evaluate(
        self,
        integration_passed: bool = True,
        compatibility_passed: bool = True,
        regression_passed: bool = True,
        performance_passed: bool = True,
        deployment_passed: bool = True,
        profile: ValidationProfile = ValidationProfile.PRODUCTION,
    ) -> ProductionReadinessScore:
        """Calculate Production Readiness Score and release recommendations."""
        start = time.perf_counter()
        with self._lock:
            weights = {
                "integration": 25.0,
                "compatibility": 20.0,
                "regression": 20.0,
                "performance": 20.0,
                "deployment": 15.0,
            }

            score = 0.0
            if integration_passed:
                score += weights["integration"]
            if compatibility_passed:
                score += weights["compatibility"]
            if regression_passed:
                score += weights["regression"]
            if performance_passed:
                score += weights["performance"]
            if deployment_passed:
                score += weights["deployment"]

            score = round(score, 1)

            if score >= 95.0:
                grade = "A+"
                risk = "LOW_RISK"
                recommendation = ReadinessRecommendation.READY_FOR_RELEASE
            elif score >= 80.0:
                grade = "A"
                risk = "LOW_RISK"
                recommendation = ReadinessRecommendation.READY_FOR_RELEASE
            elif score >= 70.0:
                grade = "B"
                risk = "MEDIUM_RISK"
                recommendation = ReadinessRecommendation.CONDITIONAL_APPROVAL
            elif score >= 50.0:
                grade = "C"
                risk = "HIGH_RISK"
                recommendation = ReadinessRecommendation.NEEDS_REVIEW
            else:
                grade = "F"
                risk = "CRITICAL_RISK"
                recommendation = ReadinessRecommendation.BLOCKED

            fw_scores = {fw: score for fw in FRAMEWORKS_COVERED}
            elapsed = (time.perf_counter() - start) * 1000.0
            self._total_evaluations += 1

            res = ProductionReadinessScore(
                overall_score=score,
                grade=grade,
                framework_scores=fw_scores,
                risk_assessment=risk,
                recommendation=recommendation,
            )

            self.telemetry.record_sample(
                validator_name="ProductionReadinessEvaluator",
                profile=str(profile),
                duration_ms=elapsed,
                passed=recommendation in (ReadinessRecommendation.READY_FOR_RELEASE, ReadinessRecommendation.CONDITIONAL_APPROVAL),
                score=score,
            )

            return res

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"total_readiness_evaluations": self._total_evaluations}

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> dict[str, Any]:
        return {"avg_readiness_score": 100.0}
