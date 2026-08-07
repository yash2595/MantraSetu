"""Run a 50-prompt live LLM benchmark for certification evidence.

The benchmark sends intent-classification prompts to OpenRouter and scores
JSON parseability, intent accuracy, latency, token usage, and cost.
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv


@dataclass(frozen=True)
class BenchmarkCase:
    expected: str
    prompt: str


SYSTEM_PROMPT = (
    "You are an intent-classification evaluator for a Hindu spiritual services assistant. "
    "Return strict JSON only with keys intent, confidence, entities, answer. "
    "Choose intent from TEMPLE_SEARCH, PUJA_BOOKING, DONATION, PANDIT_ONBOARDING, KUNDALI, "
    "MUHURAT, FESTIVAL_QUERY, GENERAL_CONVERSATION, SMALL_TALK, UNKNOWN_INTENT, MULTI_INTENT. "
    "The answer field should be a short helpful reply."
)


BENCHMARK_CASES: list[BenchmarkCase] = [
    BenchmarkCase("TEMPLE_SEARCH", "Find me a nearby Shiva temple in Jaipur"),
    BenchmarkCase("TEMPLE_SEARCH", "Show temples near me for tonight aarti"),
    BenchmarkCase("TEMPLE_SEARCH", "Which temple is best for darshan in Varanasi?"),
    BenchmarkCase("TEMPLE_SEARCH", "Locate a Hanuman temple in Delhi"),
    BenchmarkCase("PUJA_BOOKING", "Book a Satyanarayan Puja for tomorrow"),
    BenchmarkCase("PUJA_BOOKING", "I want to schedule Ganesh Puja this weekend"),
    BenchmarkCase("PUJA_BOOKING", "Reserve a puja slot for next Monday morning"),
    BenchmarkCase("PUJA_BOOKING", "Help me book Rudrabhishek at home"),
    BenchmarkCase("DONATION", "I want to donate to the temple"),
    BenchmarkCase("DONATION", "Make a donation for annadanam"),
    BenchmarkCase("DONATION", "How can I contribute to the temple trust?"),
    BenchmarkCase("DONATION", "Donate Rs 500 for renovation"),
    BenchmarkCase("PANDIT_ONBOARDING", "How do I register as a pandit?"),
    BenchmarkCase("PANDIT_ONBOARDING", "I want to onboard as a priest"),
    BenchmarkCase("PANDIT_ONBOARDING", "Pandit registration process please"),
    BenchmarkCase("PANDIT_ONBOARDING", "What documents are needed for pandit onboarding?"),
    BenchmarkCase("KUNDALI", "Generate my kundali from birth details"),
    BenchmarkCase("KUNDALI", "Check janam kundali compatibility"),
    BenchmarkCase("KUNDALI", "I need a horoscope reading"),
    BenchmarkCase("KUNDALI", "Tell me about my birth chart"),
    BenchmarkCase("MUHURAT", "Find an auspicious muhurat for housewarming"),
    BenchmarkCase("MUHURAT", "What is the best muhurat for marriage next month?"),
    BenchmarkCase("MUHURAT", "Suggest shubh muhurat for opening a shop"),
    BenchmarkCase("MUHURAT", "Need an auspicious time for travel"),
    BenchmarkCase("FESTIVAL_QUERY", "When is Janmashtami this year?"),
    BenchmarkCase("FESTIVAL_QUERY", "Tell me about Diwali dates"),
    BenchmarkCase("FESTIVAL_QUERY", "What is the significance of Navratri?"),
    BenchmarkCase("FESTIVAL_QUERY", "When does Ganesh Chaturthi start?"),
    BenchmarkCase("GENERAL_CONVERSATION", "Can you help me plan my day?"),
    BenchmarkCase("GENERAL_CONVERSATION", "What services do you offer?"),
    BenchmarkCase("GENERAL_CONVERSATION", "How does this platform work?"),
    BenchmarkCase("GENERAL_CONVERSATION", "Give me a quick overview of your capabilities"),
    BenchmarkCase("SMALL_TALK", "Hello there"),
    BenchmarkCase("SMALL_TALK", "Good morning"),
    BenchmarkCase("SMALL_TALK", "Thanks a lot"),
    BenchmarkCase("SMALL_TALK", "How are you today?"),
    BenchmarkCase("UNKNOWN_INTENT", "Blue bananas under 17 umbrellas"),
    BenchmarkCase("UNKNOWN_INTENT", "Quantum tennis toaster parade"),
    BenchmarkCase("UNKNOWN_INTENT", "Please translate the moon into accounting"),
    BenchmarkCase("UNKNOWN_INTENT", "Mars paperwork with cinnamon rules"),
    BenchmarkCase("MULTI_INTENT", "Book a puja and tell me the muhurat"),
    BenchmarkCase("MULTI_INTENT", "Find a temple and donate 500 rupees"),
    BenchmarkCase("MULTI_INTENT", "Check my kundali and suggest a festival date"),
    BenchmarkCase("MULTI_INTENT", "I want to book a puja and register as a pandit"),
    BenchmarkCase("MULTI_INTENT", "Need a temple near me and an auspicious time"),
    BenchmarkCase("MULTI_INTENT", "Help me donate and book a puja slot"),
    BenchmarkCase("MULTI_INTENT", "Plan a festival visit and horoscope reading"),
    BenchmarkCase("MULTI_INTENT", "I want temple info and small talk"),
    BenchmarkCase("MULTI_INTENT", "Schedule a puja, then give me the festival calendar"),
    BenchmarkCase("MULTI_INTENT", "Locate a temple and explain how onboarding works"),
]


async def classify_case(client: httpx.AsyncClient, base_url: str, model: str, case: BenchmarkCase) -> dict[str, object]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": case.prompt},
        ],
        "temperature": 0,
    }
    started = time.perf_counter()
    response = await client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload)
    latency_ms = (time.perf_counter() - started) * 1000.0
    response.raise_for_status()
    data = response.json()
    choice = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    parsed: dict[str, object] | None = None
    parse_error: str | None = None
    try:
        parsed = json.loads(choice)
    except Exception as exc:  # pragma: no cover - benchmark diagnostics only
        parse_error = str(exc)

    predicted = parsed.get("intent") if isinstance(parsed, dict) else None
    confidence = parsed.get("confidence") if isinstance(parsed, dict) else None
    entities = parsed.get("entities") if isinstance(parsed, dict) else None
    answer = parsed.get("answer") if isinstance(parsed, dict) else None

    return {
        "expected": case.expected,
        "prompt": case.prompt,
        "predicted": predicted,
        "confidence": confidence,
        "entities": entities,
        "answer": answer,
        "latency_ms": latency_ms,
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
        "total_tokens": int(usage.get("total_tokens", 0)),
        "cost": float(usage.get("cost", 0.0)),
        "parse_error": parse_error,
        "raw": choice,
    }


async def main() -> int:
    load_dotenv()
    api_key = os.getenv("API_KEY", "").strip()
    base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1").strip()
    model = os.getenv("MODEL", "qwen/qwen-2.5-72b-instruct").strip()

    if not api_key:
        print("API_KEY missing")
        return 1

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "MantraSetu AI Backend",
    }

    timeout = httpx.Timeout(60.0, connect=10.0)
    results: list[dict[str, object]] = []

    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        for index, case in enumerate(BENCHMARK_CASES, start=1):
            result = await classify_case(client, base_url, model, case)
            results.append(result)
            print(
                f"{index:02d}/{len(BENCHMARK_CASES)} "
                f"expected={result['expected']} predicted={result['predicted']} "
                f"latency_ms={result['latency_ms']:.1f} tokens={result['total_tokens']} cost={result['cost']}"
            )

    total = len(results)
    parsed_ok = sum(1 for result in results if result["parse_error"] is None)
    correct = sum(1 for result in results if result["predicted"] == result["expected"])
    multi_intent_correct = sum(
        1 for result in results if result["expected"] == "MULTI_INTENT" and result["predicted"] == "MULTI_INTENT"
    )
    unknown_intent_correct = sum(
        1 for result in results if result["expected"] == "UNKNOWN_INTENT" and result["predicted"] == "UNKNOWN_INTENT"
    )

    latencies = [float(result["latency_ms"]) for result in results]
    tokens = [int(result["total_tokens"]) for result in results]
    costs = [float(result["cost"]) for result in results]

    summary = {
        "total_prompts": total,
        "json_parse_rate": round(parsed_ok / total, 4),
        "intent_accuracy": round(correct / total, 4),
        "multi_intent_accuracy": round(multi_intent_correct / 10, 4),
        "unknown_intent_accuracy": round(unknown_intent_correct / 4, 4),
        "latency_ms_avg": round(statistics.mean(latencies), 2),
        "latency_ms_p95": round(sorted(latencies)[max(0, int(total * 0.95) - 1)], 2),
        "tokens_avg": round(statistics.mean(tokens), 2),
        "cost_total": round(sum(costs), 8),
        "cost_avg": round(statistics.mean(costs), 8),
    }

    print("\nSUMMARY")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))