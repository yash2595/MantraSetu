"""Action Execution Planning Engine module.

Converts a NavigationDecision and extracted context entities into a structured,
step-by-step ExecutionPlan using the workflow registry without browser automation.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.services.base import BaseService
from app.services.navigation_service import NavigationDecision
from app.workflows.registry import WORKFLOWS

logger = logging.getLogger(__name__)


class ActionStep(BaseModel):
    """Model representing a single step within an execution plan.

    Attributes:
        step_number: Sequential 1-based index of the step.
        action: Identifier string of the step action.
        target: Target UI component or entity identifier.
        parameters: Dictionary of string key-value parameters.
        requires_user_input: Boolean flag indicating if user input is needed.
        voice_prompt: Optional voice prompt string for user interaction.
    """

    step_number: int = Field(..., ge=1, description="1-based step index.")
    action: str = Field(..., description="Action identifier string.")
    target: str = Field(..., description="Target element or screen name.")
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value parameters for step execution.",
    )
    requires_user_input: bool = Field(
        default=False,
        description="Flag indicating if user input is required.",
    )
    voice_prompt: str | None = Field(
        default=None,
        description="Optional voice prompt string for user interaction.",
    )


class ExecutionPlan(BaseModel):
    """Model representing a sequence of steps to fulfill a user intent.

    Attributes:
        intent: The driving user intent string.
        target_page: Optional target destination page name.
        steps: Ordered list of ActionStep objects to execute.
        completed: Boolean indicating if all steps are complete.
        summary: Human-readable summary of the plan.
    """

    intent: str = Field(..., description="Driving user intent string.")
    target_page: str | None = Field(
        default=None,
        description="Optional target destination page name.",
    )
    steps: list[ActionStep] = Field(
        default_factory=list,
        description="Ordered list of ActionStep objects.",
    )
    completed: bool = Field(
        default=False,
        description="Boolean status indicating plan completion.",
    )
    summary: str = Field(..., description="Human-readable plan summary.")


class ActionEngine(BaseService):
    """Engine service for building intent execution plans.

    Translates NavigationDecision context into declarative ExecutionPlan steps
    by resolving intent workflows registered in app.workflows.registry.
    """

    def __init__(self) -> None:
        """Initialize the ActionEngine service instance."""
        logger.info("ActionEngine initialized")

    def _add_step(
        self,
        steps: list[ActionStep],
        action: str,
        target: str,
        parameters: dict[str, str] | None = None,
        requires_user_input: bool = False,
        voice_prompt: str | None = None,
    ) -> ActionStep:
        """Helper method to append an ActionStep with an automatically assigned step_number.

        Args:
            steps: Mutable list of existing ActionStep objects.
            action: Step action identifier.
            target: Target UI element or screen.
            parameters: Optional dictionary of string parameters.
            requires_user_input: Boolean flag for user input requirement.
            voice_prompt: Optional voice prompt message string.

        Returns:
            ActionStep: Newly created and appended ActionStep model.
        """
        step_number = len(steps) + 1
        step = ActionStep(
            step_number=step_number,
            action=action,
            target=target,
            parameters=parameters or {},
            requires_user_input=requires_user_input,
            voice_prompt=voice_prompt,
        )
        steps.append(step)
        return step

    def build_execution_plan(
        self,
        decision: NavigationDecision,
        entities: dict[str, str] | None = None,
    ) -> ExecutionPlan:
        """Build a structured ExecutionPlan from a NavigationDecision and entities.

        Args:
            decision: Validated NavigationDecision object.
            entities: Optional dictionary of extracted string entities.

        Returns:
            ExecutionPlan: Generated step-by-step execution plan.

        Raises:
            ValueError: If decision is None.
        """
        if decision is None:
            raise ValueError("NavigationDecision cannot be None.")

        intent = decision.intent.strip().upper()
        target_page = decision.target_page
        extracted_entities = entities or {}

        logger.info(
            "Execution planning started [intent=%s, target_page=%s]",
            intent,
            target_page,
        )

        workflow = WORKFLOWS.get(intent)
        if workflow is None:
            logger.info("Unknown intent [intent=%s]", intent)
            summary = f"Unknown intent '{intent}'. Empty execution plan generated."
            plan = ExecutionPlan(
                intent=intent,
                target_page=target_page,
                steps=[],
                completed=False,
                summary=summary,
            )
            logger.info("Execution plan generated [steps=0]")
            return plan

        steps: list[ActionStep] = []

        if decision.requires_navigation and target_page:
            self._add_step(
                steps=steps,
                action="NAVIGATE",
                target=target_page,
                parameters={"destination": target_page},
                requires_user_input=False,
            )

        for item in workflow:
            param_name = item.get("parameter")
            default_val = item.get("default", "")
            step_parameters: dict[str, str] = {}

            if param_name:
                step_parameters[param_name] = extracted_entities.get(
                    param_name, default_val
                )

            self._add_step(
                steps=steps,
                action=item.get("action", ""),
                target=item.get("target", ""),
                parameters=step_parameters,
                requires_user_input=bool(item.get("requires_user_input", False)),
                voice_prompt=item.get("voice_prompt"),
            )

        summary = (
            f"Execution plan with {len(steps)} steps generated for intent '{intent}'."
        )
        plan = ExecutionPlan(
            intent=intent,
            target_page=target_page,
            steps=steps,
            completed=False,
            summary=summary,
        )

        logger.info("Execution plan generated [steps=%d]", len(steps))
        return plan

    def close(self) -> None:
        """Release any allocated ActionEngine resources."""
        logger.info("ActionEngine closed")
