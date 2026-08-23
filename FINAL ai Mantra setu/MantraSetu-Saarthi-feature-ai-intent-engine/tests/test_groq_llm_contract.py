"""Focused Provider Contract Tests for Groq LLM Provider (llama-3.3-70b-versatile)."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import ExternalServiceError
from app.llm.factory import LLMProviderFactory
from app.llm.models import LLMRequest, LLMResponse
from app.llm.providers.groq import GroqProvider


class TestGroqLLMContract(unittest.TestCase):
    def setUp(self):
        self.provider = GroqProvider(api_key="mock_groq_key", model="llama-3.3-70b-versatile")

    def test_1_groq_provider_initializes(self):
        """Test provider initialization and properties."""
        self.assertEqual(self.provider.provider_name, "groq")
        self.assertEqual(self.provider.model_name, "llama-3.3-70b-versatile")
        self.assertTrue(self.provider.supports_streaming)

    def test_2_factory_registration(self):
        """Test retrieval from LLMProviderFactory."""
        factory = LLMProviderFactory()
        provider_cls = factory.get("groq")
        self.assertEqual(provider_cls, GroqProvider)

    def test_3_message_format_conversion(self):
        """Test conversion of LLMRequest system_prompt and messages."""
        req = LLMRequest(
            system_prompt="You are MantraSetu Saarthi AI.",
            messages=[
                {"role": "user", "content": "Namaste"},
                {"role": "assistant", "content": "Namaste! How can I assist you?"},
                {"role": "user", "content": "Pandit registration karni hai"},
            ],
        )
        msgs = self.provider._prepare_messages(req)
        self.assertEqual(len(msgs), 4)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[0]["content"], "You are MantraSetu Saarthi AI.")
        self.assertEqual(msgs[1]["role"], "user")
        self.assertEqual(msgs[2]["role"], "assistant")

    @patch("groq.AsyncGroq")
    def test_4_normal_response_parsed(self, mock_async_groq_cls):
        """Test normal text completion response parsing."""
        mock_client = MagicMock()
        mock_async_groq_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "Pranam! Pandit registration form bharne mein help karunga."
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 45
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 65

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_chat = MagicMock()
        mock_chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.chat = mock_chat

        req = LLMRequest(prompt="Pandit registration")
        res = asyncio.run(self.provider.generate(req))

        self.assertIsInstance(res, LLMResponse)
        self.assertIn("Pranam!", res.content)
        self.assertEqual(res.provider, "groq")
        self.assertEqual(res.model, "llama-3.3-70b-versatile")
        self.assertEqual(res.usage.total_tokens, 65)

    @patch("groq.AsyncGroq")
    def test_5_json_response_parsed(self, mock_async_groq_cls):
        """Test JSON structured output parsing compatibility."""
        json_payload = {
            "intent": "PANDIT_ONBOARDING",
            "field": "pandit-first-name",
            "extracted_value": "Ramesh",
        }
        mock_client = MagicMock()
        mock_async_groq_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(json_payload)
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=10, total_tokens=20)

        mock_chat = MagicMock()
        mock_chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.chat = mock_chat

        req = LLMRequest(prompt="Mera naam Ramesh hai")
        res = asyncio.run(self.provider.generate(req))

        parsed = json.loads(res.content)
        self.assertEqual(parsed["intent"], "PANDIT_ONBOARDING")
        self.assertEqual(parsed["extracted_value"], "Ramesh")

    @patch("groq.AsyncGroq")
    def test_6_streaming_response_works(self, mock_async_groq_cls):
        """Test async stream_generate token yielding."""
        mock_client = MagicMock()
        mock_async_groq_cls.return_value = mock_client

        class MockChunk:
            def __init__(self, token):
                self.choices = [MagicMock(delta=MagicMock(content=token))]

        async def async_generator():
            for t in ["Namaste", " ", "Pandit", " ", "Ji!"]:
                yield MockChunk(t)

        mock_chat = MagicMock()
        mock_chat.completions.create = AsyncMock(return_value=async_generator())
        mock_client.chat = mock_chat

        req = LLMRequest(prompt="Hello")

        async def collect_stream():
            chunks = []
            async for chunk in self.provider.stream_generate(req):
                chunks.append(chunk)
            return "".join(chunks)

        full_text = asyncio.run(collect_stream())
        self.assertEqual(full_text, "Namaste Pandit Ji!")

    @patch("groq.AsyncGroq")
    def test_7_api_exception_handled(self, mock_async_groq_cls):
        """Test API exception error propagation."""
        mock_client = MagicMock()
        mock_async_groq_cls.return_value = mock_client

        mock_chat = MagicMock()
        mock_chat.completions.create = AsyncMock(side_effect=Exception("Groq API 500 Internal Error"))
        mock_client.chat = mock_chat

        req = LLMRequest(prompt="Test")
        with self.assertRaises(ExternalServiceError) as ctx:
            asyncio.run(self.provider.generate(req))

        self.assertIn("Groq API error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
