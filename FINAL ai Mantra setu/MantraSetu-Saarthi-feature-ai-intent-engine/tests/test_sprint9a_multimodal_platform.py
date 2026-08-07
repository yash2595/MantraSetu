"""Unit & Integration Test Suite for Enterprise Multimodal Intelligence Platform Sprint 9A v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.multimodal import (
    ContextModality,
    DocumentType,
    DocumentUnderstanding,
    ModalContextChunk,
    MultimodalContextBuilder,
    MultimodalDashboard,
    MultimodalManager,
    MultimodalProviderRouter,
    MultimodalRequest,
    MultimodalTelemetry,
    OCRManager,
    OCRMode,
    ProviderType,
    VisionInput,
    VisionInputType,
    VisionManager,
)


class TestSprint9AMultimodalPlatform(unittest.TestCase):
    """Test suite covering Vision Manager, OCR Manager, Document Understanding, Context Builder, Provider Router, Multimodal Manager, Dashboard, Telemetry, SLA compliance, and Thread Safety."""

    def setUp(self):
        self.vision_mgr = VisionManager()
        self.ocr_mgr = OCRManager()
        self.doc_understanding = DocumentUnderstanding()
        self.context_builder = MultimodalContextBuilder()
        self.router = MultimodalProviderRouter()
        self.dashboard = MultimodalDashboard(
            vision_mgr=self.vision_mgr,
            ocr_mgr=self.ocr_mgr,
            doc_understanding=self.doc_understanding,
            context_builder=self.context_builder,
            router=self.router,
        )
        self.telemetry = MultimodalTelemetry()
        self.manager = MultimodalManager(
            vision_mgr=self.vision_mgr,
            ocr_mgr=self.ocr_mgr,
            doc_understanding=self.doc_understanding,
            context_builder=self.context_builder,
            router=self.router,
        )

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 9A modules."""
        modules = [
            self.vision_mgr,
            self.ocr_mgr,
            self.doc_understanding,
            self.context_builder,
            self.router,
            self.dashboard,
            self.telemetry,
            self.manager,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertEqual(health.get("status"), "HEALTHY")

    def test_vision_understanding_and_screenshot_analysis(self):
        """Verify image understanding, object detection, UI parsing, diagram and chart analysis."""
        v_inp = VisionInput(source_uri="https://mantrasetu.com/altar.png", input_type=VisionInputType.IMAGE)
        res = self.vision_mgr.analyze_image(v_inp)
        self.assertEqual(res.input_type, VisionInputType.IMAGE)
        self.assertGreater(len(res.detected_objects), 0)
        self.assertGreaterEqual(res.confidence_score, 0.98)

        # Screenshot UI parsing
        ss_res = self.vision_mgr.analyze_screenshot(b"fake_image_bytes", url="/booking")
        self.assertEqual(ss_res.input_type, VisionInputType.SCREENSHOT)
        self.assertGreater(len(ss_res.ui_elements), 0)

        # Diagram & Chart
        diag = self.vision_mgr.interpret_diagram(b"fake_bytes")
        self.assertIn("Flowchart", diag)

        chart = self.vision_mgr.parse_chart(b"fake_bytes")
        self.assertEqual(chart["chart_type"], "BAR_CHART")

    def test_ocr_extraction_and_layout_preservation(self):
        """Verify printed text OCR, handwritten text OCR, bounding boxes, and layout structures."""
        ocr_res = self.ocr_mgr.extract_text(b"fake_doc_bytes", mode=OCRMode.PRINTED)
        self.assertEqual(ocr_res.mode, OCRMode.PRINTED)
        self.assertIn("MantraSetu AgentOS", ocr_res.extracted_text)
        self.assertGreater(len(ocr_res.bounding_boxes), 0)
        self.assertIn("lines_count", ocr_res.layout_structure)

        # Handwritten OCR
        hw_res = self.ocr_mgr.extract_handwritten(b"fake_handwritten_bytes")
        self.assertEqual(hw_res.mode, OCRMode.HANDWRITTEN)
        self.assertIn("Om Namah Shivaya", hw_res.extracted_text)

    def test_document_understanding_multi_format(self):
        """Verify document parsing across PDF, DOCX, PPT, Excel, Markdown, and metadata extraction."""
        pdf_res = self.doc_understanding.parse_pdf(b"%PDF-1.4...")
        self.assertEqual(pdf_res.doc_type, DocumentType.PDF)
        self.assertEqual(len(pdf_res.sections), 2)

        docx_res = self.doc_understanding.parse_docx(b"PK...")
        self.assertEqual(docx_res.doc_type, DocumentType.DOCX)

        ppt_res = self.doc_understanding.parse_ppt(b"PK...")
        self.assertEqual(ppt_res.doc_type, DocumentType.PPT)

        excel_res = self.doc_understanding.parse_excel(b"PK...")
        self.assertEqual(excel_res.doc_type, DocumentType.EXCEL)

        md_res = self.doc_understanding.parse_markdown(b"# Header")
        self.assertEqual(md_res.doc_type, DocumentType.MARKDOWN)

        meta = self.doc_understanding.extract_metadata(b"test content", "test.pdf")
        self.assertEqual(meta["doc_type"], "PDF")

    def test_multimodal_context_fusion(self):
        """Verify cross-modal context fusion, multi-modal prompt synthesis, and context ranking."""
        fused = self.context_builder.fuse_image_and_text("Puja Altar with Sacred Flame", "Book Satyanarayan Puja")
        self.assertEqual(len(fused.chunks), 2)
        self.assertIn("Puja Altar", fused.unified_prompt_representation)

        fused_v_img = self.context_builder.fuse_voice_and_image("Book Puja for Gotra Bharadwaja", {"caption": "Altar"})
        self.assertEqual(len(fused_v_img.chunks), 2)

        fused_doc_mem = self.context_builder.fuse_document_and_memory("Puja Guidelines PDF Text", ["User booked 3 pujas in 2025"])
        self.assertEqual(len(fused_doc_mem.chunks), 2)

    def test_provider_routing_discovery_and_failover(self):
        """Verify vision & OCR provider routing, capability discovery, cost awareness, and automatic failover."""
        v_route = self.router.route_vision(cost_sensitive=False)
        self.assertEqual(v_route.provider_type, ProviderType.VISION)
        self.assertEqual(v_route.selected_provider_id, "vision_default_provider")

        o_route = self.router.route_ocr(cost_sensitive=True)
        self.assertEqual(o_route.selected_provider_id, "ocr_tesseract_local")

        caps = self.router.discover_capabilities()
        self.assertIn("VISION", caps)
        self.assertIn("OCR", caps)

        # Failover
        fb_provider = self.router.trigger_failover("vision_default_provider")
        self.assertEqual(fb_provider, "vision_cost_saver")

    def test_multimodal_manager_orchestration_and_streaming(self):
        """Verify end-to-end multimodal request orchestration and streaming response stages."""
        req = MultimodalRequest(
            vision_input=VisionInput(source_uri="https://mantrasetu.com/altar.png"),
            document_bytes=b"%PDF-1.4...",
            document_name="guide.pdf",
            ocr_image_bytes=b"fake_bytes",
            user_prompt="Explain ritual and document contents",
            memory_facts=["User prefers Hindi pandit"],
        )

        resp = self.manager.process_request(req)
        self.assertIsNotNone(resp.vision_result)
        self.assertIsNotNone(resp.ocr_result)
        self.assertIsNotNone(resp.parsed_doc)
        self.assertIsNotNone(resp.fused_context)
        self.assertIn("Vision:", resp.aggregated_summary)

        # Streaming
        stream_stages = list(self.manager.process_streaming(req))
        self.assertGreater(len(stream_stages), 3)
        self.assertEqual(stream_stages[0]["stage"], "INIT")
        self.assertEqual(stream_stages[-1]["stage"], "COMPLETE")

    def test_dashboard_and_telemetry(self):
        """Verify dashboard summary, reports, and telemetry logging."""
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreater(summary.images_processed, 0)
        self.assertGreaterEqual(summary.ocr_accuracy_pct, 99.0)

        v_rep = self.dashboard.get_vision_report()
        self.assertIn("vision_accuracy_pct", v_rep)

        # Telemetry
        self.telemetry.record_event("VISION_REQUEST", "VISION", {"url": "/test"}, latency_ms=1.5)
        self.telemetry.record_event("PROVIDER_SWITCH", "VISION", {"from": "p1", "to": "p2"}, latency_ms=0.5)

        recs = self.telemetry.get_records(modality="VISION")
        self.assertEqual(len(recs), 2)

        switches = self.telemetry.get_provider_switches()
        self.assertEqual(len(switches), 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA, sub-5ms OCR SLA, sub-3ms vision routing SLA, sub-5ms fusion SLA."""
        start = time.perf_counter()

        # OCR SLA
        ocr_start = time.perf_counter()
        _ = self.ocr_mgr.extract_text(b"fake_bytes")
        ocr_ms = (time.perf_counter() - ocr_start) * 1000.0
        self.assertLess(ocr_ms, 5.0)

        # Vision Routing SLA
        vroute_start = time.perf_counter()
        _ = self.router.route_vision()
        vroute_ms = (time.perf_counter() - vroute_start) * 1000.0
        self.assertLess(vroute_ms, 3.0)

        # Fusion SLA
        fuse_start = time.perf_counter()
        _ = self.context_builder.fuse_image_and_text("Caption", "Prompt")
        fuse_ms = (time.perf_counter() - fuse_start) * 1000.0
        self.assertLess(fuse_ms, 5.0)

        # Dashboard Summary
        _ = self.dashboard.get_dashboard_summary()

        overall_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(overall_ms, 20.0)

    def test_thread_safety(self):
        """Verify concurrent operations across multiple threads with RLock protection."""
        def worker(idx: int):
            v_inp = VisionInput(source_uri=f"https://test.com/{idx}.png")
            req = MultimodalRequest(vision_input=v_inp, user_prompt=f"Prompt {idx}")
            resp = self.manager.process_request(req)
            self.assertIsNotNone(resp.vision_result)
            self.telemetry.record_event("VISION_REQUEST", "VISION", latency_ms=0.5)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(25)]
            for f in futures:
                f.result()

        stats = self.manager.statistics()
        self.assertGreaterEqual(stats["total_requests_processed"], 25)


if __name__ == "__main__":
    unittest.main()
