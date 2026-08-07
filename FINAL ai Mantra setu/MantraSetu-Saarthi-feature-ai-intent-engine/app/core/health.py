"""Core Health Monitoring and Aggregation Module for MantraSetu AgentOS.

This module provides BaseHealthCheck abstract interface and HealthAggregator for executing
concurrent component health probes and aggregating outcomes into unified HealthStatus domain models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import types
from typing import Mapping, Sequence

from app.core.exceptions import HealthCheckError
from app.core.models import (
    ComponentHealth,
    HealthStatus,
    SystemHealthStatus,
)


class BaseHealthCheck(ABC):
    """Abstract interface defining the contract for component health probes."""

    @property
    @abstractmethod
    def component_name(self) -> str:
        """Return the unique component identifier name string.

        Returns:
            str: Component name identifier.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Execute a component health probe and return a fully populated ComponentHealth model.

        Returns:
            ComponentHealth: Fully populated component health model.
        """
        ...


class HealthAggregator:
    """Health status aggregator coordinating component health probes.

    Responsibility:
        Maintains an immutable lookup table of registered BaseHealthCheck instances using MappingProxyType,
        validates duplicate registration during construction, schedules concurrent health check execution
        via asyncio.gather, aggregates component statuses into a unified HealthStatus model, and provides O(1) lookup.
    """

    def __init__(self, checks: Sequence[BaseHealthCheck]) -> None:
        """Initialize HealthAggregator with a sequence of BaseHealthCheck probes.

        Args:
            checks: Sequence of BaseHealthCheck instances.

        Raises:
            HealthCheckError: If duplicate component names are detected.
        """
        checks_dict: dict[str, BaseHealthCheck] = {}
        for check in checks:
            name = check.component_name
            if name in checks_dict:
                raise HealthCheckError(
                    f"Duplicate component health check registration for '{name}'."
                )
            checks_dict[name] = check

        self._checks_map: Mapping[str, BaseHealthCheck] = types.MappingProxyType(
            checks_dict
        )

    async def check_all(self) -> HealthStatus:
        """Execute all registered component health probes concurrently and aggregate outcomes.

        Returns:
            HealthStatus: Aggregated system health status model.
        """
        if not self._checks_map:
            return HealthStatus(
                healthy=True,
                status=SystemHealthStatus.HEALTHY,
                components={},
            )

        tasks = [self._safe_check(check) for check in self._checks_map.values()]
        results: list[ComponentHealth] = await asyncio.gather(*tasks)

        components_map: dict[str, ComponentHealth] = {}
        has_unhealthy = False
        has_degraded = False

        for comp in results:
            components_map[comp.component_name] = comp
            if comp.status == SystemHealthStatus.UNHEALTHY:
                has_unhealthy = True
            elif comp.status == SystemHealthStatus.DEGRADED:
                has_degraded = True

        if has_unhealthy:
            overall_status = SystemHealthStatus.UNHEALTHY
            all_healthy = False
        elif has_degraded:
            overall_status = SystemHealthStatus.DEGRADED
            all_healthy = False
        else:
            overall_status = SystemHealthStatus.HEALTHY
            all_healthy = True

        return HealthStatus(
            healthy=all_healthy,
            status=overall_status,
            components=components_map,
        )

    async def check_component(self, component_name: str) -> ComponentHealth | None:
        """Look up and execute ONLY the requested component health probe.

        Args:
            component_name: Target component name identifier string.

        Returns:
            ComponentHealth | None: Probe result model if found, None if unregistered.
        """
        if not component_name:
            return None

        check = self._checks_map.get(component_name)
        if not check:
            return None

        return await self._safe_check(check)

    # ------------------------------------------------------------------
    # Private Helper Methods
    # ------------------------------------------------------------------

    async def _safe_check(self, check: BaseHealthCheck) -> ComponentHealth:
        """Safely execute a single BaseHealthCheck probe catching all unexpected exceptions.

        Args:
            check: BaseHealthCheck instance.

        Returns:
            ComponentHealth: Component probe outcome model.
        """
        try:
            res = await check.health_check()
            if not isinstance(res, ComponentHealth):
                return ComponentHealth(
                    component_name=check.component_name,
                    status=SystemHealthStatus.UNHEALTHY,
                    message="Health probe returned an invalid response object.",
                    details={
                        "exception": "InvalidResponseType",
                        "component": check.component_name,
                    },
                )
            return res
        except Exception as exc:
            return ComponentHealth(
                component_name=check.component_name,
                status=SystemHealthStatus.UNHEALTHY,
                message="Health check probe failed due to an unhandled exception.",
                details={
                    "exception": exc.__class__.__name__,
                    "component": check.component_name,
                },
            )
