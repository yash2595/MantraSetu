"""Domain models and schemas for the Navigation Intelligence subsystem in MantraSetu AgentOS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Any, Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return the current timestamp in UTC."""
    return datetime.now(timezone.utc)


class BaseNavigationModel(BaseModel):
    """Base Pydantic v2 model for immutable Navigation domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


# Centralized String Enums for Type Safety
class NavigationNodeType(str, Enum):
    """Enumeration of website map node types."""

    PAGE = "page"
    ACTION = "action"
    FORM = "form"
    EXTERNAL = "external"


class NavigationStatus(str, Enum):
    """Enumeration of navigation plan and action execution statuses."""

    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionType(str, Enum):
    """Enumeration of web browser navigation action types."""

    CLICK = "click"
    INPUT = "input"
    SELECT = "select"
    NAVIGATE = "navigate"


class PageType(StrEnum):
    """Enumeration of page topology types."""

    PORTAL = "PORTAL"
    CATALOG = "CATALOG"
    DETAIL = "DETAIL"
    WORKFLOW_STEP = "WORKFLOW_STEP"
    CALCULATOR = "CALCULATOR"
    CHECKOUT = "CHECKOUT"
    RECEIPT = "RECEIPT"
    AUTHENTICATION = "AUTHENTICATION"
    DASHBOARD = "DASHBOARD"
    PAGE = "PAGE"


class ComponentType(StrEnum):
    """Enumeration of UI component types."""

    BUTTON = "BUTTON"
    INPUT = "INPUT"
    DROPDOWN = "DROPDOWN"
    CHECKBOX = "CHECKBOX"
    RADIO_BUTTON = "RADIO_BUTTON"
    CALENDAR = "CALENDAR"
    CARD = "CARD"
    TABLE = "TABLE"
    TAB = "TAB"
    DIALOG = "DIALOG"
    ACCORDION = "ACCORDION"
    FILTER = "FILTER"
    SEARCH_BOX = "SEARCH_BOX"
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    FORM = "FORM"
    MODAL = "MODAL"
    MENU = "MENU"


class NavigationActionEnum(StrEnum):
    """Enumeration of navigation directives."""

    NAVIGATE = "NAVIGATE"
    BACK = "BACK"
    FORWARD = "FORWARD"
    CLICK = "CLICK"
    INPUT = "INPUT"
    SELECT = "SELECT"
    SUBMIT = "SUBMIT"
    SCROLL = "SCROLL"
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    OPEN_MODAL = "OPEN_MODAL"
    CLOSE_MODAL = "CLOSE_MODAL"
    WAIT = "WAIT"


class WorkflowCategory(StrEnum):
    """Enumeration of application workflow categories."""

    PUJA_BOOKING = "PUJA_BOOKING"
    KUNDALI_ANALYSIS = "KUNDALI_ANALYSIS"
    MUHURAT_SEARCH = "MUHURAT_SEARCH"
    AUTHENTICATION = "AUTHENTICATION"
    USER_PROFILE = "USER_PROFILE"


class AuthState(StrEnum):
    """Enumeration of user authentication states."""

    ANONYMOUS = "ANONYMOUS"
    AUTHENTICATED = "AUTHENTICATED"


class PermissionType(StrEnum):
    """Enumeration of system permissions."""

    PROCESS_PAYMENT = "PROCESS_PAYMENT"
    VIEW_USER_ORDERS = "VIEW_USER_ORDERS"
    CANCEL_ORDER = "CANCEL_ORDER"
    MANAGE_PROFILE = "MANAGE_PROFILE"


class ValidationSeverity(StrEnum):
    """Enumeration of validation severities."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RouteStatus(StrEnum):
    """Enumeration of route operational statuses."""

    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    MAINTENANCE = "MAINTENANCE"
    DISABLED = "DISABLED"


class ComponentState(StrEnum):
    """Enumeration of UI component states."""

    VISIBLE = "VISIBLE"
    HIDDEN = "HIDDEN"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    FOCUSED = "FOCUSED"


class NavigationStateEnum(StrEnum):
    """Enumeration of session navigation state status."""

    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    PENDING_ACTION = "PENDING_ACTION"
    IN_WORKFLOW = "IN_WORKFLOW"
    ERROR = "ERROR"


# Strongly Typed Immutable Value Models
@dataclass(frozen=True)
class ValidationMetadata:
    """Immutable parameter validation requirement model."""

    field_name: str
    rule_type: str
    is_required: bool = True
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    error_message: str = ""


@dataclass(frozen=True)
class PermissionMetadata:
    """Immutable permission requirements model."""

    permission_type: PermissionType
    required_role: str = "USER"
    is_mandatory: bool = True


@dataclass(frozen=True)
class CapabilityMetadata:
    """Immutable capability specification model."""

    capability_name: str
    description: str = ""
    is_enabled: bool = True


@dataclass(frozen=True)
class WorkflowMetadata:
    """Immutable workflow step definition model."""

    workflow_name: WorkflowCategory
    step_name: str
    step_index: int = 0
    total_steps: int = 1
    is_mandatory: bool = True


@dataclass(frozen=True)
class RouteMetadata:
    """Immutable strongly typed route metadata value object."""

    page_type: PageType
    semantic_label: str
    description: str = ""
    parent: str | None = None
    children: tuple[str, ...] = field(default_factory=tuple)
    breadcrumbs: tuple[str, ...] = field(default_factory=tuple)
    workflow: WorkflowCategory | None = None
    workflow_step: str | None = None
    parameters: tuple[str, ...] = field(default_factory=tuple)
    validation_rules: dict[str, Any] = field(default_factory=dict)
    requires_auth: bool = False
    permissions: tuple[PermissionType, ...] = field(default_factory=tuple)
    feature_flags: tuple[str, ...] = field(default_factory=tuple)
    allowed_transitions: tuple[str, ...] = field(default_factory=tuple)
    previous_routes: tuple[str, ...] = field(default_factory=tuple)
    next_routes: tuple[str, ...] = field(default_factory=tuple)
    shortcut_routes: tuple[str, ...] = field(default_factory=tuple)
    recovery_routes: tuple[str, ...] = field(default_factory=tuple)
    page_capabilities: tuple[str, ...] = field(default_factory=tuple)
    supported_ai_actions: tuple[NavigationActionEnum, ...] = field(default_factory=tuple)
    visible_regions: tuple[str, ...] = field(default_factory=tuple)
    primary_actions: tuple[str, ...] = field(default_factory=tuple)
    secondary_actions: tuple[str, ...] = field(default_factory=tuple)
    forms: tuple[str, ...] = field(default_factory=tuple)
    buttons: tuple[str, ...] = field(default_factory=tuple)
    dropdowns: tuple[str, ...] = field(default_factory=tuple)
    filters: tuple[str, ...] = field(default_factory=tuple)
    cards: tuple[str, ...] = field(default_factory=tuple)
    tables: tuple[str, ...] = field(default_factory=tuple)
    dialogs: tuple[str, ...] = field(default_factory=tuple)
    tabs: tuple[str, ...] = field(default_factory=tuple)
    accordions: tuple[str, ...] = field(default_factory=tuple)
    search_boxes: tuple[str, ...] = field(default_factory=tuple)
    uploads: tuple[str, ...] = field(default_factory=tuple)
    downloads: tuple[str, ...] = field(default_factory=tuple)
    metadata_version: str = "4.1"
    updated_at: str = "2026-07-31T22:50:00Z"


# Pydantic Domain Entities (Existing Frozen Contracts Preserved)
class WebsiteNode(BaseNavigationModel):
    """Domain model representing a node (page/form) in a website structure map."""

    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique website node identifier UUID.",
    )
    url: str = Field(
        ...,
        description="Page or target URL string.",
    )
    name: str = Field(
        ...,
        description="Human-readable name or label string.",
    )
    node_type: NavigationNodeType = Field(
        default=NavigationNodeType.PAGE,
        description="NavigationNodeType enum value.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class NavigationEdge(BaseNavigationModel):
    """Domain model representing a transition edge connecting two WebsiteNode entities."""

    edge_id: UUID = Field(
        default_factory=uuid4,
        description="Unique edge transition identifier UUID.",
    )
    source_node_id: UUID = Field(
        ...,
        description="Origin WebsiteNode identifier UUID.",
    )
    target_node_id: UUID = Field(
        ...,
        description="Destination WebsiteNode identifier UUID.",
    )
    action_type: ActionType = Field(
        ...,
        description="ActionType enum causing the transition.",
    )
    action_data: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable transition parameters or selector mapping.",
    )


class NavigationPlan(BaseNavigationModel):
    """Domain model representing a multi-step goal navigation plan."""

    plan_id: UUID = Field(
        default_factory=uuid4,
        description="Unique navigation plan identifier UUID.",
    )
    goal: str = Field(
        ...,
        description="Target goal description string.",
    )
    steps: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of step description strings.",
    )
    status: NavigationStatus = Field(
        default=NavigationStatus.PLANNED,
        description="NavigationStatus enum indicating plan state.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )


class NavigationAction(BaseNavigationModel):
    """Domain model representing an individual browser navigation command action."""

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique action identifier UUID.",
    )
    action_type: ActionType = Field(
        ...,
        description="ActionType enum value.",
    )
    target: str = Field(
        ...,
        description="Target CSS selector, element text, or URL string.",
    )
    parameters: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable parameters mapping.",
    )
    status: NavigationStatus = Field(
        default=NavigationStatus.PLANNED,
        description="NavigationStatus enum value.",
    )


class NavigationContext(BaseNavigationModel):
    """Domain model capturing active navigation session context and page history."""

    session_id: UUID | None = Field(
        default=None,
        description="Optional associated user session identifier UUID.",
    )
    current_url: str | None = Field(
        default=None,
        description="Optional active browser page URL string.",
    )
    current_node: WebsiteNode | None = Field(
        default=None,
        description="Optional active WebsiteNode entity.",
    )
    history: tuple[WebsiteNode, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of visited WebsiteNode entities.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
