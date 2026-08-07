"""Unit & Integration Test Suite for Enterprise Business Workflows Sprint 6D v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.business import (
    DonationWorkflow,
    KundaliRequestState,
    KundaliWorkflow,
    MuhuratWorkflow,
    PanditOnboardingWorkflow,
    ProfileManagementWorkflow,
    PujaBookingWorkflow,
    TempleDiscoveryWorkflow,
    WorkflowCoordinator,
    WorkflowTelemetryEngine,
)


class TestSprint6DBusinessWorkflows(unittest.TestCase):
    """Test suite covering all 7 production business workflows, coordinator, telemetry, SLAs, and thread safety."""

    def setUp(self):
        self.telemetry = WorkflowTelemetryEngine()
        self.coordinator = WorkflowCoordinator()
        self.pandit_onboarding = PanditOnboardingWorkflow()
        self.puja_booking = PujaBookingWorkflow()
        self.muhurat = MuhuratWorkflow()
        self.kundali = KundaliWorkflow()
        self.temple_discovery = TempleDiscoveryWorkflow()
        self.donation = DonationWorkflow()
        self.profile = ProfileManagementWorkflow()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all business workflow modules."""
        modules = [
            self.telemetry,
            self.coordinator,
            self.pandit_onboarding,
            self.puja_booking,
            self.muhurat,
            self.kundali,
            self.temple_discovery,
            self.donation,
            self.profile,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertEqual(health.get("status"), "HEALTHY")

    def test_pandit_onboarding_multi_step_and_draft_recovery(self):
        """Test Pandit voice onboarding, multi-step progress, pause/resume draft recovery, and submission."""
        draft = self.pandit_onboarding.start_onboarding(pandit_name="Pandit Ramesh Shastri", phone="9876543210", city="Varanasi")
        self.assertEqual(draft.current_step, 1)

        # Update step 2
        draft = self.pandit_onboarding.update_specializations(draft.draft_id, ["Satyanarayan Puja", "Griha Pravesh"], experience_years=15)
        self.assertEqual(draft.current_step, 3)

        # Resume draft
        recovered_draft = self.pandit_onboarding.resume_draft(draft.draft_id)
        self.assertIsNotNone(recovered_draft)
        self.assertEqual(recovered_draft.pandit_name, "Pandit Ramesh Shastri")

        # Submit
        res = self.pandit_onboarding.submit_onboarding(draft.draft_id)
        self.assertEqual(res["status"], "APPROVED")
        self.assertEqual(res["verification_status"], "VERIFIED")

    def test_puja_booking_workflow(self):
        """Test Puja booking initiation, pandit selection, and payment prep."""
        state = self.puja_booking.initiate_booking(user_id="u_100", puja_type="Satyanarayan Puja", booking_date="2026-08-15")
        self.assertEqual(state.status, "INITIATED")

        state = self.puja_booking.select_temple_and_pandit(state.booking_id, temple_id="tmp_kashi", pandit_id="pnd_100")
        self.assertEqual(state.status, "SLOT_VALIDATED")

        res = self.puja_booking.confirm_and_prepare_payment(state.booking_id)
        self.assertEqual(res["payment_status"], "PREPARED")
        self.assertIn("payment_gateway_payload", res)

    def test_muhurat_search_workflow(self):
        """Test Muhurat search date evaluation and recommendations."""
        res = self.muhurat.find_muhurat(purpose="Griha Pravesh", preferred_month="August 2026", location="Varanasi")
        self.assertIn("best_muhurat", res)
        self.assertGreater(len(res["alternative_muhurats"]), 0)

    def test_kundali_workflow(self):
        """Test Kundali report generation."""
        state = KundaliRequestState(person_name="Aarav", date_of_birth="1998-05-20", time_of_birth="08:30 AM", place_of_birth="Varanasi")
        res = self.kundali.generate_kundali_report(state)
        self.assertEqual(res["person_name"], "Aarav")
        self.assertIsNotNone(res["report_download_url"])

    def test_temple_discovery_workflow(self):
        """Test temple search and navigation handoff."""
        res = self.temple_discovery.discover_temples(city="Varanasi")
        self.assertGreater(len(res["temples"]), 0)
        self.assertIn("navigation_handoff", res)

    def test_donation_workflow(self):
        """Test temple donation processing and tax exemption receipt hooks."""
        res = self.donation.process_donation(temple_id="tmp_kashi", amount_inr=501.0, donor_name="Rohan")
        self.assertEqual(res["status"], "CONFIRMED")
        self.assertTrue(res["tax_exemption_80g"])

    def test_profile_management_workflow(self):
        """Test profile views and preference updates."""
        prof = self.profile.update_preferences(user_id="u_100", language="hi-IN", favorite_temple="tmp_kashi")
        self.assertEqual(prof.preferred_language, "hi-IN")
        self.assertIn("tmp_kashi", prof.favorite_temples)

    def test_workflow_coordinator_dispatch(self):
        """Test Workflow Coordinator dispatching across workflows."""
        res_booking = self.coordinator.dispatch_workflow("PujaBookingWorkflow", {"puja_type": "Rudrabhishek"})
        self.assertEqual(res_booking["workflow"], "PujaBookingWorkflow")

        res_muhurat = self.coordinator.dispatch_workflow("MuhuratWorkflow", {"purpose": "Marriage"})
        self.assertEqual(res_muhurat["workflow"], "MuhuratWorkflow")

    def test_thread_safety(self):
        def worker(idx: int):
            coord = WorkflowCoordinator()
            _ = coord.dispatch_workflow("MuhuratWorkflow", {"purpose": f"Purpose {idx}"})

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
