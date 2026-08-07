"""Comprehensive Unit & Integration Test Suite for Enterprise Security, Identity & Governance Framework v1.0."""

import time
import unittest
from app.security.audit_manager import AuditManager
from app.security.authentication_manager import AuthenticationManager
from app.security.authorization_manager import AuthorizationManager
from app.security.identity_manager import IdentityManager
from app.security.secret_manager import SecretManager
from app.security.security_models import (
    AuditAction,
    AuthenticationState,
    AuthorizationState,
    RoleType,
    SecurityPolicy,
)
from app.security.security_policy import SecurityPolicyEngine
from app.security.security_telemetry import SecurityTelemetryEngine
from app.security.threat_detector import ThreatDetector
from app.security.token_manager import TokenManager


class TestIdentityTokenAndAuthentication(unittest.TestCase):
    """Test suite for IdentityManager, TokenManager, and AuthenticationManager."""

    def setUp(self):
        self.identity_mgr = IdentityManager()
        self.token_mgr = TokenManager()
        self.auth_mgr = AuthenticationManager(self.identity_mgr, self.token_mgr)

    def test_identity_resolution_and_role_assignment(self):
        identity = self.identity_mgr.resolve_identity("usr_sec_100")
        self.assertEqual(identity.user_id, "usr_sec_100")
        self.assertIn(RoleType.USER, identity.roles)

        updated = self.identity_mgr.assign_role("usr_sec_100", RoleType.PANDIT)
        self.assertIn(RoleType.PANDIT, updated.roles)

    def test_token_issuance_validation_and_revocation(self):
        token = self.token_mgr.issue_access_token("usr_sec_100", ["USER"])
        self.assertIsNotNone(token.token_str)

        is_valid, fetched = self.token_mgr.validate_token(token.token_str)
        self.assertTrue(is_valid)
        self.assertEqual(fetched.user_id, "usr_sec_100")

        self.token_mgr.revoke_token(token.token_id)
        is_valid_after, _ = self.token_mgr.validate_token(token.token_str)
        self.assertFalse(is_valid_after)

    def test_authentication_flow(self):
        state, token = self.auth_mgr.authenticate_credentials("usr_sec_100", "valid_secret")
        self.assertEqual(state, AuthenticationState.AUTHENTICATED)
        self.assertIsNotNone(token)

        state_invalid, _ = self.auth_mgr.authenticate_credentials("usr_sec_100", "invalid")
        self.assertEqual(state_invalid, AuthenticationState.UNAUTHENTICATED)


class TestAuthorizationSecretsAndAudit(unittest.TestCase):
    """Test suite for AuthorizationManager, SecretManager, AuditManager, and ThreatDetector."""

    def setUp(self):
        self.identity_mgr = IdentityManager()
        self.token_mgr = TokenManager()
        self.auth_mgr = AuthenticationManager(self.identity_mgr, self.token_mgr)
        self.authz_mgr = AuthorizationManager()
        self.secret_mgr = SecretManager()
        self.audit_mgr = AuditManager()
        self.threat_detector = ThreatDetector()

    def test_rbac_authorization(self):
        _, context = self.auth_mgr.validate_session(self.auth_mgr.authenticate_credentials("admin_01", "valid")[1].token_str)
        self.assertIsNotNone(context)

        authz_state = self.authz_mgr.authorize_action(context, required_permission="ADMIN")
        self.assertEqual(authz_state, AuthorizationState.GRANTED)

    def test_secret_management_and_rotation(self):
        val = self.secret_mgr.get_secret("SYSTEM_API_KEY")
        self.assertIsNotNone(val)

        new_val = self.secret_mgr.rotate_key("SYSTEM_API_KEY")
        self.assertNotEqual(val, new_val)
        self.assertEqual(self.secret_mgr.get_secret("SYSTEM_API_KEY"), new_val)

    def test_audit_logging_and_threat_detection(self):
        audit = self.audit_mgr.log_audit("usr_sec_100", AuditAction.LOGIN, resource="/api/login")
        self.assertIsNotNone(audit.audit_id)
        self.assertEqual(len(self.audit_mgr.get_audit_logs("usr_sec_100")), 1)

        # Trigger rate limit threat
        incident = None
        for _ in range(12):
            incident = self.threat_detector.evaluate_threat("192.168.1.1", "usr_attacker", "LOGIN")

        self.assertIsNotNone(incident)


if __name__ == "__main__":
    unittest.main()
