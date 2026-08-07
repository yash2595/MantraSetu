"""Branching, Checkpointed, and Resumable Workflow Graph Engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowTransitionStatus(StrEnum):
    """Enumeration of workflow transition outcomes."""

    NEXT_STEP = "NEXT_STEP"
    COMPLETED = "COMPLETED"
    ROLLED_BACK = "ROLLED_BACK"
    RESTARTED = "RESTARTED"
    RESUMED = "RESUMED"
    INTERRUPTED = "INTERRUPTED"
    RECOVERED = "RECOVERED"
    BLOCKED = "BLOCKED"


@dataclass
class WorkflowNode:
    """Node in a multi-step user journey workflow graph."""

    step_id: str
    name: str
    route_path: str
    required_inputs: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    conditional_branches: dict[str, str] = field(default_factory=dict)
    can_skip: bool = False
    is_mandatory: bool = True
    rollback_target: str | None = None


@dataclass(frozen=True)
class WorkflowEdge:
    """Directed transition edge connecting two workflow nodes."""

    source_step_id: str
    target_step_id: str
    branch_key: str | None = None
    condition_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowGraph:
    """Graph structure representing an application workflow."""

    workflow_name: str
    category: str
    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    edges: list[WorkflowEdge] = field(default_factory=list)
    initial_step_id: str = ""
    checkpoint_steps: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class WorkflowResult:
    """Evaluation or transition result from WorkflowGraphEngine."""

    status: WorkflowTransitionStatus
    current_step_id: str
    target_step_id: str | None = None
    current_node: WorkflowNode | None = None
    target_node: WorkflowNode | None = None
    checkpoints: list[str] = field(default_factory=list)
    context_data: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


class WorkflowGraphEngine:
    """Engine managing branching, rollback, checkpoints, resume, and interruption recovery."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._workflows: dict[str, dict[str, WorkflowNode]] = {}
        self._graph_objects: dict[str, WorkflowGraph] = {}
        self._register_default_workflows()

    def _register_default_workflows(self) -> None:
        puja_nodes = {
            "SELECT_PUJA": WorkflowNode(
                step_id="SELECT_PUJA",
                name="Select Puja Ritual",
                route_path="/puja",
                next_steps=["VIEW_DETAIL"],
                is_mandatory=True,
            ),
            "VIEW_DETAIL": WorkflowNode(
                step_id="VIEW_DETAIL",
                name="Review Puja Details",
                route_path="/puja/[id]",
                required_inputs=["id"],
                next_steps=["SELECT_DATE"],
                is_mandatory=True,
                rollback_target="SELECT_PUJA",
            ),
            "SELECT_DATE": WorkflowNode(
                step_id="SELECT_DATE",
                name="Select Booking Date & Package",
                route_path="/booking",
                required_inputs=["date"],
                next_steps=["SELECT_PANDIT", "PAYMENT"],
                can_skip=True,
                is_mandatory=False,
                rollback_target="VIEW_DETAIL",
            ),
            "SELECT_PANDIT": WorkflowNode(
                step_id="SELECT_PANDIT",
                name="Select Preferred Pandit",
                route_path="/pandit",
                next_steps=["PAYMENT"],
                can_skip=True,
                is_mandatory=False,
                rollback_target="SELECT_DATE",
            ),
            "PAYMENT": WorkflowNode(
                step_id="PAYMENT",
                name="Checkout Payment Gateway",
                route_path="/payment",
                required_inputs=["booking_id"],
                next_steps=["CONFIRMATION"],
                is_mandatory=True,
                rollback_target="SELECT_DATE",
            ),
            "CONFIRMATION": WorkflowNode(
                step_id="CONFIRMATION",
                name="Booking Confirmation Receipt",
                route_path="/confirmation",
                required_inputs=["order_id"],
                next_steps=[],
                is_mandatory=True,
            ),
        }

        puja_edges = [
            WorkflowEdge("SELECT_PUJA", "VIEW_DETAIL"),
            WorkflowEdge("VIEW_DETAIL", "SELECT_DATE"),
            WorkflowEdge("SELECT_DATE", "SELECT_PANDIT", branch_key="custom_pandit"),
            WorkflowEdge("SELECT_DATE", "PAYMENT", branch_key="default_pandit"),
            WorkflowEdge("SELECT_PANDIT", "PAYMENT"),
            WorkflowEdge("PAYMENT", "CONFIRMATION"),
        ]

        puja_graph = WorkflowGraph(
            workflow_name="PUJA_BOOKING",
            category="PUJA_BOOKING",
            nodes=puja_nodes,
            edges=puja_edges,
            initial_step_id="SELECT_PUJA",
            checkpoint_steps=("SELECT_PUJA", "SELECT_DATE", "PAYMENT"),
        )

        self.register_graph(puja_graph)

    def register_graph(self, graph: WorkflowGraph) -> None:
        """Register a custom WorkflowGraph in the engine."""
        with self._lock:
            self._graph_objects[graph.workflow_name] = graph
            self._workflows[graph.workflow_name] = graph.nodes
            logger.info("Registered workflow graph '%s' with %d nodes", graph.workflow_name, len(graph.nodes))

    def get_workflow_graph(self, workflow_name: str) -> WorkflowGraph | None:
        """Return registered WorkflowGraph object."""
        with self._lock:
            return self._graph_objects.get(workflow_name)

    def get_next_step(
        self,
        workflow_name: str,
        current_step_id: str,
        branch_key: str | None = None,
    ) -> WorkflowNode | None:
        """Find next workflow node given current step and optional branch decision key."""
        with self._lock:
            nodes = self._workflows.get(workflow_name)
            if not nodes or current_step_id not in nodes:
                return None

            curr_node = nodes[current_step_id]
            if branch_key and branch_key in curr_node.conditional_branches:
                target_id = curr_node.conditional_branches[branch_key]
                return nodes.get(target_id)

            if curr_node.next_steps:
                return nodes.get(curr_node.next_steps[0])

            return None

    def rollback(
        self,
        workflow_name: str,
        current_step_id: str,
        history: list[str] | None = None,
    ) -> WorkflowResult:
        """Rollback to previous step or node's explicit rollback target."""
        with self._lock:
            nodes = self._workflows.get(workflow_name)
            if not nodes or current_step_id not in nodes:
                return WorkflowResult(
                    status=WorkflowTransitionStatus.BLOCKED,
                    current_step_id=current_step_id,
                    reason=f"Workflow '{workflow_name}' or step '{current_step_id}' not found.",
                )

            curr_node = nodes[current_step_id]
            target_id = curr_node.rollback_target

            if not target_id and history:
                # Find most recent valid step in history
                for prev in reversed(history):
                    if prev in nodes and prev != current_step_id:
                        target_id = prev
                        break

            if not target_id:
                graph = self._graph_objects.get(workflow_name)
                target_id = graph.initial_step_id if graph else current_step_id

            target_node = nodes.get(target_id)
            return WorkflowResult(
                status=WorkflowTransitionStatus.ROLLED_BACK,
                current_step_id=current_step_id,
                target_step_id=target_id,
                current_node=curr_node,
                target_node=target_node,
                reason=f"Rolled back workflow '{workflow_name}' from '{current_step_id}' to '{target_id}'.",
            )

    def restart(self, workflow_name: str) -> WorkflowResult:
        """Restart workflow from its initial entry node."""
        with self._lock:
            graph = self._graph_objects.get(workflow_name)
            if not graph:
                return WorkflowResult(
                    status=WorkflowTransitionStatus.BLOCKED,
                    current_step_id="",
                    reason=f"Workflow '{workflow_name}' not found.",
                )
            initial_id = graph.initial_step_id
            init_node = graph.nodes.get(initial_id)
            return WorkflowResult(
                status=WorkflowTransitionStatus.RESTARTED,
                current_step_id=initial_id,
                target_step_id=initial_id,
                current_node=init_node,
                target_node=init_node,
                checkpoints=[initial_id] if initial_id in graph.checkpoint_steps else [],
                reason=f"Restarted workflow '{workflow_name}' to initial step '{initial_id}'.",
            )

    def checkpoint(
        self,
        workflow_name: str,
        current_step_id: str,
        existing_checkpoints: list[str] | None = None,
    ) -> WorkflowResult:
        """Add checkpoint at current step if permitted."""
        with self._lock:
            graph = self._graph_objects.get(workflow_name)
            checkpoints = list(existing_checkpoints or [])
            if graph and current_step_id in graph.nodes:
                if current_step_id not in checkpoints:
                    checkpoints.append(current_step_id)
                return WorkflowResult(
                    status=WorkflowTransitionStatus.NEXT_STEP,
                    current_step_id=current_step_id,
                    target_step_id=current_step_id,
                    current_node=graph.nodes.get(current_step_id),
                    checkpoints=checkpoints,
                    reason=f"Saved checkpoint for step '{current_step_id}' in workflow '{workflow_name}'.",
                )
            return WorkflowResult(
                status=WorkflowTransitionStatus.BLOCKED,
                current_step_id=current_step_id,
                reason=f"Invalid checkpoint step '{current_step_id}'.",
            )

    def resume(
        self,
        workflow_name: str,
        checkpoint_step_id: str,
    ) -> WorkflowResult:
        """Resume workflow from a saved checkpoint."""
        with self._lock:
            graph = self._graph_objects.get(workflow_name)
            if not graph or checkpoint_step_id not in graph.nodes:
                return WorkflowResult(
                    status=WorkflowTransitionStatus.BLOCKED,
                    current_step_id=checkpoint_step_id,
                    reason=f"Cannot resume: step '{checkpoint_step_id}' not found in workflow '{workflow_name}'.",
                )

            node = graph.nodes[checkpoint_step_id]
            return WorkflowResult(
                status=WorkflowTransitionStatus.RESUMED,
                current_step_id=checkpoint_step_id,
                target_step_id=checkpoint_step_id,
                current_node=node,
                target_node=node,
                reason=f"Resumed workflow '{workflow_name}' at checkpoint step '{checkpoint_step_id}'.",
            )

    def recover_interruption(
        self,
        workflow_name: str,
        current_route: str,
        history: list[str],
    ) -> WorkflowResult:
        """Recover from unexpected detour or interruption back to current active workflow step."""
        with self._lock:
            graph = self._graph_objects.get(workflow_name)
            if not graph:
                return WorkflowResult(
                    status=WorkflowTransitionStatus.BLOCKED,
                    current_step_id="",
                    reason=f"Workflow '{workflow_name}' not found.",
                )

            # Search in reverse history order starting from current_route
            candidates = list(history) + [current_route]
            for route_or_step in reversed(candidates):
                for step_id, node in graph.nodes.items():
                    if node.route_path == route_or_step or step_id == route_or_step:
                        return WorkflowResult(
                            status=WorkflowTransitionStatus.RECOVERED,
                            current_step_id=step_id,
                            target_step_id=step_id,
                            current_node=node,
                            target_node=node,
                            reason=f"Recovered workflow '{workflow_name}' at step '{step_id}' from route '{current_route}'.",
                        )

            # Default to initial step
            init_id = graph.initial_step_id
            init_node = graph.nodes.get(init_id)
            return WorkflowResult(
                status=WorkflowTransitionStatus.RECOVERED,
                current_step_id=init_id,
                target_step_id=init_id,
                current_node=init_node,
                target_node=init_node,
                reason=f"Recovered workflow '{workflow_name}' to initial step '{init_id}'.",
            )
