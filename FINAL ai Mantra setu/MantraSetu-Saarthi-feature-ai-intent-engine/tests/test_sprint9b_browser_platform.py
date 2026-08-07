"""Unit & Integration Test Suite for Enterprise Browser Intelligence & Computer Use Platform Sprint 9B v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.browser import (
    ApprovalRequest,
    BrowserActionPlan,
    BrowserActionSpec,
    BrowserActionType,
    BrowserDashboard,
    BrowserSafetyManager,
    BrowserState,
    BrowserStateManager,
    BrowserTab,
    BrowserTelemetry,
    DOMAnalysisResult,
    DOMAnalyzer,
    EnterpriseBrowserExecutor,
    EnterpriseBrowserManager,
    EnterpriseBrowserSession,
    PageReasoningEngine,
    ScreenshotValidator,
)


class TestSprint9BBrowserPlatform(unittest.TestCase):
    """Test suite covering Browser Manager, DOM Analyzer, Browser Executor, Page Reasoning, State Manager, Screenshot Validator, Safety Manager, Dashboard, Telemetry, SLA compliance, and Thread Safety."""

    def setUp(self):
        self.manager = EnterpriseBrowserManager()
        self.dom_analyzer = DOMAnalyzer()
        self.executor = EnterpriseBrowserExecutor()
        self.reasoning_engine = PageReasoningEngine()
        self.state_mgr = BrowserStateManager()
        self.validator = ScreenshotValidator()
        self.safety_mgr = BrowserSafetyManager()
        self.dashboard = BrowserDashboard(
            manager=self.manager,
            executor=self.executor,
            dom_analyzer=self.dom_analyzer,
            reasoning_engine=self.reasoning_engine,
            state_mgr=self.state_mgr,
            safety_mgr=self.safety_mgr,
        )
        self.telemetry = BrowserTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 9B modules."""
        modules = [
            self.manager,
            self.dom_analyzer,
            self.executor,
            self.reasoning_engine,
            self.state_mgr,
            self.validator,
            self.safety_mgr,
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

    def test_browser_lifecycle_and_multi_tab_execution(self):
        """Verify browser session start, tab opening, tab switching, navigation, and session termination."""
        sess = self.manager.start_browser_session("user_101", initial_url="https://mantrasetu.com")
        self.assertEqual(sess.user_id, "user_101")
        self.assertEqual(len(sess.tabs), 1)

        # Open tab
        tab2 = self.manager.open_tab(sess.session_id, url="https://mantrasetu.com/booking")
        self.assertIsNotNone(tab2)
        self.assertEqual(len(sess.tabs), 2)

        # Switch tab
        switched = self.manager.switch_tab(sess.session_id, tab2.tab_id)
        self.assertTrue(switched)

        # Navigate
        nav_ok = self.manager.navigate(sess.session_id, "https://mantrasetu.com/pandits")
        self.assertTrue(nav_ok)

        # Close tab
        closed = self.manager.close_tab(sess.session_id, tab2.tab_id)
        self.assertTrue(closed)
        self.assertEqual(len(sess.tabs), 1)

        # Close session
        closed_sess = self.manager.close_session(sess.session_id)
        self.assertTrue(closed_sess)

    def test_dom_analysis_forms_and_accessibility(self):
        """Verify DOM parsing, interactive element discovery, form detection, and accessibility tree."""
        html = "<html><body><form id='puja'><input name='gotra'/><button id='btn'>Book</button></form></body></html>"
        res = self.dom_analyzer.analyze_dom(html, url="https://mantrasetu.com/booking")
        self.assertEqual(res.url, "https://mantrasetu.com/booking")
        self.assertGreater(len(res.interactive_elements), 0)
        self.assertGreater(len(res.discovered_forms), 0)
        self.assertIsNotNone(res.accessibility_tree)

    def test_browser_executor_primitives(self):
        """Verify Click, Type, Select, Upload, Download, Scroll, Hover, and Keyboard Shortcuts."""
        click_res = self.executor.click("#btn_book")
        self.assertTrue(click_res.success)

        type_res = self.executor.type_text("input[name='gotra']", "Bharadwaja")
        self.assertTrue(type_res.success)

        select_res = self.executor.select_option("#pandit_select", "Acharya Ved Prakash")
        self.assertTrue(select_res.success)

        upload_res = self.executor.upload_file("#doc_upload", "/tmp/id_card.pdf")
        self.assertTrue(upload_res.success)

        download_res = self.executor.download_file("https://mantrasetu.com/rec.pdf", "/tmp/rec.pdf")
        self.assertTrue(download_res.success)

        scroll_res = self.executor.scroll(0, 500)
        self.assertTrue(scroll_res.success)

        hover_res = self.executor.hover(".dropdown")
        self.assertTrue(hover_res.success)

        shortcut_res = self.executor.keyboard_shortcut("Control+Enter")
        self.assertTrue(shortcut_res.success)

    def test_page_reasoning_and_action_planning(self):
        """Verify webpage understanding, multi-step action planning, navigation prediction, and completion verification."""
        page_info = self.reasoning_engine.understand_page("DOM Summary", "https://mantrasetu.com/booking")
        self.assertEqual(page_info["recommended_action"], "FILL_FORM_AND_SUBMIT")

        plan = self.reasoning_engine.plan_actions("Book Puja", [], "https://mantrasetu.com/booking")
        self.assertEqual(plan.goal, "Book Puja")
        self.assertGreater(len(plan.planned_steps), 0)

        pred_url = self.reasoning_engine.predict_next_navigation({"action": "CLICK", "selector": "#btn_book"}, "https://mantrasetu.com/booking")
        self.assertIn("confirmation", pred_url)

        ver = self.reasoning_engine.verify_completion("Book Puja", "Confirmation - Puja Booked Successfully")
        self.assertTrue(ver.is_complete)

    def test_browser_state_persistence_and_recovery(self):
        """Verify cookies, local storage, session storage, auth tokens, import/export, and session state recovery."""
        st = self.state_mgr.save_state(
            session_id="sess_101",
            cookies={"session_token": "abc_123"},
            local_storage={"theme": "dark"},
            auth_tokens={"bearer": "jwt_xyz"},
        )
        self.assertEqual(st.session_id, "sess_101")

        loaded = self.state_mgr.load_state("sess_101")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.cookies["session_token"], "abc_123")

        cookies = self.state_mgr.export_cookies("sess_101")
        self.assertEqual(cookies.get("session_token"), "abc_123")

        self.state_mgr.import_cookies("sess_101", {"new_cookie": "val"})
        self.assertIn("new_cookie", self.state_mgr.export_cookies("sess_101"))

        recovered = self.state_mgr.recover_session_state("sess_101")
        self.assertTrue(recovered)

    def test_screenshot_validation_and_visual_diffing(self):
        """Verify screenshot verification, page diff comparison, and UI change confirmation."""
        v_res = self.validator.verify_screenshot(b"current_bytes")
        self.assertTrue(v_res.is_match)

        diff_res = self.validator.compare_pages(b"before_bytes", b"after_bytes")
        self.assertGreater(diff_res.visual_diff_pct, 0.0)

        confirmed = self.validator.confirm_ui_change(b"before_bytes", b"after_bytes", "#btn_submit")
        self.assertTrue(confirmed)

    def test_browser_safety_and_human_approval(self):
        """Verify dangerous action evaluation, domain allowlists, human approval workflow, and CAPTCHA handling."""
        safe_eval = self.safety_mgr.evaluate_action("CLICK_NAV", "https://mantrasetu.com/booking")
        self.assertTrue(safe_eval.is_safe)
        self.assertFalse(safe_eval.requires_human_approval)

        danger_eval = self.safety_mgr.evaluate_action("PAYMENT_EXECUTE", "https://mantrasetu.com/pay")
        self.assertFalse(danger_eval.is_safe)
        self.assertTrue(danger_eval.requires_human_approval)

        req = self.safety_mgr.request_human_approval("PAYMENT", "https://mantrasetu.com/pay", "Confirm $50 payment")
        self.assertEqual(req.status, "PENDING")

        app_ok = self.safety_mgr.approve_request(req.request_id)
        self.assertTrue(app_ok)

        captcha_eval = self.safety_mgr.handle_captcha_escalation("https://mantrasetu.com/captcha")
        self.assertTrue(captcha_eval.captcha_detected)
        self.assertTrue(captcha_eval.requires_human_approval)

    def test_dashboard_aggregation_and_telemetry(self):
        """Verify dashboard summaries and telemetry logging."""
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreater(summary.active_sessions, 0)

        rec = self.telemetry.record_event("ACTION_EVENT", "sess_101", {"action": "CLICK"}, latency_ms=1.1)
        self.assertEqual(rec.session_id, "sess_101")

        recs = self.telemetry.get_records(session_id="sess_101")
        self.assertEqual(len(recs), 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA, sub-5ms DOM SLA, sub-5ms planning SLA, sub-5ms execution SLA."""
        start = time.perf_counter()

        # DOM SLA
        dom_start = time.perf_counter()
        _ = self.dom_analyzer.analyze_dom("<html></html>")
        dom_ms = (time.perf_counter() - dom_start) * 1000.0
        self.assertLess(dom_ms, 5.0)

        # Action Planning SLA
        plan_start = time.perf_counter()
        _ = self.reasoning_engine.plan_actions("Goal", [], "https://mantrasetu.com")
        plan_ms = (time.perf_counter() - plan_start) * 1000.0
        self.assertLess(plan_ms, 5.0)

        # Execution SLA
        exec_start = time.perf_counter()
        _ = self.executor.click("#btn")
        exec_ms = (time.perf_counter() - exec_start) * 1000.0
        self.assertLess(exec_ms, 5.0)

        # Dashboard Summary
        _ = self.dashboard.get_dashboard_summary()

        overall_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(overall_ms, 20.0)

    def test_thread_safety(self):
        """Verify concurrent operations across multiple threads with RLock protection."""
        def worker(idx: int):
            user_id = f"user_{idx}"
            sess = self.manager.start_browser_session(user_id)
            self.executor.click("#btn")
            self.state_mgr.save_state(sess.session_id, cookies={f"cookie_{idx}": "val"})
            self.telemetry.record_event("ACTION_EVENT", sess.session_id, latency_ms=0.5)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(25)]
            for f in futures:
                f.result()

        stats = self.manager.statistics()
        self.assertGreaterEqual(stats["total_sessions_started"], 25)


if __name__ == "__main__":
    unittest.main()
