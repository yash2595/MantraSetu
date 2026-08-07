"""Message Queue Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any, Callable
from app.integrations.integration_models import ProviderCapability, ProviderCategory, ProviderSpec
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseMessageQueueAdapter(BaseProviderAdapter):
    """Base class for Message Queue Adapters."""

    def __init__(self, spec: ProviderSpec):
        super().__init__(spec)
        self._queues: dict[str, list[dict[str, Any]]] = {}

    def publish(self, topic: str, message: dict[str, Any]) -> str:
        queue = self._queues.setdefault(topic, [])
        msg_id = f"msg_{len(queue) + 1}"
        queue.append({"msg_id": msg_id, "payload": message, "published_at": time.time()})
        return msg_id

    def consume(self, topic: str, max_messages: int = 10) -> list[dict[str, Any]]:
        queue = self._queues.get(topic, [])
        messages = queue[:max_messages]
        self._queues[topic] = queue[max_messages:]
        return messages


class RabbitMQAdapter(BaseMessageQueueAdapter):
    pass

class KafkaAdapter(BaseMessageQueueAdapter):
    pass

class SQSAdapter(BaseMessageQueueAdapter):
    pass

class RedisPubSubAdapter(BaseMessageQueueAdapter):
    pass


class MessageQueueManager:
    """Manager for Enterprise Messaging & Event Streaming (RabbitMQ, Kafka, SQS, Redis PubSub)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("rabbitmq_mq", "RabbitMQ", ProviderCategory.MESSAGE_QUEUE, capabilities=[ProviderCapability.PUB_SUB], priority=1),
            ProviderSpec("kafka_mq", "Kafka", ProviderCategory.MESSAGE_QUEUE, capabilities=[ProviderCapability.PUB_SUB], priority=1),
            ProviderSpec("sqs_mq", "AWS SQS", ProviderCategory.MESSAGE_QUEUE, capabilities=[ProviderCapability.PUB_SUB], priority=2),
            ProviderSpec("redis_pubsub_mq", "Redis PubSub", ProviderCategory.MESSAGE_QUEUE, capabilities=[ProviderCapability.PUB_SUB], priority=2),
        ]
        classes = [RabbitMQAdapter, KafkaAdapter, SQSAdapter, RedisPubSubAdapter]
        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def publish(self, topic: str, message: dict[str, Any], provider_id: str = "kafka_mq") -> str:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            raise RuntimeError(f"MQ provider '{provider_id}' not found")
        msg_id = adapter.publish(topic, message)
        self.telemetry.record_request(provider_id=provider_id, category="MESSAGE_QUEUE", latency_ms=0.5, success=True)
        return msg_id

    def consume(self, topic: str, max_messages: int = 10, provider_id: str = "kafka_mq") -> list[dict[str, Any]]:
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            return []
        return adapter.consume(topic, max_messages)
