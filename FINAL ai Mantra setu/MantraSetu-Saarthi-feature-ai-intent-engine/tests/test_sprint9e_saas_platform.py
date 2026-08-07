"""Unit & Integration Test Suite for Enterprise SaaS Platform Sprint 9E v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.saas import (
    AdminDashboard,
    BillingManager,
    EnterpriseAnalytics,
    LicenseManager,
    OrganizationManager,
    PlanType,
    QuotaManager,
    SaaSTelemetryEngine,
    SubscriptionManager,
    TenantManager,
    TenantStatus,
)


class TestSprint9ESaaSPlatform(unittest.TestCase):
    """Test suite covering Tenant Manager, Organization Manager, Subscription Manager, Billing Manager, License Manager, Quota Manager, Enterprise Analytics, Admin Dashboard, Telemetry, SLA compliance, and Thread Safety."""

    def setUp(self):
        self.tenant_mgr = TenantManager()
        self.org_mgr = OrganizationManager()
        self.sub_mgr = SubscriptionManager()
        self.billing_mgr = BillingManager()
        self.license_mgr = LicenseManager()
        self.quota_mgr = QuotaManager()
        self.analytics = EnterpriseAnalytics()
        self.dashboard = AdminDashboard(
            tenant_mgr=self.tenant_mgr,
            org_mgr=self.org_mgr,
            sub_mgr=self.sub_mgr,
            billing_mgr=self.billing_mgr,
            license_mgr=self.license_mgr,
            quota_mgr=self.quota_mgr,
            analytics=self.analytics,
        )
        self.telemetry = SaaSTelemetryEngine()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 9E modules."""
        modules = [
            self.tenant_mgr,
            self.org_mgr,
            self.sub_mgr,
            self.billing_mgr,
            self.license_mgr,
            self.quota_mgr,
            self.analytics,
            self.dashboard,
            self.telemetry,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertEqual(health.get("status"), "HEALTHY")

    def test_multi_tenant_isolation_and_lifecycle(self):
        """Verify tenant provisioning, suspension, activation, termination, and isolation boundaries."""
        t1 = self.tenant_mgr.provision_tenant("Corp A", "org_1", "ENTERPRISE")
        t2 = self.tenant_mgr.provision_tenant("Corp B", "org_2", "PRO")

        self.assertEqual(t1.status, TenantStatus.ACTIVE)
        self.assertEqual(t2.status, TenantStatus.ACTIVE)

        # Isolation verification
        self.assertTrue(self.tenant_mgr.verify_isolation(t1.tenant_id, t1.tenant_id))
        self.assertFalse(self.tenant_mgr.verify_isolation(t1.tenant_id, t2.tenant_id))

        # Suspend
        self.tenant_mgr.suspend_tenant(t1.tenant_id, "Non-payment")
        self.assertEqual(self.tenant_mgr.get_tenant(t1.tenant_id).status, TenantStatus.SUSPENDED)
        self.assertFalse(self.tenant_mgr.verify_isolation(t1.tenant_id, t1.tenant_id))  # suspended

        # Reactivate
        self.tenant_mgr.reactivate_tenant(t1.tenant_id)
        self.assertEqual(self.tenant_mgr.get_tenant(t1.tenant_id).status, TenantStatus.ACTIVE)

        # Terminate
        self.tenant_mgr.terminate_tenant(t2.tenant_id)
        self.assertEqual(self.tenant_mgr.get_tenant(t2.tenant_id).status, TenantStatus.TERMINATED)

    def test_organization_hierarchy_and_roles(self):
        """Verify organization creation, teams, and user role assignments."""
        org = self.org_mgr.create_organization("Global Corp", "tenant_xyz")
        self.assertEqual(org.tenant_id, "tenant_xyz")

        team = self.org_mgr.add_team(org.org_id, "AI Research", "R&D")
        self.assertEqual(team.name, "AI Research")

        self.org_mgr.assign_user_role(org.org_id, "user_001", "ADMIN")
        roles = self.org_mgr.get_user_roles(org.org_id, "user_001")
        self.assertIn("ADMIN", roles)

    def test_subscription_upgrades_and_downgrades(self):
        """Verify subscription plan upgrades, downgrades, and tier properties."""
        sub = self.sub_mgr.create_subscription("tenant_123", PlanType.FREE)
        self.assertEqual(sub.plan_type, PlanType.FREE)

        # Upgrade
        upg = self.sub_mgr.upgrade_plan("tenant_123", PlanType.ENTERPRISE)
        self.assertEqual(upg.plan_type, PlanType.ENTERPRISE)

        # Downgrade
        dwg = self.sub_mgr.downgrade_plan("tenant_123", PlanType.PRO)
        self.assertEqual(dwg.plan_type, PlanType.PRO)

        # Details
        details = self.sub_mgr.get_plan_details(PlanType.PRO)
        self.assertEqual(details.max_seats, 15)

    def test_billing_and_invoicing(self):
        """Verify invoice generation, tax abstraction, and payment processing."""
        inv = self.billing_mgr.generate_invoice("tenant_123", 100.0, tax_rate_pct=10.0)
        self.assertEqual(inv.amount_usd, 100.0)
        self.assertEqual(inv.tax_amount_usd, 10.0)
        self.assertEqual(inv.total_amount_usd, 110.0)
        self.assertEqual(inv.status, "ISSUED")

        pmt = self.billing_mgr.process_payment(inv.invoice_id, "CREDIT_CARD")
        self.assertIsNotNone(pmt)
        self.assertEqual(pmt.status, "SUCCESS")
        self.assertEqual(pmt.amount_usd, 110.0)

        # Verify state
        inv_check = self.billing_mgr.get_invoices("tenant_123")[0]
        self.assertEqual(inv_check.status, "PAID")

    def test_license_management_and_validation(self):
        """Verify license key generation, activation, expiry check, and seat allocation."""
        lic = self.license_mgr.generate_license("tenant_555", "ENTERPRISE", seats=5, duration_days=30)
        self.assertTrue(lic.is_active)
        self.assertEqual(lic.total_seats, 5)

        # Allocate seats
        self.assertTrue(self.license_mgr.allocate_seat(lic.key_code, "user_a"))
        self.assertTrue(self.license_mgr.allocate_seat(lic.key_code, "user_b"))

        # Release seat
        self.assertTrue(self.license_mgr.release_seat(lic.key_code, "user_a"))
        
        # Validation
        self.assertTrue(self.license_mgr.validate_license(lic.key_code))
        
        check_lic = self.license_mgr.get_license(lic.key_code)
        self.assertEqual(check_lic.used_seats, 1)

    def test_quota_enforcement(self):
        """Verify tenant resource quotas, boundary limits, and consumption."""
        self.quota_mgr.set_tenant_quotas("tenant_api", api_call_limit=10)
        
        st1 = self.quota_mgr.consume_quota("tenant_api", "API", 8)
        self.assertFalse(st1.is_exceeded)
        
        st2 = self.quota_mgr.consume_quota("tenant_api", "API", 5)
        self.assertTrue(st2.is_exceeded)
        self.assertEqual(st2.exceeded_quota_type, "API")

        usage = self.quota_mgr.get_quota_usage("tenant_api")
        self.assertEqual(usage.api_calls_used, 8)  # Should not increment after fail

        self.quota_mgr.reset_quota_usage("tenant_api")
        usage2 = self.quota_mgr.get_quota_usage("tenant_api")
        self.assertEqual(usage2.api_calls_used, 0)

    def test_enterprise_analytics_and_dashboard_aggregation(self):
        """Verify analytics report generation and dashboard metric aggregation."""
        report = self.analytics.generate_tenant_report("tenant_1")
        self.assertEqual(report.tenant_id, "tenant_1")

        cost = self.analytics.generate_cost_analytics()
        self.assertIn("total_estimated_platform_cost_usd", cost)

        summary = self.dashboard.get_dashboard_summary()
        self.assertEqual(summary.system_health, "HEALTHY")

    def test_saas_telemetry(self):
        """Verify SaaS telemetry event recording and querying."""
        self.telemetry.record_event("BILLING_EVENT", "tenant_a", {"invoice": "123"})
        self.telemetry.record_event("TENANT_ACTIVITY", "tenant_b", {"login": True})

        recs = self.telemetry.get_records(event_type="BILLING_EVENT")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].tenant_id, "tenant_a")

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead, sub-5ms provisioning, billing, analytics SLA."""
        start = time.perf_counter()

        # Tenant Provisioning SLA
        t_start = time.perf_counter()
        _ = self.tenant_mgr.provision_tenant("Perf Corp", "org_p")
        t_ms = (time.perf_counter() - t_start) * 1000.0
        self.assertLess(t_ms, 5.0)

        # Billing SLA
        b_start = time.perf_counter()
        _ = self.billing_mgr.generate_invoice("Perf Corp", 100.0)
        b_ms = (time.perf_counter() - b_start) * 1000.0
        self.assertLess(b_ms, 5.0)

        # Analytics SLA
        a_start = time.perf_counter()
        _ = self.analytics.generate_tenant_report("Perf Corp")
        a_ms = (time.perf_counter() - a_start) * 1000.0
        self.assertLess(a_ms, 5.0)

        overall_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(overall_ms, 20.0)

    def test_thread_safety(self):
        """Verify concurrent tenant provisioning, billing, and telemetry across multiple threads."""
        def worker(idx: int):
            t_id = f"tenant_{idx}"
            self.tenant_mgr.provision_tenant(f"Corp {idx}", f"org_{idx}")
            inv = self.billing_mgr.generate_invoice(t_id, 10.0)
            self.billing_mgr.process_payment(inv.invoice_id)
            self.telemetry.record_event("API_CALL", t_id)
            self.quota_mgr.consume_quota(t_id, "TOKEN", 100)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(25)]
            for f in futures:
                f.result()

        stats = self.tenant_mgr.statistics()
        self.assertGreaterEqual(stats["total_tenants_provisioned"], 25)
        
        telemetry_stats = self.telemetry.statistics()
        self.assertGreaterEqual(telemetry_stats["total_saas_telemetry_records"], 25)


if __name__ == "__main__":
    unittest.main()
