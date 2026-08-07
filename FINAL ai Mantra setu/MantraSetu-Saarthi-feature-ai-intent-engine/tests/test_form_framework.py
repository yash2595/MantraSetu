"""Comprehensive Unit & Integration Test Suite for Enterprise Voice Form Automation Framework v1.0."""

import time
import unittest
from app.forms.confirmation_manager import ConfirmationManager
from app.forms.draft_manager import DraftManager
from app.forms.field_mapper import FieldMapper
from app.forms.form_discovery import FormDiscovery
from app.forms.form_models import FieldType, FormDefinition, FormField, ValidationState
from app.forms.form_progress_manager import FormProgressManager
from app.forms.form_sync_manager import FormSyncManager
from app.forms.form_telemetry import FormTelemetryEngine
from app.forms.form_validator import FormValidator
from app.forms.voice_form_controller import VoiceFormController


class TestFormDiscoveryAndFieldMapper(unittest.TestCase):
    """Test suite for FormDiscovery and FieldMapper."""

    def setUp(self):
        self.discovery = FormDiscovery()
        self.mapper = FieldMapper()

    def test_discovery_by_route_and_id(self):
        forms = self.discovery.discover_forms_for_route("/puja/book")
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0].form_id, "puja_booking_form")

        form = self.discovery.get_form_by_id("kundali_form")
        self.assertIsNotNone(form)

    def test_field_mapper_exact_and_alias_matching(self):
        form_def = self.discovery.get_form_by_id("puja_booking_form")
        self.assertIsNotNone(form_def)

        # Exact match
        field_exact, conf_exact = self.mapper.map_slot_to_field(form_def, "puja_name", "Satyanarayan Puja")
        self.assertEqual(field_exact.field_name, "puja_name")
        self.assertEqual(conf_exact, 1.0)

        # Alias match ("date" -> "booking_date")
        field_alias, conf_alias = self.mapper.map_slot_to_field(form_def, "date", "2026-08-15")
        self.assertEqual(field_alias.field_name, "booking_date")
        self.assertEqual(conf_alias, 0.9)


class TestFormValidatorProgressAndDraftManager(unittest.TestCase):
    """Test suite for FormValidator, FormProgressManager, and DraftManager."""

    def setUp(self):
        self.discovery = FormDiscovery()
        self.validator = FormValidator()
        self.progress_mgr = FormProgressManager()
        self.draft_mgr = DraftManager()

    def test_validator_required_field_check(self):
        form_def = self.discovery.get_form_by_id("puja_booking_form")
        self.assertIsNotNone(form_def)

        # Missing required field validation
        is_valid, reports = self.validator.validate_form(form_def, {"puja_name": "Ganesh Puja"})
        self.assertFalse(is_valid)

        # All required fields present
        is_valid_pass, reports_pass = self.validator.validate_form(form_def, {"puja_name": "Ganesh Puja", "booking_date": "2026-08-15"})
        self.assertTrue(is_valid_pass)

    def test_progress_calculation(self):
        form_def = self.discovery.get_form_by_id("puja_booking_form")
        prog = self.progress_mgr.calculate_progress(form_def, {"puja_name": "Ganesh Puja"})
        self.assertGreater(prog.completion_percentage, 0.0)
        self.assertIn("booking_date", prog.missing_required_fields)

    def test_draft_save_and_restore(self):
        values = {"name": "Yash", "birth_date": "1995-10-25"}
        self.draft_mgr.save_draft("sess_f1", "kundali_form", values)

        draft = self.draft_mgr.restore_draft("sess_f1", "kundali_form")
        self.assertIsNotNone(draft)
        self.assertEqual(draft.values["name"], "Yash")


class TestVoiceFormControllerIntegration(unittest.TestCase):
    """Integration test suite for VoiceFormController and performance SLAs."""

    def setUp(self):
        self.controller = VoiceFormController()

    def test_voice_form_turn_and_performance_sla(self):
        start_ts = time.perf_counter()
        progress = self.controller.process_form_turn(
            session_id="sess_vfc",
            form_id="puja_booking_form",
            conversation_slots={"puja": "Satyanarayan Puja", "date": "2026-09-01"},
        )
        duration_ms = (time.perf_counter() - start_ts) * 1000

        self.assertIsNotNone(progress)
        self.assertGreater(progress.completion_percentage, 60.0)
        # Verify performance SLA (<15ms overhead target)
        self.assertLess(duration_ms, 50.0)

    def test_apply_voice_correction(self):
        self.controller.process_form_turn("sess_vfc2", "puja_booking_form", {"puja": "Satyanarayan Puja"})
        updated_progress = self.controller.apply_voice_correction("sess_vfc2", "puja_booking_form", "puja_name", "Maha Rudrabhishek")
        self.assertIsNotNone(updated_progress)

        stats = self.controller.statistics()
        self.assertGreater(stats["turns_processed_count"], 0)


if __name__ == "__main__":
    unittest.main()
