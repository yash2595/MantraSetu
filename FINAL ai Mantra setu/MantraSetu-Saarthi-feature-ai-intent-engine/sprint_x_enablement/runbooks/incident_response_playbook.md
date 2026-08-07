# Incident Response Playbook

## P1: Primary Provider Failure (OpenAI/Anthropic Outage)
1. Detect `AI_5001` spike in Telemetry.
2. Toggle `production_flags.yaml` to secondary provider.
3. Notify Backend teams.

## P2: RAG Embedding Drift
1. Detect Hallucination Rate > 5%.
2. Re-trigger Qdrant sync recovery scripts.
3. Validate against Golden Dataset.
