"""Browser Bridge Service module.

Translates ActionEngine ExecutionPlan steps into declarative BrowserCommand
objects for consumption by the React frontend without performing browser automation.
"""

from enum import Enum
import logging

from pydantic import BaseModel, Field


from app.services.action_engine import ActionStep, ExecutionPlan
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class BrowserCommandType(str, Enum):
    """Enumeration of supported browser command types."""

    NAVIGATE = "NAVIGATE"
    SELECT = "SELECT"
    INPUT = "INPUT"
    CLICK = "CLICK"
    WAIT_FOR_USER = "WAIT_FOR_USER"
    DISPLAY = "DISPLAY"
    CUSTOM = "CUSTOM"


class BrowserCommand(BaseModel):
    """Model representing a declarative command sent to the frontend.

    Attributes:
        command_id: Sequential 1-based index identifier.
        command_type: BrowserCommandType enumeration value.
        target: Target component or route string.
        payload: Key-value dictionary of string parameters and voice prompt.
        blocking: Flag indicating if frontend should pause for user action.
        description: Human-readable command summary description.
    """

    command_id: int = Field(..., ge=1, description="1-based command index.")
    command_type: BrowserCommandType = Field(
        ..., description="Type of browser command."
    )
    target: str = Field(..., description="Target route or UI element name.")
    payload: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value command payload dictionary.",
    )
    blocking: bool = Field(
        default=False,
        description="Flag indicating if command blocks workflow for user input.",
    )
    description: str = Field(
        ..., description="Human-readable command description."
    )


class BrowserBridge(BaseService):
    """Bridge service for translating ExecutionPlan steps into BrowserCommand objects.

    Decouples backend planning from frontend rendering and voice interactions.
    """

    def __init__(self) -> None:
        """Initialize the BrowserBridge service instance."""
        logger.info("BrowserBridge initialized")

    def _resolve_command_type(self, action: str) -> BrowserCommandType:
        """Map step action string to a BrowserCommandType enum value.

        Args:
            action: Action identifier string.

        Returns:
            BrowserCommandType: Matched command type.
        """
        act = action.strip().upper()

        if act == "NAVIGATE" or act.startswith("NAVIGATE"):
            return BrowserCommandType.NAVIGATE
        elif (
            act
            in (
                "SELECT",
                "SELECT_TEMPLE",
                "SELECT_PUJA",
                "SELECT_DATE",
                "SELECT_TIME",
                "CHOOSE_ASTROLOGER",
                "CHOOSE_SLOT",
            )
            or act.startswith("SELECT")
            or act.startswith("CHOOSE")
        ):
            return BrowserCommandType.SELECT
        elif (
            act in ("INPUT", "FILL_DETAILS")
            or act.startswith("FILL")
            or act.startswith("INPUT")
        ):
            return BrowserCommandType.INPUT
        elif act in ("CLICK",) or act.startswith("CLICK"):
            return BrowserCommandType.CLICK
        elif act in ("WAIT_FOR_USER", "WAIT_PAYMENT") or act.startswith("WAIT"):
            return BrowserCommandType.WAIT_FOR_USER
        elif (
            act in ("DISPLAY", "LOAD_PANCHANG", "LOAD_PANDITS")
            or act.startswith("LOAD")
            or act.startswith("DISPLAY")
        ):
            return BrowserCommandType.DISPLAY
        else:
            return BrowserCommandType.CUSTOM

    def _translate_step(
        self,
        step: ActionStep,
        command_id: int,
    ) -> BrowserCommand:
        """Translate a single ActionStep into a BrowserCommand model.

        Args:
            step: ActionStep object to translate.
            command_id: Sequential command index integer.

        Returns:
            BrowserCommand: Translated browser command model.
        """
        cmd_type = self._resolve_command_type(step.action)
        blocking = step.requires_user_input or (
            cmd_type == BrowserCommandType.WAIT_FOR_USER
        )

        payload: dict[str, str] = {"action": step.action}
        for k, v in step.parameters.items():
            payload[k] = str(v)

        if step.voice_prompt:
            payload["voice_prompt"] = step.voice_prompt

        description = (
            f"Execute {cmd_type.value} on '{step.target}' for action '{step.action}'."
        )

        command = BrowserCommand(
            command_id=command_id,
            command_type=cmd_type,
            target=step.target,
            payload=payload,
            blocking=blocking,
            description=description,
        )

        logger.info(
            "Command translated [command_id=%d, type=%s, target=%s]",
            command_id,
            cmd_type.value,
            step.target,
        )
        return command

    def build_browser_commands(
        self,
        execution_plan: ExecutionPlan,
    ) -> list[BrowserCommand]:
        """Translate an ExecutionPlan into a list of BrowserCommand objects.

        Args:
            execution_plan: Validated ExecutionPlan model containing steps.

        Returns:
            list[BrowserCommand]: Ordered list of BrowserCommand models.

        Raises:
            ValueError: If execution_plan is None or contains no steps.
        """
        if execution_plan is None:
            raise ValueError("ExecutionPlan cannot be None.")

        if not execution_plan.steps:
            raise ValueError("ExecutionPlan steps cannot be empty.")

        logger.info(
            "Browser command generation started [intent=%s, steps=%d]",
            execution_plan.intent,
            len(execution_plan.steps),
        )

        commands: list[BrowserCommand] = []
        for idx, step in enumerate(execution_plan.steps, start=1):
            command = self._translate_step(step, command_id=idx)
            commands.append(command)

        logger.info(
            "Browser commands generated [count=%d]",
            len(commands),
        )
        return commands

    def close(self) -> None:
        """Release any allocated BrowserBridge resources."""
        logger.info("BrowserBridge closed")
