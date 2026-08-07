"""Domain models for Task Context Builder."""

from datetime import datetime

from pydantic import Field

from app.schemas.base import SchemaModel
from app.services.browser_intelligence.dom_intelligence_models import DOMIntelligence
from app.services.browser_intelligence.navigation_graph_models import NavigationGraph
from app.services.browser_intelligence.page_context_models import PageContext


class TaskSummary(SchemaModel):
    """Lightweight projection of frequently accessed planner information."""
    page_url: str = Field(..., description="Current page URL.")
    page_title: str = Field(..., description="Current page title.")
    primary_action_count: int = Field(..., description="Number of primary actions.")
    secondary_action_count: int = Field(..., description="Number of secondary actions.")
    navigation_link_count: int = Field(..., description="Number of navigation links.")
    input_field_count: int = Field(..., description="Number of input fields.")
    has_navigation: bool = Field(..., description="Whether the page has navigation links.")
    has_form: bool = Field(..., description="Whether the page has forms.")
    has_primary_action: bool = Field(..., description="Whether the page has primary actions.")
    has_input: bool = Field(..., description="Whether the page has inputs.")


class TaskContext(SchemaModel):
    """Unified context aggregating browser state intelligence."""
    summary: TaskSummary = Field(..., description="High-level task summary projection.")
    page_context: PageContext = Field(..., description="Raw page context data.")
    dom_intelligence: DOMIntelligence = Field(..., description="Semantic DOM intelligence data.")
    navigation_graph: NavigationGraph = Field(..., description="Navigation graph state.")
    created_at: datetime = Field(..., description="Timestamp of task context creation.")
