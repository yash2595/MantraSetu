# ADR-001: AIOrchestrator Architecture Specification

- **Status**: Approved / Freeze Candidate (v3.4)
- **Date**: 2026-07-31
- **Deciders**: Principal AI Backend Engineer & AI Systems Architecture Team

---

## Context & Problem Statement

MantraSetu Saarthi is evolving into a **Voice-First AI Digital Pandit** platform where interactions occur primarily through natural language speech. The legacy orchestration layer relied on `ChatOrchestrator`, coupling requests to conversational text chat concepts and embedding prompt selection logic directly inside the orchestrator.

To ensure enterprise-grade stability, long-term maintainability, and transport independence, the orchestration layer must be decoupled from entry-point transport mediums (Voice STT outputs, Chat endpoints, Mobile APIs) and established as a pure, stateless AI brain.

---

## Decision Drivers

1. **Modality & Transport Independence**: `AIOrchestrator` must operate exclusively on normalized, transport-agnostic requests (`InteractionRequest`) without knowledge of originating transport details.
2. **Pure Orchestration (Air Traffic Controller)**: The orchestrator contains zero business rules, zero booking logic, zero navigation heuristics, zero regex, and zero prompt-building routines.
3. **Stateless & Re-entrant Execution**: All state belongs to dedicated managers (`SessionManager`, `ContextManager`, `NavigationStore`). `AIOrchestrator` stores no turn state.
4. **Plugin Stage Architecture**: Stage flow is managed via a pluggable `PipelineExecutor` iterating over registered `PipelineStage` objects (`SessionStage`, `ContextStage`, `IntentStage`, `PlannerStage`, `ExecutionStage`, `ResponseFormattingStage`).
5. **Strict Field Ownership**: Every stage owns exactly one field inside `ExecutionContext` (`session_data`, `context`, `intent_result`, `plan`, `execution_result`, `response`), reading only required data and modifying only its owned field.
6. **Null Object Pattern & Zero `hasattr()`**: Optional collaborators use Null Objects (`NoopSessionManager`, `NoopIntentEngine`, `NoopPlanner`) configured during dependency construction, eliminating runtime `hasattr()` checks.
7. **100% Backward Compatibility**: Existing API routes (`POST /chat`) and `ChatOrchestrator` remain functional via a thin adapter mapping `ChatRequest` -> `InteractionRequest` -> `AIOrchestrator` -> `InteractionResponse` -> `AIResponse`.

---

## Alternatives Considered & Rejected

- **Alternative A: Extending `ChatOrchestrator` with Voice Branches**: Rejected because it violates SRP, OCP, and couples the core AI brain to chat-specific models.
- **Alternative B: Introducing Heavy Frameworks (CQRS, Actors, Event Sourcing)**: Rejected as overengineering for Module 1. Clean Architecture and SOLID principles satisfy all requirements without extra complexity.

---

## Consequences & Trade-offs

- **Positive**:
  - Plugin stage pipeline permits adding new stages (e.g. `SafetyStage`, `AuditStage`) without modifying `AIOrchestrator` or `PipelineExecutor`.
  - Zero runtime reflection or `hasattr()` checks ensures high execution performance and deterministic behavior.
  - Complete mockability for unit testing without network, DB, LLM, or browser dependencies.
- **Trade-off**:
  - Requires maintaining the `ChatOrchestrator` adapter layer until legacy text-chat endpoints are formally deprecated.
