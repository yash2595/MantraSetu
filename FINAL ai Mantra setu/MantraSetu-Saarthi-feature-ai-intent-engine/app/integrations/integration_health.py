"""Provider Health Monitoring & Status Engine for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any
from app.integrations.integration_models import (
    ProviderCategory,
    ProviderHealthState,
    ProviderHealthStatus,
)
from app.integrations.integration_registry import IntegrationRegistry


class IntegrationHealthManager:
    """Real-time provider health status & monitoring engine (<2 ms benchmark target)."""

    _instance: IntegrationHealthManager | None = None
    _lock: RLock = RLock()

    def __new__(cls) -> IntegrationHealthManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._statuses: dict[str, ProviderHealthStatus] = {}
                cls._instance._registry = IntegrationRegistry()
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset status cache for isolated test execution."""
        with cls._lock:
            if cls._instance:
                cls._instance._statuses.clear()

    def check_health(self, provider_id: str) -> ProviderHealthStatus:
        """Evaluate provider health status in <2 ms."""
        start = time.perf_counter()
        with self._lock:
            status = self._statuses.get(provider_id)
            if not status:
                status = ProviderHealthStatus(provider_id=provider_id)
                self._statuses[provider_id] = status

            adapter = self._registry.get_provider(provider_id)
            if adapter:
                try:
                    latency = adapter.ping()
                    status.latency_ms = round(latency, 3)
                    if status.consecutive_failures >= 3:
                        status.health_state = ProviderHealthState.DEGRADED
                    else:
                        status.health_state = ProviderHealthState.HEALTHY
                except Exception as exc:
                    status.consecutive_failures += 1
                    status.last_error = str(exc)
                    if status.consecutive_failures >= 5:
                        status.health_state = ProviderHealthState.UNHEALTHY
                    else:
                        status.health_state = ProviderHealthState.DEGRADED
            else:
                status.health_state = ProviderHealthState.UNKNOWN

            _ = (time.perf_counter() - start) * 1000.0
            return status

    def check_all_health(self) -> dict[str, ProviderHealthStatus]:
        """Check health status across all registered providers."""
        with self._lock:
            all_specs = self._registry.list_all_providers()
            results = {}
            for spec in all_specs:
                pid = spec["provider_id"]
                results[pid] = self.check_health(pid)
            return results

    def record_success(self, provider_id: str, latency_ms: float) -> None:
        """Record successful invocation."""
        with self._lock:
            status = self._statuses.get(provider_id)
            if not status:
                status = ProviderHealthStatus(provider_id=provider_id)
                self._statuses[provider_id] = status

            status.total_requests += 1
            status.successful_requests += 1
            status.consecutive_failures = 0
            status.latency_ms = round(latency_ms, 3)
            status.health_state = ProviderHealthState.HEALTHY

    def record_failure(self, provider_id: str, error_msg: str) -> None:
        """Record failed invocation."""
        with self._lock:
            status = self._statuses.get(provider_id)
            if not status:
                status = ProviderHealthStatus(provider_id=provider_id)
                self._statuses[provider_id] = status

            status.total_requests += 1
            status.failed_requests += 1
            status.consecutive_failures += 1
            status.last_error = error_msg

            if status.consecutive_failures >= 5:
                status.health_state = ProviderHealthState.UNHEALTHY
            elif status.consecutive_failures >= 2:
                status.health_state = ProviderHealthState.DEGRADED

    def get_healthy_providers(self, category: ProviderCategory) -> list[str]:
        """Get IDs of all healthy providers for a category."""
        with self._lock:
            adapters = self._registry.get_providers_by_category(category)
            healthy = []
            for adapter in adapters:
                pid = adapter.get_spec().provider_id
                st = self.check_health(pid)
                if st.health_state in (ProviderHealthState.HEALTHY, ProviderHealthState.DEGRADED):
                    healthy.append(pid)
            return healthy
