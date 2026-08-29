import os

root_dir = r"c:\Users\hp\OneDrive\Pictures\Documents\Desktop\MantraSetu\FINAL ai Mantra setu\MantraSetu-Saarthi-feature-ai-intent-engine"

secrets = [
    ("mock_test_c.py", [8]),
    ("test_rate_limiting.py", [6]),
    ("app/api/dependencies/auth.py", [10]),
    ("app/config/production.env.example", [78, 87, 90, 93]),
    ("app/llm/providers/gemini.py", [54, 59]),
    ("app/llm/providers/groq.py", [36, 112, 171, 229]),
    ("app/orchestrator/pandit_onboarding.py", [28, 30]),
    ("app/speech/providers/sarvam.py", [21]),
    ("app/tts/providers/cosyvoice.py", [15]),
    ("app/tts/providers/elevenlabs_provider.py", [82]),
    ("app/voice/stt/groq_adapter.py", [28, 105]),
    ("app/voice/stt/sarvam_adapter.py", [20]),
    ("app/voice/stt/whisper_adapter.py", [22, 207]),
    ("app/voice/tts/elevenlabs_adapter.py", [31]),
    ("app/voice/tts/openai_adapter.py", [24]),
    ("app/voice/tts/sarvam_adapter.py", [24]),
    ("scripts/ai_intelligence_validation_v2.py", [254, 590]),
    ("scripts/llm_certification_benchmark.py", [137]),
    ("tests/test_groq_llm_contract.py", [16]),
    ("tests/test_groq_stt_contract.py", [17, 27]),
    ("tests/test_inworld_tts_contract.py", [24, 40, 52])
]

fallbacks = [
    "app/api/dependencies/voice.py",
    "app/api/v1/routes/stubs.py",
    "app/dependencies/providers.py",
    "app/llm/settings.py",
    "app/llm/providers/gemini.py",
    "app/llm/providers/groq.py",
    "app/orchestrator/defaults.py",
    "app/orchestrator/pandit_onboarding.py",
    "app/tts/providers/elevenlabs_provider.py",
    "app/voice/stt/groq_adapter.py",
    "app/voice/stt/whisper_adapter.py",
    "app/voice/tts/elevenlabs_adapter.py",
    "app/voice/tts/inworld_adapter.py"
]

with open(os.path.join(root_dir, "scratch", "context.txt"), "w", encoding="utf-8") as out:
    out.write("SECRETS\n=======\n")
    for file, lines in secrets:
        path = os.path.join(root_dir, file.replace('/', '\\'))
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.readlines()
                for line_num in lines:
                    out.write(f"\n--- {file}:{line_num} ---\n")
                    start = max(0, line_num - 2)
                    end = min(len(content), line_num + 1)
                    for i in range(start, end):
                        prefix = ">> " if i == line_num - 1 else "   "
                        out.write(f"{prefix}{i+1}: {content[i]}")
        except Exception as e:
            out.write(f"Error reading {file}: {e}\n")

    out.write("\nFALLBACKS\n=========\n")
    for file in fallbacks:
        path = os.path.join(root_dir, file.replace('/', '\\'))
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.readlines()
                out.write(f"\n--- {file} ---\n")
                for i, line in enumerate(content):
                    if "os.getenv(" in line or "os.environ.get(" in line:
                        out.write(f"   {i+1}: {line.strip()}\n")
        except Exception as e:
            out.write(f"Error reading {file}: {e}\n")
