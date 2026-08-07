"""Browser Session package.

Public API:
    BrowserSession        — abstract base class (depend on this, not the concrete class).
    BrowserSessionError   — only permitted error type (invalid arguments only).
    BrowserState          — browser lifecycle state enum.
    BrowserSessionResult  — immutable lifecycle result model.
    DefaultBrowserSession — placeholder concrete implementation.

Lifecycle:
    BrowserSession, BrowserContext, BrowserPage, BrowserDriver, BrowserActions,
    and BrowserNavigation instances must be created and owned by the ServiceContainer.

Future backends:
    Replace DefaultBrowserSession with PlaywrightBrowserSession,
    DefaultBrowserContext with PlaywrightBrowserContext,
    DefaultBrowserPage with PlaywrightBrowserPage,
    DefaultBrowserDriver with PlaywrightBrowserDriver,
    DefaultBrowserActions with PlaywrightBrowserActions, and
    PlaywrightNavigation with other implementations inside the
    ServiceContainer without changing any other module.
"""

from app.services.browser.actions_base import BrowserActionError, BrowserActions
from app.services.browser.actions_models import ActionState, BrowserActionResult
from app.services.browser.actions_service import DefaultBrowserActions
from app.services.browser.base import BrowserSession, BrowserSessionError
from app.services.browser.context_base import BrowserContext, BrowserContextError
from app.services.browser.context_models import BrowserContextResult, ContextState
from app.services.browser.context_service import DefaultBrowserContext
from app.services.browser.driver_base import BrowserDriver, BrowserDriverError
from app.services.browser.driver_models import BrowserDriverResult, DriverState
from app.services.browser.driver_service import DefaultBrowserDriver
from app.services.browser.models import BrowserSessionResult, BrowserState
from app.services.browser.navigation_base import BrowserNavigation, BrowserNavigationError
from app.services.browser.navigation_models import BrowserNavigationResult, NavigationState
from app.services.browser.page_base import BrowserPage, BrowserPageError
from app.services.browser.page_models import BrowserPageResult, PageState
from app.services.browser.page_service import DefaultBrowserPage
from app.services.browser.playwright_actions import PlaywrightActions
from app.services.browser.playwright_driver import PlaywrightBrowserDriver
from app.services.browser.playwright_navigation import PlaywrightNavigation
from app.services.browser.service import DefaultBrowserSession

__all__ = [
    "ActionState",
    "BrowserActionError",
    "BrowserActionResult",
    "BrowserActions",
    "BrowserContext",
    "BrowserContextError",
    "BrowserContextResult",
    "BrowserDriver",
    "BrowserDriverError",
    "BrowserDriverResult",
    "BrowserNavigation",
    "BrowserNavigationError",
    "BrowserNavigationResult",
    "BrowserPage",
    "BrowserPageError",
    "BrowserPageResult",
    "BrowserSession",
    "BrowserSessionError",
    "BrowserSessionResult",
    "BrowserState",
    "ContextState",
    "DefaultBrowserActions",
    "DefaultBrowserContext",
    "DefaultBrowserDriver",
    "DefaultBrowserPage",
    "DefaultBrowserSession",
    "DriverState",
    "NavigationState",
    "PageState",
    "PlaywrightActions",
    "PlaywrightBrowserDriver",
    "PlaywrightNavigation",
]
