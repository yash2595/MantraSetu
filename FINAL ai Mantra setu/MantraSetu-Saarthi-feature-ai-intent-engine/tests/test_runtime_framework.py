"""Comprehensive Unit & Integration Test Suite for Enterprise Deployment, Runtime & Infrastructure Framework v1.0."""

import time
import unittest
from app.infrastructure.configuration_manager import ConfigurationManager
from app.infrastructure.configuration_validator import ConfigurationValidator
from app.infrastructure.deployment_manager import DeploymentManager
from app.infrastructure.environment_manager import EnvironmentManager
from app.infrastructure.failover_manager import FailoverManager
from app.infrastructure.load_balancer import LoadBalancer
from app.infrastructure.resource_manager import ResourceManager
from app.infrastructure.runtime_health import RuntimeHealthAggregator
from app.infrastructure.runtime_manager import RuntimeManager
from app.infrastructure.runtime_models import (
    EnvironmentProfile,
    LoadBalancingAlgorithm,
    ScalingPolicy,
    ServiceEndpoint,
    ServiceState,
)
from app.infrastructure.scaling_manager import ScalingManager
from app.infrastructure.service_discovery import ServiceDiscovery
from app.infrastructure.service_registry import ServiceRegistry


class TestConfigurationAndEnvironment(unittest.TestCase):
    """Test suite for ConfigurationManager, EnvironmentManager, and ConfigurationValidator."""

    def setUp(self):
        self.config_mgr = ConfigurationManager()
        self.env_mgr = EnvironmentManager()
        self.validator = ConfigurationValidator()

    def test_configuration_setting_lookup(self):
        app_name = self.config_mgr.get_setting("APP_NAME")
        self.assertEqual(app_name, "MantraSetu AgentOS")

        self.config_mgr.set_setting("NEW_SETTING", "custom_val")
        self.assertEqual(self.config_mgr.get_setting("NEW_SETTING"), "custom_val")

    def test_environment_profile_switching(self):
        profile = self.env_mgr.get_active_profile()
        self.assertEqual(profile, EnvironmentProfile.DEVELOPMENT)

        context = self.env_mgr.switch_profile(EnvironmentProfile.PRODUCTION)
        self.assertEqual(context.profile, EnvironmentProfile.PRODUCTION)
        self.assertFalse(context.is_debug)


class TestServiceDiscoveryLoadBalancingAndScaling(unittest.TestCase):
    """Test suite for ServiceRegistry, ServiceDiscovery, LoadBalancer, FailoverManager, and ScalingManager."""

    def setUp(self):
        self.registry = ServiceRegistry()
        self.discovery = ServiceDiscovery(self.registry)
        self.balancer = LoadBalancer()
        self.failover_mgr = FailoverManager(self.registry)
        self.scaling_mgr = ScalingManager()

    def test_service_registration_and_discovery(self):
        ep2 = ServiceEndpoint(endpoint_id="ep_api_02", service_name="api_gateway", port=8001)
        self.registry.register_service(ep2)

        discovered = self.discovery.discover_service("api_gateway")
        self.assertGreaterEqual(len(discovered), 2)

    def test_load_balancing_and_failover(self):
        endpoints = self.discovery.discover_service("api_gateway")
        selected = self.balancer.select_endpoint(endpoints, LoadBalancingAlgorithm.ROUND_ROBIN)
        self.assertIsNotNone(selected)

        # Trigger endpoint failover
        backup = self.failover_mgr.handle_service_failure("ep_api_01")
        self.assertIsNotNone(backup)
        self.assertEqual(backup.endpoint_id, "ep_api_02")

    def test_scaling_policy_evaluation(self):
        policy = ScalingPolicy(min_replicas=2, max_replicas=10, target_cpu_percent=75.0)
        should_scale, target = self.scaling_mgr.evaluate_scaling(policy, current_cpu_percent=85.0)
        self.assertTrue(should_scale)
        self.assertGreater(target, 2)


class TestRuntimeHealthAndManager(unittest.TestCase):
    """Test suite for RuntimeManager and RuntimeHealthAggregator."""

    def setUp(self):
        self.runtime_mgr = RuntimeManager()
        self.health_agg = RuntimeHealthAggregator()

    def test_runtime_lifecycle_and_health(self):
        self.assertTrue(self.runtime_mgr.start_runtime())
        self.assertTrue(self.runtime_mgr.stop_runtime())

        health = self.health_agg.get_runtime_health()
        self.assertEqual(health.status, "HEALTHY")


if __name__ == "__main__":
    unittest.main()
