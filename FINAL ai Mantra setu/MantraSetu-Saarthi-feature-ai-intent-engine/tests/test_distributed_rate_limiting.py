"""Unit Test Suite for Distributed Rate Limiting (MED-02)."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.infrastructure.api_gateway import APIGateway
from app.infrastructure.production_database_adapters import RedisProductionAdapter


class TestDistributedRateLimiting(unittest.TestCase):
    """Tests covering multi-instance rate-limiting via Redis, atomic counter increments, RPM thresholds, and TTL expiration."""

    def setUp(self):
        self.shared_redis = RedisProductionAdapter()
        # Create 2 gateway instances sharing the same Redis adapter with low max_rpm for testing
        self.gateway_a = APIGateway(redis_adapter=self.shared_redis, max_rpm=5)
        self.gateway_b = APIGateway(redis_adapter=self.shared_redis, max_rpm=5)

    def test_distributed_rate_limiting_across_multiple_instances(self):
        """Verify requests on Gateway A count towards the RPM limit on Gateway B for the same client IP."""
        client_ip = "192.168.1.50"
        headers = {"x-forwarded-for": client_ip}

        # 3 requests on Gateway A
        for _ in range(3):
            res_a = self.gateway_a.route_request(path="/api/v1/test", headers=headers)
            self.assertEqual(res_a["status_code"], 200)

        # 2 requests on Gateway B (Total 5 - limit reached)
        for _ in range(2):
            res_b = self.gateway_b.route_request(path="/api/v1/test", headers=headers)
            self.assertEqual(res_b["status_code"], 200)

        # 6th request on Gateway B should be rate-limited (429)
        res_exceeded = self.gateway_b.route_request(path="/api/v1/test", headers=headers)
        self.assertEqual(res_exceeded["status_code"], 429)
        self.assertIn("Rate limit exceeded", res_exceeded["error"])

    def test_concurrent_requests_rate_limiting(self):
        """Verify thread-safe rate-limiting under high concurrent request volume."""
        client_ip = "10.0.0.1"

        def send_request(idx: int):
            return self.gateway_a.route_request(
                path="/api/v1/puja",
                headers={"x-forwarded-for": client_ip},
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_request, i) for i in range(10)]
            results = [f.result() for f in futures]

        status_200s = sum(1 for r in results if r["status_code"] == 200)
        status_429s = sum(1 for r in results if r["status_code"] == 429)

        self.assertEqual(status_200s, 5)
        self.assertEqual(status_429s, 5)

    def test_rate_limit_expiration_and_recovery(self):
        """Verify client recovers after Redis key TTL expires."""
        client_ip = "172.16.0.5"
        headers = {"x-forwarded-for": client_ip}

        # Reach limit
        for _ in range(5):
            self.gateway_a.route_request(path="/api/v1/test", headers=headers)

        res_limited = self.gateway_a.route_request(path="/api/v1/test", headers=headers)
        self.assertEqual(res_limited["status_code"], 429)

        # Manually clear/expire Redis key to test recovery
        key = f"rate_limit:{client_ip}"
        self.shared_redis.delete(key)

        res_recovered = self.gateway_b.route_request(path="/api/v1/test", headers=headers)
        self.assertEqual(res_recovered["status_code"], 200)


if __name__ == "__main__":
    unittest.main()
