"""Browser Automation Application Service facade for MantraSetu AgentOS.

This module implements BrowserService as the primary facade layer exposing browser operations,
page navigation, element interaction actions, and operational health monitoring.
"""

from __future__ import annotations

from app.browser.base import (
    BaseBrowserClient,
    BaseBrowserExecutor,
    BrowserError,
    BrowserInitializationError,
)
from app.browser.models import (
    BrowserActionResult,
    BrowserPage,
)
from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.models import NavigationAction


class BrowserService:
    """Application facade service coordinating Browser Automation subsystem components.

    Responsibility:
        Exposes high-level browser operations (page loading, action execution, active page retrieval)
        by orchestrating injected BaseBrowserClient and BaseBrowserExecutor dependencies.
    """

    def __init__(
        self,
        client: BaseBrowserClient,
        executor: BaseBrowserExecutor,
    ) -> None:
        """Initialize BrowserService with injected client driver and action executor.

        Args:
            client: Injected BaseBrowserClient instance.
            executor: Injected BaseBrowserExecutor instance.
        """
        self._client = client
        self._executor = executor
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the browser service has been initialized.

        Raises:
            BrowserInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise BrowserInitializationError(
                "BrowserService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize browser service and underlying client runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._client, "initialize"):
            await self._client.initialize()
        if hasattr(self._executor, "initialize"):
            await self._executor.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close browser service and release client connections and browser resources."""
        if hasattr(self._executor, "close"):
            await self._executor.close()
        if hasattr(self._client, "close"):
            await self._client.close()

        self._initialized = False

    async def open_page(self, url: str) -> BrowserPage:
        """Navigate browser driver to target URL and return loaded page snapshot model.

        Args:
            url: Target URL string.

        Returns:
            BrowserPage: Loaded browser page domain model.

        Raises:
            BrowserInitializationError: If service is uninitialized.
            BrowserError: If URL is blank or navigation fails.
        """
        self._require_initialized()
        if not url or not url.strip():
            raise BrowserError("URL parameter string cannot be empty or blank.")

        try:
            return await self._client.open_page(url)
        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError(f"BrowserService failed to open page '{url}': {str(e)}") from e

    async def execute_action(
        self,
        action: NavigationAction,
    ) -> BrowserActionResult:
        """Execute a NavigationAction command through the injected browser executor.

        Args:
            action: NavigationAction model command.

        Returns:
            BrowserActionResult: Action execution outcome result model.

        Raises:
            BrowserInitializationError: If service is uninitialized.
            BrowserError: If action parameter is invalid or execution fails.
        """
        self._require_initialized()
        if not isinstance(action, NavigationAction):
            raise BrowserError("Invalid NavigationAction instance provided.")

        try:
            return await self._executor.execute(action)
        except BrowserError:
            raise
        except Exception as e:
            raise BrowserError(f"BrowserService action execution failed: {str(e)}") from e

    async def get_current_page(self) -> BrowserPage | None:
        """Retrieve snapshot of the current active browser page.

        Returns:
            BrowserPage | None: Active page model if loaded, None otherwise.

        Raises:
            BrowserInitializationError: If service is uninitialized.
        """
        self._require_initialized()
        return await self._client.get_current_page()

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the browser service and underlying driver client.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="browser_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="BrowserService uninitialized.",
            )

        client_health = await self._client.health_check()
        is_healthy = (
            isinstance(client_health, ComponentHealth)
            and client_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="browser_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="BrowserService operational."
            if is_healthy
            else "BrowserService client driver degraded.",
        )
