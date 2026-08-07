"""Unit Test Suite for Legacy Abstract Base Compatibility (HIGH-01)."""

import unittest
from app.llm.base import BaseLLMProvider
from app.providers import (
    ProductionLLMProviderManager,
    ProductionSTTProviderManager,
    ProductionTTSProviderManager,
)
from app.speech.base import BaseSpeechToTextProvider
from app.speech.providers.sarvam import SarvamProvider
from app.tts.base import BaseTextToSpeechProvider
from app.tts.providers.cosyvoice import CosyVoiceProvider


class TestLegacyCompatibility(unittest.TestCase):
    """Tests ensuring abstract base classes cannot be instantiated directly and production adapters remain functional."""

    def test_abstract_classes_cannot_be_instantiated(self):
        """Verify ABC instantiation raises TypeError."""
        with self.assertRaises(TypeError):
            BaseLLMProvider()

        with self.assertRaises(TypeError):
            BaseSpeechToTextProvider()

        with self.assertRaises(TypeError):
            BaseTextToSpeechProvider()

    def test_legacy_providers_raise_informative_not_implemented_error(self):
        """Verify calling legacy provider methods raises NotImplementedError pointing to app.providers."""
        sarvam_stt = SarvamProvider()
        with self.assertRaises(NotImplementedError) as ctx_stt:
            import asyncio

            asyncio.run(sarvam_stt.transcribe(None))  # type: ignore

        self.assertIn("app.providers.ProductionSTTProviderManager", str(ctx_stt.exception))

        cosy_tts = CosyVoiceProvider()
        with self.assertRaises(NotImplementedError) as ctx_tts:
            import asyncio

            asyncio.run(cosy_tts.synthesize(None))  # type: ignore

        self.assertIn("app.providers.ProductionTTSProviderManager", str(ctx_tts.exception))

    def test_production_provider_adapters_continue_operating(self):
        """Verify production provider managers in app.providers operate cleanly."""
        llm_mgr = ProductionLLMProviderManager()
        stt_mgr = ProductionSTTProviderManager()
        tts_mgr = ProductionTTSProviderManager()

        self.assertEqual(llm_mgr.health()["status"], "HEALTHY")
        self.assertEqual(stt_mgr.health()["status"], "HEALTHY")
        self.assertEqual(tts_mgr.health()["status"], "HEALTHY")


if __name__ == "__main__":
    unittest.main()
