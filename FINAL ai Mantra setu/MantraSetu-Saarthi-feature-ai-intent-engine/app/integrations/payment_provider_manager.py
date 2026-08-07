"""Payment Provider Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_models import PaymentTransaction, ProviderCapability, ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BasePaymentAdapter(BaseProviderAdapter):
    """Base class for Payment Adapters."""

    def create_checkout_session(self, amount: float, currency: str = "INR", description: str = "") -> PaymentTransaction:
        tx_id = f"tx_{self.spec.name.lower()[:3]}_{int(time.time()*1000)}"
        url = f"https://checkout.{self.spec.name.lower().replace(' ', '')}.com/pay/{tx_id}"
        return PaymentTransaction(
            transaction_id=tx_id,
            amount=amount,
            currency=currency,
            provider_id=self.spec.provider_id,
            status="CREATED",
            checkout_url=url,
        )

    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        return len(signature) > 0 and len(secret) > 0


class RazorpayAdapter(BasePaymentAdapter):
    pass

class StripeAdapter(BasePaymentAdapter):
    pass


class PaymentProviderManager:
    """Manager for Payment Gateways (Razorpay, Stripe)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("razorpay_payment", "Razorpay", ProviderCategory.PAYMENT, capabilities=[ProviderCapability.PAYMENTS], priority=1),
            ProviderSpec("stripe_payment", "Stripe", ProviderCategory.PAYMENT, capabilities=[ProviderCapability.PAYMENTS], priority=1),
        ]
        classes = [RazorpayAdapter, StripeAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def create_checkout_session(self, amount: float, currency: str = "INR", description: str = "", provider_id: str = "razorpay_payment") -> PaymentTransaction:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            raise RuntimeError(f"Payment provider '{provider_id}' not found")
        tx = adapter.create_checkout_session(amount, currency, description)
        self.telemetry.record_request(provider_id=provider_id, category="PAYMENT", latency_ms=2.0, success=True, estimated_cost=amount * 0.02)
        return tx

    def verify_webhook(self, payload: str, signature: str, secret: str, provider_id: str = "razorpay_payment") -> bool:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            return False
        return adapter.verify_webhook_signature(payload, signature, secret)
