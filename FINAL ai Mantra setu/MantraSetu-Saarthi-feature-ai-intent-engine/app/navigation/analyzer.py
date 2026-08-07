"""Website Structure Analyzer Service orchestration layer for MantraSetu AgentOS.

This module implements NavigationAnalyzerService, coordinating website URL analysis requests with
an injected BaseNavigationAnalyzer implementation without browser SDKs or scraping logic.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.base import (
    BaseNavigationAnalyzer,
    NavigationError,
    NavigationInitializationError,
)
from app.navigation.models import WebsiteNode


class NavigationAnalyzerService:
    """Service facade coordinating website URL structure analysis requests.

    Responsibility:
        Validates URL analysis inputs, delegates page parsing and node discovery to an injected
        BaseNavigationAnalyzer instance, translates errors into domain exceptions, and manages lifecycle health.
    """

    def __init__(self, analyzer: BaseNavigationAnalyzer) -> None:
        """Initialize NavigationAnalyzerService with an injected BaseNavigationAnalyzer dependency.

        Args:
            analyzer: Injected BaseNavigationAnalyzer implementation.
        """
        self._analyzer = analyzer
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the analyzer service has been initialized.

        Raises:
            NavigationInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise NavigationInitializationError(
                "NavigationAnalyzerService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize analyzer service and underlying provider runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._analyzer, "initialize"):
            await self._analyzer.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close analyzer service and release provider connection resources."""
        if hasattr(self._analyzer, "close"):
            await self._analyzer.close()

        self._initialized = False

    async def analyze(
        self,
        url: str,
    ) -> tuple[WebsiteNode, ...]:
        """Validate web URL and discover website structure nodes via injected analyzer.

        Args:
            url: Page or website URL string to analyze.

        Returns:
            tuple[WebsiteNode, ...]: Immutable tuple of discovered WebsiteNode entities.

        Raises:
            NavigationInitializationError: If service is uninitialized.
            NavigationError: If URL is invalid or analysis fails.
        """
        self._require_initialized()
        if not url or not url.strip():
            raise NavigationError("URL parameter cannot be empty or blank.")

        try:
            return await self._analyzer.analyze(url)
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Website URL analysis failed for '{url}': {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the analyzer service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="navigation_analyzer_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="NavigationAnalyzerService uninitialized.",
            )

        analyzer_healthy = True
        if hasattr(self._analyzer, "health_check"):
            res = await self._analyzer.health_check()
            if isinstance(res, ComponentHealth):
                analyzer_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                analyzer_healthy = res

        return ComponentHealth(
            component_name="navigation_analyzer_service",
            status=SystemHealthStatus.HEALTHY if analyzer_healthy else SystemHealthStatus.UNHEALTHY,
            message="NavigationAnalyzerService operational."
            if analyzer_healthy
            else "NavigationAnalyzerService backend degraded.",
        )
