"""Verify all voice commands through the AIOrchestrator pipeline."""
import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.orchestrator_models import OrchestratorRequest, ConversationMode

TEST_COMMANDS = [
    "Book Puja",
    "Puja book karo",
    "Pooja karwani hai",
    "Pandit book karo",
    "Pandit chahiye",
    "Pandit book karna hai",
    "Kundli dikhao",
    "Janam Kundli",
    "Open Kundali",
    "Muhurat batao",
    "Shubh Muhurat",
    "Login kholo",
    "Signup karna hai",
    "Home chalo",
    "Go Home",
    "Dashboard",
    "Birth chart",
    "Sign in",
]


async def main():
    orchestrator = AIOrchestrator()
    
    results = []
    
    for cmd in TEST_COMMANDS:
        print(f"\n{'='*60}")
        print(f"TESTING: {cmd}")
        print(f"{'='*60}")
        
        try:
            req = OrchestratorRequest(
                user_message=cmd,
                session_id="test_session",
                conversation_id="test_conv",
                mode=ConversationMode.VOICE,
            )
            resp = await orchestrator.process_request(req)
            
            nav = resp.navigation_directive or {}
            result = {
                "command": cmd,
                "response_text": resp.text,
                "response_type": resp.response_type.value if resp.response_type else "UNKNOWN",
                "intent": nav.get("intent", "CHAT"),
                "action": nav.get("action", "CHAT"),
                "target": nav.get("target", None),
                "fast_path": resp.metadata.fast_path if resp.metadata else False,
            }
            results.append(result)
            
            print(f"  INTENT:        {result['intent']}")
            print(f"  ACTION:        {result['action']}")
            print(f"  TARGET:        {result['target']}")
            print(f"  RESPONSE_TEXT: {result['response_text']}")
            print(f"  FAST_PATH:     {result['fast_path']}")
            print(f"  RESPONSE_TYPE: {result['response_type']}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"command": cmd, "error": str(e)})
    
    # Summary table
    print(f"\n\n{'='*100}")
    print("SUMMARY TABLE")
    print(f"{'='*100}")
    print(f"{'Command':<30} {'Intent':<18} {'Target':<22} {'FastPath':<10} {'Response (truncated)'}")
    print(f"{'-'*30} {'-'*18} {'-'*22} {'-'*10} {'-'*40}")
    
    for r in results:
        if "error" in r:
            print(f"{r['command']:<30} {'ERROR':<18} {'':<22} {'':<10} {r['error'][:40]}")
        else:
            resp_text = r['response_text'][:40] if r['response_text'] else ""
            print(f"{r['command']:<30} {r['intent']:<18} {str(r['target']):<22} {str(r['fast_path']):<10} {resp_text}")


if __name__ == "__main__":
    asyncio.run(main())
