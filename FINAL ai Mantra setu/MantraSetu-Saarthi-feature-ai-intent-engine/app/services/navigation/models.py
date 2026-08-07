"""Domain models for the Navigation Service.

These Pydantic v2 models define the data contract for navigation planning.
They are intentionally free of any browser, DOM, or automation logic so the
Navigation Service can evolve — connecting Playwright, BrowserService, vision
models, or multi-step recovery — without changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Navigation action enumeration
# ---------------------------------------------------------------------------


class NavigationAction(str, Enum):
    """Describes a single browser or UI interaction to be performed.

    Values:
        UNKNOWN:       Action is not known or has not been determined yet.
        GO_TO_PAGE:    Navigate directly to a named page or URL.
        OPEN_SECTION:  Open or expand a named section on the current page.
        SEARCH:        Perform a search query on the current page or globally.
        CLICK_ELEMENT: Click a named UI element (button, link, tab, etc.).
        FILL_FORM:     Enter data into a named form field.
        SUBMIT_FORM:   Submit a form on the current page.
        GO_BACK:       Navigate to the previous page in browser history.
        GO_FORWARD:    Navigate to the next page in browser history.
        REFRESH:       Reload the current page.
    """

    UNKNOWN = "unknown"
    GO_TO_PAGE = "go_to_page"
    OPEN_SECTION = "open_section"
    SEARCH = "search"
    CLICK_ELEMENT = "click_element"
    FILL_FORM = "fill_form"
    SUBMIT_FORM = "submit_form"
    GO_BACK = "go_back"
    GO_FORWARD = "go_forward"
    REFRESH = "refresh"


# ---------------------------------------------------------------------------
# Navigation status enumeration
# ---------------------------------------------------------------------------


class NavigationStatus(str, Enum):
    """Lifecycle status of a navigation plan or operation.

    Values:
        NOT_REQUIRED: Navigation is not needed for this request.
        PLANNED:      A navigation plan has been created but not yet executed.
        FAILED:       Navigation execution was attempted and failed.
        COMPLETED:    Navigation execution completed successfully.
    """

    NOT_REQUIRED = "not_required"
    PLANNED = "planned"
    FAILED = "failed"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# Navigation target model
# ---------------------------------------------------------------------------


class NavigationTarget(SchemaModel):
    """Describes the destination or subject of a navigation action.

    Attributes:
        page:     Name or identifier of the target page (e.g. ``"panchang"``).
        section:  Name of the target section within a page.
        element:  Name or selector hint for the target UI element.
        url:      Explicit URL override for ``GO_TO_PAGE`` actions.
        metadata: Optional free-form context forwarded to the browser agent.
    """

    page: Optional[str] = Field(
        default=None,
        description="Name or identifier of the target page.",
    )
    section: Optional[str] = Field(
        default=None,
        description="Name of the target section within a page.",
    )
    element: Optional[str] = Field(
        default=None,
        description="Name or selector hint for the target UI element.",
    )
    url: Optional[str] = Field(
        default=None,
        description="Explicit URL for GO_TO_PAGE actions.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to the browser agent.",
    )


# ---------------------------------------------------------------------------
# Navigation step model
# ---------------------------------------------------------------------------


class NavigationStep(SchemaModel):
    """A single ordered step within a NavigationResult.

    Steps are declarative — they describe *what* the browser agent should do,
    not *how* to implement it. The actual execution happens in the browser
    agent layer.

    Attributes:
        order:       1-based execution order within the parent plan.
        action:      ``NavigationAction`` to perform.
        target:      ``NavigationTarget`` describing the destination/subject.
        description: Human-readable description of this step for logging and
                     debugging.
    """

    order: int = Field(
        default=1,
        ge=1,
        description="1-based execution order within the parent plan.",
    )
    action: NavigationAction = Field(
        ...,
        description="Navigation action to perform.",
    )
    target: NavigationTarget = Field(
        default_factory=NavigationTarget,
        description="Destination or subject of this navigation action.",
    )
    description: str = Field(
        default="",
        description="Human-readable step description.",
    )


# ---------------------------------------------------------------------------
# Navigation result model
# ---------------------------------------------------------------------------


class NavigationResult(SchemaModel):
    """Immutable navigation plan produced by the Navigation Service.

    The service always returns one of these — it never returns ``None``.
    When navigation is not needed, ``required`` is ``False`` and ``steps``
    is empty.

    Attributes:
        required:   ``True`` when browser navigation is needed for this request.
        status:     Current lifecycle status of this navigation plan.
        steps:      Ordered list of ``NavigationStep`` instances to execute.
        confidence: Planning confidence in [0.0, 1.0].
        metadata:   Optional free-form context forwarded to callers.
    """

    required: bool = Field(
        ...,
        description="True when browser navigation is needed.",
    )
    status: NavigationStatus = Field(
        default=NavigationStatus.NOT_REQUIRED,
        description="Lifecycle status of this navigation plan.",
    )
    steps: list[NavigationStep] = Field(
        default_factory=list,
        description="Ordered navigation steps to execute.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Planning confidence in [0.0, 1.0].",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
