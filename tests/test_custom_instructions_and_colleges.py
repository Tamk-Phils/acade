"""
Unit tests for HTTTC vs HTTC differentiation and custom editing/formatting instructions.
"""
import unittest
import os
import docx
from backend.academic_data import UBA_ESTABLISHMENTS, ALL_ESTABLISHMENTS
from backend.models import DocumentMetadata, ReformatRequest
from backend.restructurer import parse_custom_formatting_rules, restructure_document
from backend.auditor import audit_document
from backend.parser import parse_document
from backend.chatbot import generate_chat_response

TEST_DOCX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sample_dissertation.docx")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "test_output")

class TestCustomInstructionsAndColleges(unittest.TestCase):
    def setUp(self):
        os.makedirs(OUT_DIR, exist_ok=True)

    def test_htttc_vs_httc_differentiation(self):
        """Verify HTTTC (ENSET) and HTTC (ENS) are distinct institutions with proper degrees."""
        self.assertIn("htttc", UBA_ESTABLISHMENTS)
        self.assertIn("httc", UBA_ESTABLISHMENTS)

        htttc = UBA_ESTABLISHMENTS["htttc"]
        httc = UBA_ESTABLISHMENTS["httc"]

        # Codes and names
        self.assertEqual(htttc["code"], "HTTTC")
        self.assertIn("TECHNICAL", htttc["name_en"].upper())
        self.assertIn("ENSET", htttc["name_en"].upper())

        self.assertEqual(httc["code"], "HTTC")
        self.assertNotIn("TECHNICAL", httc["name_en"].upper())
        self.assertIn("ENS", httc["name_en"].upper())

        # Technical teacher degrees vs general teacher degrees
        self.assertIn("DIPET I", htttc["degrees"])
        self.assertIn("DIPET II", htttc["degrees"])
        self.assertIn("DIPES I", httc["degrees"])
        self.assertIn("DIPES II", httc["degrees"])

        # Backward compatibility alias
        self.assertIn("ens", ALL_ESTABLISHMENTS)
        self.assertEqual(ALL_ESTABLISHMENTS["ens"]["code"], "ENS")
        self.assertEqual(ALL_ESTABLISHMENTS["httc"]["code"], "HTTC")
        self.assertEqual(ALL_ESTABLISHMENTS["ens"]["name_en"], ALL_ESTABLISHMENTS["httc"]["name_en"])

    def test_parse_custom_formatting_rules(self):
        """Test extraction of custom rules from natural language instructions and metadata overrides."""
        # 1. Custom font and size
        meta1 = DocumentMetadata(
            title="TEST MANUSCRIPT",
            author="TEST AUTHOR",
            custom_instructions="Please use Arial 11pt with 1.15 line spacing, 2.5cm margins and unboxed title."
        )
        rules1 = parse_custom_formatting_rules(meta1)
        self.assertEqual(rules1.font_family, "Arial")
        self.assertEqual(rules1.font_size_pt, 11.0)
        self.assertEqual(rules1.line_spacing, 1.15)
        self.assertAlmostEqual(rules1.margin_left_cm, 2.5, places=1)
        self.assertAlmostEqual(rules1.margin_right_cm, 2.5, places=1)
        self.assertFalse(rules1.box_title)

        # 2. 1 inch margins and single spacing
        meta2 = DocumentMetadata(
            title="TEST 2",
            author="TEST AUTHOR",
            custom_instructions="Use 1 inch margins, single line spacing, and Calibri font."
        )
        rules2 = parse_custom_formatting_rules(meta2)
        self.assertEqual(rules2.font_family, "Calibri")
        self.assertEqual(rules2.line_spacing, 1.0)
        self.assertAlmostEqual(rules2.margin_left_cm, 2.54, places=2)

        # 3. Direct overrides on ReformatRequest
        req3 = ReformatRequest(
            doc_type="dissertation_bsc",
            school_type="coltech",
            header_mode="center_crest",
            font_family="Georgia",
            font_size_pt=10.5,
            line_spacing=2.0,
            box_title=False
        )
        rules3 = parse_custom_formatting_rules(req=req3)
        self.assertEqual(rules3.font_family, "Georgia")
        self.assertEqual(rules3.font_size_pt, 10.5)
        self.assertEqual(rules3.line_spacing, 2.0)
        self.assertFalse(rules3.box_title)

    def test_auditor_acknowledges_custom_instructions(self):
        """Test that auditor reports custom instructions as active rules."""
        if not os.path.exists(TEST_DOCX):
            return
        parsed = parse_document(TEST_DOCX)
        custom_inst = "Use Arial 11pt, 1.15 line spacing, and 2.5cm margins."
        audit_res = audit_document(
            parsed,
            doc_type="dissertation_bsc",
            school_type="htttc",
            header_mode="center_crest",
            custom_instructions=custom_inst
        )
        # Check issues include custom instructions info
        custom_issues = [i for i in audit_res.issues if "custom-instructions" in i.id or "Custom" in i.message]
        self.assertGreater(len(custom_issues), 0)
        self.assertIn("Active", custom_issues[0].message)

    def test_restructurer_with_custom_instructions(self):
        """Test generating a document with non-standard custom instructions."""
        if not os.path.exists(TEST_DOCX):
            return
        parsed = parse_document(TEST_DOCX)
        custom_inst = "Use Arial 11pt font, 1.15 line spacing, 2.5cm margins, and do not put title in a box."
        req = ReformatRequest(
            doc_type="dissertation_bsc",
            school_type="htttc",
            header_mode="center_crest",
            custom_instructions=custom_inst,
            metadata=parsed.metadata
        )
        out_path = os.path.join(OUT_DIR, "test_custom_formatted.docx")
        restructure_document(parsed, req, out_path)

        self.assertTrue(os.path.exists(out_path))
        doc = docx.Document(out_path)

        # Margin check: First section margin should be ~2.5cm (not 4.0cm standard)
        section = doc.sections[0]
        left_cm = section.left_margin.cm
        self.assertAlmostEqual(left_cm, 2.5, places=1)

        # Body paragraph font check
        found_arial = False
        for p in doc.paragraphs:
            for run in p.runs:
                if run.font.name == "Arial":
                    found_arial = True
                    break
            if found_arial:
                break
        self.assertTrue(found_arial, "Reformatted document should have Arial font runs")

    def test_chatbot_college_differentiation_and_custom_rules(self):
        """Verify the chatbot correctly distinguishes HTTTC vs HTTC and handles custom instructions."""
        # 1. HTTTC vs HTTC query
        resp_htttc = generate_chat_response("Tell me about HTTTC vs HTTC", school_type="htttc")
        self.assertIn("ENSET", resp_htttc["reply"].upper())

        # 2. Natural language custom formatting command
        resp_cmd = generate_chat_response(
            "Please format my document using Arial 11pt, 1.15 line spacing, and 2.5cm margins",
            school_type="coltech"
        )
        self.assertIsNotNone(resp_cmd.get("applied_changes"))
        self.assertIn("custom_instructions", resp_cmd["applied_changes"])
        self.assertEqual(resp_cmd["applied_changes"].get("font_family"), "Arial")
        self.assertEqual(resp_cmd["applied_changes"].get("font_size_pt"), 11.0)
        self.assertEqual(resp_cmd["applied_changes"].get("line_spacing"), 1.15)


if __name__ == "__main__":
    unittest.main()
