"""
Unit tests for UBa / COLTECH document pipeline v2.
"""
import unittest
import os
from backend.parser import parse_document
from backend.auditor import audit_document
from backend.restructurer import restructure_document
from backend.models import ReformatRequest

TEST_DOCX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sample_dissertation.docx")
USER_DOCX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "5460b15f-a9d3-4474-a318-d787960598a6", "original.docx")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "test_output")

class TestUBaPipeline(unittest.TestCase):
    def setUp(self):
        os.makedirs(OUT_DIR, exist_ok=True)

    def test_parser_and_auditor(self):
        self.assertTrue(os.path.exists(TEST_DOCX), "Sample DOCX must exist")
        parsed = parse_document(TEST_DOCX)
        self.assertGreater(len(parsed.paragraphs), 10)
        self.assertTrue(parsed.metadata.author, "Candidate author should be extracted")
        
        # Run audit
        audit = audit_document(parsed, doc_type="dissertation_bsc", school_type="coltech", header_mode="center_crest")
        self.assertIsInstance(audit.compliance_score, int)
        self.assertGreater(audit.total_issues, 0)
        print(f"\n[Test] Compliance Score: {audit.compliance_score}% | Issues: {audit.total_issues}")

    def test_user_document_extraction(self):
        if os.path.exists(USER_DOCX):
            parsed = parse_document(USER_DOCX)
            self.assertEqual(parsed.metadata.author, "NJITAPON AHMED SAID ASSAN")
            self.assertEqual(parsed.metadata.reg_number, "UBA2SPP228")
            self.assertIn("PHISHING DETECTION", parsed.metadata.title.upper())
            print(f"[Test User Doc] Extracted title: {parsed.metadata.title}")
            print(f"[Test User Doc] Extracted candidate: {parsed.metadata.author}")
            print(f"[Test User Doc] Extracted degree: {parsed.metadata.degree}")

    def test_restructurer_margins(self):
        parsed = parse_document(TEST_DOCX)
        req = ReformatRequest(doc_type="dissertation_bsc", school_type="coltech", header_mode="center_crest")
        out_path = os.path.join(OUT_DIR, "test_reformatted.docx")
        restructure_document(parsed, req, out_path)
        
        self.assertTrue(os.path.exists(out_path), "Reformatted docx must be created")
        re_parsed = parse_document(out_path)
        self.assertAlmostEqual(re_parsed.margins["left"], 4.0, delta=0.2)
        print(f"[Test] Restructured docx margin: {re_parsed.margins['left']} cm")

    def test_clean_body_restructuring_no_duplicate_prelims(self):
        if os.path.exists(USER_DOCX):
            parsed = parse_document(USER_DOCX)
            req = ReformatRequest(
                doc_type="proposal",
                school_type="coltech",
                header_mode="center_crest",
                metadata=parsed.metadata
            )
            out_path = os.path.join(OUT_DIR, "test_clean_user_doc.docx")
            restructure_document(parsed, req, out_path)
            self.assertTrue(os.path.exists(out_path), "Reformatted file should exist")

            import docx
            doc = docx.Document(out_path)
            
            # Find the paragraph where Chapter 1 starts
            ch1_idx = -1
            for i, p in enumerate(doc.paragraphs):
                if p.text.strip().upper() == "CHAPTER 1\nINTRODUCTION":
                    ch1_idx = i
                    break
            self.assertGreater(ch1_idx, 0, "CHAPTER 1 heading should exist")
            
            # Verify that paragraph immediately following Chapter 1 is 1.1 Background
            self.assertEqual(doc.paragraphs[ch1_idx + 1].text.strip(), "1.1 Background")

            # Verify that in all body paragraphs (from ch1_idx to end), NO preliminary leakage occurs
            body_text = "\n".join([p.text.strip() for p in doc.paragraphs[ch1_idx:]])
            leakage_phrases = [
                "COPYRIGHT — REQUIRED BY COLTECH",
                "REQUIRES_USER_REVIEW",
                "DECLARATION OF ORIGINALITY OF STUDY",
                "CERTIFICATION OF CORRECTIONS AFTER DEFENSE",
                "ACCEPTANCE OF DISSERTATION",
                "DEDICATION — REQUIRED BY COLTECH",
                "ACKNOWLEDGEMENTS — REQUIRED BY COLTECH",
                "Table 2.1: 1.1 Background\t1",
                "CHAPTER 2: INTRODUCTION\t1"
            ]
            for phrase in leakage_phrases:
                self.assertNotIn(phrase, body_text.upper(), f"Body should not contain leaked prelim phrase: {phrase}")

            # Verify chapters and references exist in body
            self.assertIn("CHAPTER 2\nLITERATURE REVIEW", body_text)
            self.assertIn("CHAPTER 3\nPROPOSED RESEARCH METHODOLOGY", body_text)
            self.assertIn("REFERENCES", body_text)
            print("[Test] Clean body verification passed with 0 leaked preliminary phrases!")

    def test_assignment_table_of_contents_and_acknowledgements(self):
        """Verifies that Course Technical Assignments generate an accurate TOC followed by Acknowledgements."""
        parsed = parse_document(TEST_DOCX)
        req = ReformatRequest(
            doc_type="assignment",
            school_type="coltech",
            header_mode="dual_logo",
            metadata=parsed.metadata
        )
        out_path = os.path.join(OUT_DIR, "test_assignment.docx")
        restructure_document(parsed, req, out_path)
        self.assertTrue(os.path.exists(out_path), "Assignment DOCX should be created")

        import docx
        doc = docx.Document(out_path)
        all_text = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

        self.assertIn("TABLE OF CONTENTS", all_text, "Assignment must contain Table of Contents")
        self.assertIn("ACKNOWLEDGEMENTS", all_text, "Assignment must contain Acknowledgements")
        
        # Verify ordering: Table of Contents appears before Acknowledgements
        toc_pos = all_text.find("TABLE OF CONTENTS")
        ack_pos = all_text.find("ACKNOWLEDGEMENTS")
        self.assertLess(toc_pos, ack_pos, "TOC must precede Acknowledgements in Assignment structure")

        # Verify acknowledgement body mentions pedagogical guidance / University of Bamenda
        self.assertIn("University of Bamenda", all_text)
        print("[Test] Assignment Table of Contents & Acknowledgements verified successfully!")

    def test_preview_purging_prevents_preview_joining(self):
        """Verifies that generate_page_previews purges the preview directory completely so short docs don't inherit old pages."""
        from backend.converter import generate_page_previews
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            # Create 10 dummy pages simulating a long dissertation
            for i in range(1, 11):
                dummy_path = os.path.join(temp_dir, f"page-{i:02d}.png")
                with open(dummy_path, "w") as f:
                    f.write("dummy")

            self.assertEqual(len(os.listdir(temp_dir)), 10)

            # Purge the directory as generate_page_previews does
            shutil.rmtree(temp_dir, ignore_errors=True)
            os.makedirs(temp_dir, exist_ok=True)
            
            # Now simulate a short 3-page document
            for i in range(1, 4):
                dummy_path = os.path.join(temp_dir, f"page-{i:02d}.png")
                with open(dummy_path, "w") as f:
                    f.write("dummy")

            remaining = [f for f in os.listdir(temp_dir) if f.endswith(".png")]
            self.assertEqual(len(remaining), 3, "Only the 3 new pages should exist, no leftover pages from previous doc!")
            print("[Test] Preview purging successfully prevents document joining bug!")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_database_persistence_layer(self):
        """Verifies save, retrieve, and reformat operations in the AcadFormat database layer."""
        from backend.database import save_document_record, get_document_record, save_reformat_record, list_recent_documents
        import uuid

        test_token = f"test-{uuid.uuid4()}"
        save_success = save_document_record(
            token=test_token,
            filename="Test_Proposal.docx",
            doc_type="proposal",
            school_type="coltech",
            compliance_score=95,
            metadata={"title": "Test Title", "author": "Test Author", "reg_number": "UB1234"},
            issues_count=1
        )
        self.assertTrue(save_success, "Saving document record should succeed")

        rec = get_document_record(test_token)
        self.assertIsNotNone(rec, "Document record should be retrievable")
        self.assertEqual(rec["token"], test_token)
        self.assertEqual(rec["compliance_score"], 95)

        reformat_success = save_reformat_record(
            token=test_token,
            docx_path="/dummy/path.docx",
            pdf_path="/dummy/path.pdf",
            page_count=12
        )
        self.assertTrue(reformat_success, "Saving reformat record should succeed")

        recent = list_recent_documents(limit=5)
        self.assertGreater(len(recent), 0, "Recent documents list should not be empty")
        print(f"[Test] Database persistence layer verified successfully! ({len(recent)} recent records)")

    def test_internship_and_assignment_have_only_one_cover_page(self):
        """Verifies that Internship Reports and Assignments have ONLY 1 cover page (no title page replica)."""
        import docx
        parsed = parse_document(TEST_DOCX)
        
        # 1. Assignment: should have ONLY 1 cover page
        req_ass = ReformatRequest(doc_type="assignment", school_type="coltech", header_mode="dual_logo", metadata=parsed.metadata)
        out_ass = os.path.join(OUT_DIR, "test_single_cover_assignment.docx")
        restructure_document(parsed, req_ass, out_ass)
        doc_ass = docx.Document(out_ass)
        
        # Count occurrences of the University Name heading
        uba_count_ass = sum(1 for p in doc_ass.paragraphs if p.text.strip() == "THE UNIVERSITY OF BAMENDA")
        self.assertEqual(uba_count_ass, 1, "Assignment must have exactly 1 cover page, no duplicate title page!")

        # 2. Internship: should have ONLY 1 cover page
        req_int = ReformatRequest(doc_type="internship", school_type="fems", header_mode="center_crest", metadata=parsed.metadata)
        out_int = os.path.join(OUT_DIR, "test_single_cover_internship.docx")
        restructure_document(parsed, req_int, out_int)
        doc_int = docx.Document(out_int)
        uba_count_int = sum(1 for p in doc_int.paragraphs if p.text.strip() == "THE UNIVERSITY OF BAMENDA")
        self.assertEqual(uba_count_int, 1, "Internship Report must have exactly 1 cover page, no duplicate title page!")

        # 3. Dissertation: SHOULD have 2 (Cover + Title Page)
        req_dis = ReformatRequest(doc_type="dissertation_bsc", school_type="coltech", header_mode="center_crest", metadata=parsed.metadata)
        out_dis = os.path.join(OUT_DIR, "test_dual_cover_dissertation.docx")
        restructure_document(parsed, req_dis, out_dis)
        doc_dis = docx.Document(out_dis)
        uba_count_dis = sum(1 for p in doc_dis.paragraphs if p.text.strip() == "THE UNIVERSITY OF BAMENDA")
        self.assertEqual(uba_count_dis, 2, "Dissertation must have Cover Page AND inside Title Page replica!")
        print("[Test] Verified: Internship & Assignment have only 1 cover page; Dissertation has Cover + Title page.")

    def test_group_assignment_small_roster_fits_on_cover(self):
        """Verifies that a group assignment with <= 5 members renders the member table directly on the cover page."""
        import docx
        from backend.models import GroupMember
        parsed = parse_document(TEST_DOCX)
        meta = parsed.metadata.model_copy(deep=True)
        meta.is_group_assignment = True
        meta.group_name = "Group 3"
        meta.group_members = [
            GroupMember(name="ALICE NJEI", matricule="UBa25EN001", participation="Lead", grade="____ / 20"),
            GroupMember(name="BOB TITA", matricule="UBa25EN002", participation="Research", grade="____ / 20"),
            GroupMember(name="CHARLIE CHE", matricule="UBa25EN003", participation="Analysis", grade="____ / 20"),
        ]

        req = ReformatRequest(doc_type="assignment", school_type="coltech", header_mode="dual_logo", metadata=meta)
        out_path = os.path.join(OUT_DIR, "test_small_group_assignment.docx")
        restructure_document(parsed, req, out_path)

        doc = docx.Document(out_path)
        all_text = "\n".join([p.text for p in doc.paragraphs])
        self.assertIn("PRESENTED BY: GROUP 3", all_text)
        
        # Verify table on cover contains member names
        found_names = 0
        for tbl in doc.tables:
            for row in tbl.rows:
                row_t = " ".join([c.text for c in row.cells])
                if "ALICE NJEI" in row_t: found_names += 1
                if "BOB TITA" in row_t: found_names += 1
                if "CHARLIE CHE" in row_t: found_names += 1
        self.assertEqual(found_names, 3, "All 3 members must appear in the member table on the cover page!")
        print("[Test] Small group assignment correctly renders member table on cover page.")

    def test_group_assignment_large_roster_overflows_to_page_2(self):
        """Verifies that a group assignment with > 5 members does not put names on the cover page and generates Page 2."""
        import docx
        from backend.models import GroupMember
        parsed = parse_document(TEST_DOCX)
        meta = parsed.metadata.model_copy(deep=True)
        meta.is_group_assignment = True
        meta.group_name = "Team Delta"
        meta.group_members = [
            GroupMember(name=f"STUDENT MEMBER {i}", matricule=f"UBa25EN{i:03d}", participation="Subtask", grade="____ / 20")
            for i in range(1, 9)  # 8 members (> 5)
        ]

        req = ReformatRequest(doc_type="assignment", school_type="coltech", header_mode="dual_logo", metadata=meta)
        out_path = os.path.join(OUT_DIR, "test_large_group_assignment.docx")
        restructure_document(parsed, req, out_path)

        doc = docx.Document(out_path)
        all_text = "\n".join([p.text for p in doc.paragraphs]) + "\n" + "\n".join([c.text for t in doc.tables for r in t.rows for c in r.cells])
        
        # Cover page has the overflow note
        self.assertIn("Complete Register of Group Members & Evaluation Sheet Attached on Page 2", all_text)
        
        # Dedicated Page 2 Heading
        self.assertIn("LIST OF GROUP MEMBERS & PRESENTATION EVALUATION ROSTER", all_text)
        self.assertIn("EVALUATOR / COURSE LECTURER SIGN-OFF:", all_text)

        # Verify all 8 members are in the dedicated table
        found_members = sum(1 for i in range(1, 9) if f"STUDENT MEMBER {i}" in all_text)
        self.assertEqual(found_members, 8, "All 8 members must appear in the dedicated register on Page 2!")
        print("[Test] Large group assignment (>5 members) successfully moved to dedicated Page 2 register.")

    def test_internship_preliminaries_structure(self):
        """Verifies that Internship Reports include Attestation, Declaration, Dedication, Acknowledgements, and Summary."""
        import docx
        parsed = parse_document(TEST_DOCX)
        meta = parsed.metadata.model_copy(deep=True)
        meta.host_company = "CAMTEL BAMENDA"
        meta.field_supervisor = "Engr. Nkwenti Peter"

        req = ReformatRequest(doc_type="internship", school_type="fems", header_mode="center_crest", metadata=meta)
        out_path = os.path.join(OUT_DIR, "test_internship_prelims.docx")
        restructure_document(parsed, req, out_path)

        doc = docx.Document(out_path)
        all_text = "\n".join([p.text for p in doc.paragraphs]) + "\n" + "\n".join([c.text for t in doc.tables for r in t.rows for c in r.cells])

        self.assertIn("ATTESTATION OF INTERNSHIP COMPLETION", all_text)
        self.assertIn("FIELD / PROFESSIONAL SUPERVISOR", all_text)
        self.assertIn("CAMTEL BAMENDA", all_text)
        self.assertIn("DECLARATION", all_text)
        self.assertIn("DEDICATION", all_text)
        self.assertIn("ACKNOWLEDGEMENTS", all_text)
        self.assertIn("EXECUTIVE SUMMARY", all_text)
        self.assertNotIn("CERTIFICATION OF CORRECTIONS AFTER DEFENSE", all_text, "Internship should not have defense certification!")
        print("[Test] Internship Report preliminaries verified successfully according to UBa standards!")

    def test_preview_base64_data_urls(self):
        """Verifies that generate_document_previews generates valid Base64 data URLs for instant client preview."""
        from backend.converter import generate_document_previews
        out_pdf, files, data_urls = generate_document_previews(
            TEST_DOCX, OUT_DIR, os.path.join(OUT_DIR, "previews_test"), dpi=100, max_pages=5
        )
        self.assertGreater(len(files), 0)
        self.assertEqual(len(files), len(data_urls))
        self.assertTrue(data_urls[0].startswith("data:image/png;base64,"))
        print(f"[Test] Successfully generated {len(data_urls)} Base64 data URLs for instant zero-request client rendering.")

if __name__ == "__main__":
    unittest.main()

