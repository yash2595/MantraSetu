"""Unit Test Suite for Production Environment & Secret Configuration Validation (CRIT-01)."""

import os
import unittest
from app.validation.production_configuration_validator import ProductionConfigurationValidator


class TestProductionConfigValidation(unittest.TestCase):
    """Tests covering production environment variable validation, fail-fast behavior, and development mock modes."""

    def setUp(self):
        self.validator = ProductionConfigurationValidator()

    def test_production_startup_fail_fast_on_missing_keys(self):
        """Verify fail-fast exception when mandatory keys are missing in production mode."""
        bad_env = {
            "ENVIRONMENT": "production",
            "ALLOW_MOCK_PROVIDERS": "false",
            "OPENAI_API_KEY": "",  # Missing
            "POSTGRES_URL": "postgresql://localhost/db",
        }

        with self.assertRaises(RuntimeError) as ctx:
            self.validator.validate_production_environment(env_dict=bad_env, strict_mode=True)

        self.assertIn("Missing mandatory production environment variables", str(ctx.exception))
        self.assertIn("OPENAI_API_KEY", str(ctx.exception))

    def test_production_startup_fail_fast_on_placeholder_secrets(self):
        """Verify fail-fast exception when secrets contain placeholder strings."""
        bad_env = {
            "ENVIRONMENT": "production",
            "ALLOW_MOCK_PROVIDERS": "false",
            "OPENAI_API_KEY": "your_production_openai_api_key_here",  # Placeholder
            "JWT_SECRET_KEY": "change_this_to_a_secure_random_production_secret",
        }

        with self.assertRaises(RuntimeError) as ctx:
            self.validator.validate_production_environment(env_dict=bad_env, strict_mode=True)

        self.assertIn("OPENAI_API_KEY", str(ctx.exception))

    def test_development_startup_allows_missing_keys(self):
        """Verify development mode permits startup with warnings when keys are omitted."""
        dev_env = {
            "ENVIRONMENT": "development",
            "ALLOW_MOCK_PROVIDERS": "false",
        }

        res = self.validator.validate_production_environment(env_dict=dev_env, strict_mode=False)
        self.assertFalse(res["is_production"])
        self.assertTrue(res["valid"])

    def test_mock_provider_mode_enabled_in_production(self):
        """Verify setting ALLOW_MOCK_PROVIDERS=true bypasses missing key strict error."""
        mock_env = {
            "ENVIRONMENT": "production",
            "ALLOW_MOCK_PROVIDERS": "true",
        }

        res = self.validator.validate_production_environment(env_dict=mock_env, strict_mode=False)
        self.assertTrue(res["allow_mock_providers"])
        self.assertTrue(res["valid"])

    def test_valid_production_configuration(self):
        """Verify valid production environment configuration passes cleanly."""
        good_env = {
            "ENVIRONMENT": "production",
            "ALLOW_MOCK_PROVIDERS": "false",
            "OPENAI_API_KEY": "sk-proj-prod-real-key-100",
            "SARVAM_API_KEY": "sarvam-prod-real-key-100",
            "QWEN_API_KEY": "qwen-prod-real-key-100",
            "JWT_SECRET_KEY": "super_secret_production_jwt_signing_key_32bytes",
            "POSTGRES_URL": "postgresql://user:pass@postgres:5432/db",
            "REDIS_URL": "redis://redis:6379/0",
            "MONGODB_URL": "mongodb://mongo:27017/db",
            "QDRANT_HOST": "http://qdrant:6333",
        }

        res = self.validator.validate_production_environment(env_dict=good_env, strict_mode=True)
        self.assertEqual(len(res["missing_keys"]), 0)
        self.assertTrue(res["valid"])


if __name__ == "__main__":
    unittest.main()
