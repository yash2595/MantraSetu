import sys

with open('app/orchestrator/ai_orchestrator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'Check if we are currently in an active onboarding session' in line:
        insert_idx = i - 1
        break

block = '''
        # -- NAVIGATION ABANDON CONFIRMATION STEP --
        pending_nav_target = getattr(session, "pending_nav_target", None)
        if pending_nav_target:
            yes_triggers = ["haan", "yes", "kar do", "kardo", "chalo", "thik hai", "theek hai", "???", "???", "?? ??", "???"]
            no_triggers = ["nahi", "na", "no", "ruko", "cancel", "mat jao", "?????", "????", "??"]
            
            if any(t in msg_lower or t in norm_msg for t in yes_triggers):
                session.pending_nav_target = None
                session.onboarding_state = {}
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                nav_directive = {"action": "NAVIGATE", "target": pending_nav_target, "intent": "NAVIGATE"}
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Theek hai, chaliye naye page par chalte hain.",
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            elif any(t in msg_lower or t in norm_msg for t in no_triggers):
                session.pending_nav_target = None
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Theek hai, wahi se continue karte hain.",
                    response_type=ResponseType.CHAT,
                    navigation_directive={"action": None, "target": None, "query": None, "active_field": getattr(session, "current_field", None), "intent": "CANCEL_NAVIGATE"},
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            else:
                session.pending_nav_target = None
                import logging
                logging.getLogger(__name__).info("[NAVIGATION] Safety net: Cleared pending_nav_target because user said something unrelated.")

        # -- NAVIGATION INTENT DETECTION --
        if is_navigation_command(sanitized_req.user_message) and not getattr(session, "pending_pandit_clarification", False) and not getattr(session, "pending_tour_clarification", False):
            nav_result = resolve_navigation_target(sanitized_req.user_message)
            if nav_result["needs_clarification"]:
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=nav_result["clarification_msg"],
                    response_type=ResponseType.CHAT,
                    navigation_directive={"action": None, "target": None, "query": None, "active_field": None, "intent": "CLARIFY_NAVIGATION"},
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            elif nav_result["target"]:
                target_route = nav_result["target"]
                onboarding_state = getattr(session, "onboarding_state", None)
                
                if onboarding_state and onboarding_state.get("active"):
                    session.pending_nav_target = target_route
                    elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                    return self._response_builder.build_response(
                        request_id=request.request_id,
                        text_override="Aapka form abhi poora nahi hua hai. Kya aap isko chhod kar naye page par jana chahte hain?",
                        response_type=ResponseType.CHAT,
                        navigation_directive={"action": None, "target": None, "query": None, "active_field": None, "intent": "NAVIGATE_CONFIRMATION"},
                        metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                    )
                else:
                    session.onboarding_state = {}
                    elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                    nav_directive = {"action": "NAVIGATE", "target": target_route, "intent": "NAVIGATE"}
                    self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                    return self._response_builder.build_response(
                        request_id=request.request_id,
                        text_override="Theek hai, main aapko le ja raha hoon.",
                        response_type=ResponseType.NAVIGATION_DIRECTIVE,
                        navigation_directive=nav_directive,
                        metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                    )
'''

lines.insert(insert_idx, block)

# And add the import at the top
import_block = 'from app.orchestrator.navigation_intent_detector import is_navigation_command, resolve_navigation_target\\n'
for i, line in enumerate(lines):
    if 'import' in line:
        lines.insert(i, import_block)
        break

with open('app/orchestrator/ai_orchestrator.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
