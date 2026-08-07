"""OCR Provider Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_models import OCRResult, ProviderCapability, ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseOCRAdapter(BaseProviderAdapter):
    """Base class for Optical Character Recognition Adapters."""

    def extract_text(self, document_bytes: bytes) -> OCRResult:
        return OCRResult(
            extracted_text=f"Mock extracted text from {self.spec.name} ({len(document_bytes)} bytes)",
            confidence=0.985,
            detected_language="en",
        )


class GoogleVisionOCRAdapter(BaseOCRAdapter):
    pass

class AzureOCRAdapter(BaseOCRAdapter):
    pass


class OCRProviderManager:
    """Manager for Optical Character Recognition Providers (Google Vision, Azure OCR)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("google_vision_ocr", "Google Vision OCR", ProviderCategory.OCR, capabilities=[ProviderCapability.OCR_EXTRACT], priority=1),
            ProviderSpec("azure_ocr", "Azure OCR", ProviderCategory.OCR, capabilities=[ProviderCapability.OCR_EXTRACT], priority=1),
        ]
        classes = [GoogleVisionOCRAdapter, AzureOCRAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def extract_text(self, document_bytes: bytes, provider_id: str = "google_vision_ocr") -> OCRResult:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            raise RuntimeError(f"OCR provider '{provider_id}' not found")
        res = adapter.extract_text(document_bytes)
        self.telemetry.record_request(provider_id=provider_id, category="OCR", latency_ms=1.4, success=True)
        return res
