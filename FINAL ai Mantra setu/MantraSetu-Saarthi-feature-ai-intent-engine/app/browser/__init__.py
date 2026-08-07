"""Browser Automation subsystem for MantraSetu AgentOS."""

from app.browser.base import (
    BaseBrowserClient,
    BaseBrowserExecutor,
    BrowserError,
    BrowserExecutionError,
    BrowserInitializationError,
    BrowserNavigationError,
    BrowserSessionError,
)

# Sprint 9B Additions
from app.browser.browser_dashboard import (
    BrowserDashboard,
    BrowserDashboardSummary,
)
from app.browser.browser_executor import (
    BrowserActionSpec,
    BrowserActionType,
    EnterpriseBrowserExecutor,
)
from app.browser.browser_manager import (
    BrowserTab,
    EnterpriseBrowserManager,
    EnterpriseBrowserSession,
)
from app.browser.browser_safety_manager import (
    ApprovalRequest,
    BrowserSafetyManager,
    SafetyEvaluation,
)
from app.browser.browser_state_manager import (
    BrowserState,
    BrowserStateManager,
)
from app.browser.browser_telemetry import (
    BrowserEventType,
    BrowserTelemetry,
    BrowserTelemetryRecord,
)
from app.browser.dom_analyzer import (
    AccessibilityNode,
    DiscoveredForm,
    DOMAnalysisResult,
    DOMAnalyzer,
    DOMElement,
)
from app.browser.executor import BrowserExecutor
from app.browser.models import (
    BaseBrowserModel,
    BrowserActionResult,
    BrowserActionResultStatus,
    BrowserPage,
    BrowserSession,
    BrowserStatus,
)
from app.browser.page_reasoning_engine import (
    BrowserActionPlan,
    CompletionVerification,
    PageReasoningEngine,
)
from app.browser.playwright_client import PlaywrightBrowserClient
from app.browser.screenshot_validator import (
    ScreenshotVerification,
    ScreenshotValidator,
)
from app.browser.service import BrowserService

__all__ = [
    # Legacy / Base Exports
    "BaseBrowserModel",
    "BrowserStatus",
    "BrowserActionResultStatus",
    "BrowserSession",
    "BrowserPage",
    "BrowserActionResult",
    "BaseBrowserClient",
    "BaseBrowserExecutor",
    "PlaywrightBrowserClient",
    "BrowserExecutor",
    "BrowserService",
    "BrowserError",
    "BrowserSessionError",
    "BrowserNavigationError",
    "BrowserExecutionError",
    "BrowserInitializationError",
    # Sprint 9B Additions
    "BrowserTab",
    "EnterpriseBrowserSession",
    "EnterpriseBrowserManager",
    "DOMElement",
    "DiscoveredForm",
    "AccessibilityNode",
    "DOMAnalysisResult",
    "DOMAnalyzer",
    "BrowserActionType",
    "BrowserActionSpec",
    "EnterpriseBrowserExecutor",
    "BrowserActionPlan",
    "CompletionVerification",
    "PageReasoningEngine",
    "BrowserState",
    "BrowserStateManager",
    "ScreenshotVerification",
    "ScreenshotValidator",
    "ApprovalRequest",
    "SafetyEvaluation",
    "BrowserSafetyManager",
    "BrowserDashboardSummary",
    "BrowserDashboard",
    "BrowserEventType",
    "BrowserTelemetryRecord",
    "BrowserTelemetry",
]
