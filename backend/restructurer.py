"""
Restructuring Engine for The University of Bamenda (UBa) and College of Technology (COLTECH).
Generates compliant DOCX manuscripts conforming to official Senate and Establishment regulations.
"""
import os
import re
import io
import copy
from typing import List, Dict, Any, Optional
import docx
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
from backend.models import DocumentMetadata, ReformatRequest, GroupMember
from backend.parser import ParsedDocument
from backend.academic_data import UBA_ESTABLISHMENTS, resolve_department_and_option

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
UBA_LOGO_PATH = os.path.join(ASSETS_DIR, "uba_logo.png")
COLTECH_LOGO_PATH = os.path.join(ASSETS_DIR, "coltech_logo.png")

INTRO_HEADING_PATTERN = re.compile(
    r'^(?:(?:1(?:\.[01])?\.?\s*)?(?:GENERAL\s+)?INTRODUCTION|CHAPTER\s+1\s*[:\-–—]?\s*(?:GENERAL\s+)?INTRODUCTION)\s*[:.\-]?$',
    re.IGNORECASE
)

class CustomFormattingRules:
    """Holds parsed custom formatting rules that deviate from standard Senate guidelines."""
    def __init__(self):
        self.font_name: str = "Times New Roman"
        self.font_size_pt: float = 12.0
        self.heading1_size_pt: float = 14.0
        self.heading2_size_pt: float = 12.0
        self.line_spacing: float = 1.5
        self.margin_left_cm: float = 4.0
        self.margin_right_cm: float = 2.0
        self.margin_top_cm: float = 2.0
        self.margin_bottom_cm: float = 2.0
        self.box_title: bool = True
        self.alignment: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.JUSTIFY
        self.auto_label_unlabeled_figures: bool = True
        self.has_custom_overrides: bool = False

    @property
    def font_family(self) -> str:
        return self.font_name

    @font_family.setter
    def font_family(self, val: str):
        self.font_name = val

def parse_custom_formatting_rules(meta: Optional[DocumentMetadata] = None, req: Optional[ReformatRequest] = None) -> CustomFormattingRules:
    """
    Parses custom editing instructions and explicit overrides to support
    non-standard user formatting specifications (e.g. Arial 11pt, 2.5cm margins, unboxed title).
    """
    rules = CustomFormattingRules()

    # 1. Check direct properties on req or meta
    for src in [meta, req]:
        if not src:
            continue
        if getattr(src, "font_family", None):
            rules.font_name = src.font_family.strip()
            rules.has_custom_overrides = True
        if getattr(src, "font_size_pt", None) and src.font_size_pt > 0:
            rules.font_size_pt = float(src.font_size_pt)
            rules.heading1_size_pt = rules.font_size_pt + 2.0
            rules.heading2_size_pt = rules.font_size_pt
            rules.has_custom_overrides = True
        if getattr(src, "line_spacing", None) and src.line_spacing > 0:
            rules.line_spacing = float(src.line_spacing)
            rules.has_custom_overrides = True
        if getattr(src, "margin_left_cm", None) and src.margin_left_cm > 0:
            rules.margin_left_cm = float(src.margin_left_cm)
            rules.has_custom_overrides = True
        if getattr(src, "margin_right_cm", None) and src.margin_right_cm > 0:
            rules.margin_right_cm = float(src.margin_right_cm)
            rules.has_custom_overrides = True
        if getattr(src, "margin_top_cm", None) and src.margin_top_cm > 0:
            rules.margin_top_cm = float(src.margin_top_cm)
            rules.has_custom_overrides = True
        if getattr(src, "margin_bottom_cm", None) and src.margin_bottom_cm > 0:
            rules.margin_bottom_cm = float(src.margin_bottom_cm)
            rules.has_custom_overrides = True
        if getattr(src, "box_title", None) is not None:
            rules.box_title = bool(src.box_title)
            rules.has_custom_overrides = True

    # 2. Parse natural language instructions from custom_instructions
    instructions = ""
    if req and getattr(req, "custom_instructions", None):
        instructions += " " + str(req.custom_instructions)
    if meta and getattr(meta, "custom_instructions", None):
        instructions += " " + str(meta.custom_instructions)

    instructions = instructions.strip()
    if instructions:
        low = instructions.lower()
        rules.has_custom_overrides = True

        # Font family parsing
        font_map = {
            "arial": "Arial",
            "calibri": "Calibri",
            "georgia": "Georgia",
            "cambria": "Cambria",
            "helvetica": "Helvetica",
            "verdana": "Verdana",
            "garamond": "Garamond",
            "palatino": "Palatino Linotype",
            "trebuchet": "Trebuchet MS",
            "courier": "Courier New",
            "times new roman": "Times New Roman"
        }
        for k, v in font_map.items():
            if re.search(rf'\b{k}\b', low):
                rules.font_name = v
                break

        # Font size parsing (e.g. 10pt, 11pt, 12pt, 11 pt)
        fsize_m = re.search(r'\b(9|10|10\.5|11|11\.5|12|13|14)\s*(?:pt|points?)\b', low)
        if fsize_m:
            rules.font_size_pt = float(fsize_m.group(1))
            rules.heading1_size_pt = rules.font_size_pt + 2.0
            rules.heading2_size_pt = rules.font_size_pt

        # Line spacing parsing (e.g. single spacing, 1.15, 1.5, double spacing)
        if re.search(r'\b(single(?:\s+spaced?|\s+line)?|1\.0(?:\s+spacing)?)\b', low):
            rules.line_spacing = 1.0
        elif re.search(r'\b(1\.15(?:\s+spaced?|\s+line)?)\b', low):
            rules.line_spacing = 1.15
        elif re.search(r'\b(double(?:\s+spaced?|\s+line)?|2\.0(?:\s+spacing)?)\b', low):
            rules.line_spacing = 2.0
        elif re.search(r'\b(1\.5(?:\s+spaced?|\s+line)?)\b', low):
            rules.line_spacing = 1.5
        else:
            lsp_m = re.search(r'\bspacing\s*(?:of|is|to|=)?\s*(\d(?:\.\d+)?)\b', low)
            if lsp_m:
                rules.line_spacing = float(lsp_m.group(1))

        # Margin parsing
        if re.search(r'\b(1\s*inch|2\.54\s*cm|2\.5\s*cm|normal\s+margins?|standard\s+margins?)\b', low):
            rules.margin_left_cm = 2.54
            rules.margin_right_cm = 2.54
            rules.margin_top_cm = 2.54
            rules.margin_bottom_cm = 2.54
        elif re.search(r'\b4(?:\.0)?\s*cm\s*(?:binding|left)?\s*margin\b', low):
            rules.margin_left_cm = 4.0

        # Specific margin side parsing
        m_all = re.search(r'\b(\d+(?:\.\d+)?)\s*cm\s*(?:margins?|all\s+around|on\s+all\s+sides)\b', low)
        if m_all:
            val = float(m_all.group(1))
            rules.margin_left_cm = val
            rules.margin_right_cm = val
            rules.margin_top_cm = val
            rules.margin_bottom_cm = val

        m_left = re.search(r'\b(?:left\s+margin|margin\s+left)\s*(?:of|is|to|=)?\s*(\d+(?:\.\d+)?)\s*(?:cm)?\b', low)
        if m_left:
            rules.margin_left_cm = float(m_left.group(1))
        m_right = re.search(r'\b(?:right\s+margin|margin\s+right)\s*(?:of|is|to|=)?\s*(\d+(?:\.\d+)?)\s*(?:cm)?\b', low)
        if m_right:
            rules.margin_right_cm = float(m_right.group(1))
        m_top = re.search(r'\b(?:top\s+margin|margin\s+top)\s*(?:of|is|to|=)?\s*(\d+(?:\.\d+)?)\s*(?:cm)?\b', low)
        if m_top:
            rules.margin_top_cm = float(m_top.group(1))
        m_bottom = re.search(r'\b(?:bottom\s+margin|margin\s+bottom)\s*(?:of|is|to|=)?\s*(\d+(?:\.\d+)?)\s*(?:cm)?\b', low)
        if m_bottom:
            rules.margin_bottom_cm = float(m_bottom.group(1))

        # Boxed title parsing
        if re.search(r'\b(no\s+box(?:ed)?|remove\s+box|without\s+box|unboxed|no\s+border)\b', low):
            rules.box_title = False
        elif re.search(r'\b(box(?:ed)?\s+title|with\s+box|border\s+around\s+title)\b', low):
            rules.box_title = True

        # Alignment parsing
        if re.search(r'\b(left\s+align(?:ed)?|align\s+left)\b', low):
            rules.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif re.search(r'\b(justif(?:ied|y))\b', low):
            rules.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        # Figure labeling acceptance / rejection parsing
        if re.search(r'\b(do not label|dont label|no figure labels?|keep original figures?|without figure labels?)\b', low):
            rules.auto_label_unlabeled_figures = False
        elif re.search(r'\b(apply proposed (?:figure )?labels?|label figures?)\b', low):
            rules.auto_label_unlabeled_figures = True

    return rules

def set_cell_margins(cell, top=60, bottom=60, left=60, right=60):
    """Set zero or tight margins for header table cells."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_background(cell, hex_color: str):
    """Sets background shading of a docx table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def add_boxed_title(doc: docx.Document, title_text: str, font_name: str = "Times New Roman"):
    """
    Renders the document title inside a clean rectangular single-line border box,
    centered horizontally with appropriate internal padding.
    """
    tbl_box = doc.add_table(rows=1, cols=1)
    tbl_box.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_box.autofit = False
    cell = tbl_box.rows[0].cells[0]
    cell.width = Cm(15.0)
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)

    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        r'<w:tcBorders %s>'
        r'  <w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        r'  <w:left w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        r'  <w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        r'  <w:right w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
        r'</w:tcBorders>' % nsdecls('w')
    )
    tcPr.append(tcBorders)

    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.2
    r = p.add_run(title_text.upper())
    r.font.name = font_name
    r.font.size = Pt(13)
    r.font.bold = True

def add_header_banner(doc: docx.Document, meta: DocumentMetadata, doc_type: str = "dissertation_bsc", header_mode: str = "center_crest"):
    """
    Builds the official University of Bamenda header.
    - If header_mode == 'dual_logo' or doc_type == 'assignment':
        Renders Dual Logos (UBa on left, College/Assignment on right).
    - If header_mode == 'center_crest' (Official standard for dissertations, theses, proposals, projects):
        Renders the official UBa crest in the center flanked by the School/College on the left and Department on the right.
    """
    # 1. Top University Header
    univ_name = "THE UNIVERSITY OF BAMENDA"
    if "CATUC" in meta.faculty_code.upper() or "CATHOLIC" in (meta.faculty or "").upper():
        univ_name = "CATHOLIC UNIVERSITY OF CAMEROON, BAMENDA"

    p_u = doc.add_paragraph()
    p_u.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_u.paragraph_format.space_before = Pt(0)
    p_u.paragraph_format.space_after = Pt(6)
    r_u = p_u.add_run(univ_name)
    r_u.font.name = "Times New Roman"
    r_u.font.size = Pt(16)
    r_u.font.bold = True

    resolved_dept, resolved_opt = resolve_department_and_option(meta.faculty_code, meta.department, meta.option)

    # Determine School and Department texts
    school_name = meta.faculty.upper() if meta.faculty else "THE COLLEGE OF TECHNOLOGY"
    if "COLTECH" in meta.faculty_code.upper() and "(COLTECH)" not in school_name and "COLLEGE OF TECHNOLOGY" not in school_name:
        school_name = "THE COLLEGE OF TECHNOLOGY"
    dept_name = f"DEPARTMENT OF {resolved_dept.upper()}" if resolved_dept else "DEPARTMENT OF ORIGIN"

    is_dual = (header_mode == "dual_logo" or doc_type == "assignment")

    # 3-Column Crest & Establishment Table
    tbl = doc.add_table(rows=1, cols=3)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False

    if is_dual:
        # Dual logo layout: Left = UBa, Center = Text, Right = COLTECH
        col_widths = [Cm(2.6), Cm(9.8), Cm(2.6)]
        for idx, w in enumerate(col_widths):
            tbl.rows[0].cells[idx].width = w
            set_cell_margins(tbl.rows[0].cells[idx], top=10, bottom=10, left=15, right=15)

        # Left cell: UBa Crest
        c0 = tbl.cell(0, 0)
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if os.path.exists(UBA_LOGO_PATH):
            p0.add_run().add_picture(UBA_LOGO_PATH, width=Inches(1.0))

        # Center cell: School & Dept
        c1 = tbl.cell(0, 1)
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.paragraph_format.line_spacing = 1.15
        
        r_sn = p1.add_run(f"{school_name}\n")
        r_sn.font.name = "Times New Roman"
        r_sn.font.size = Pt(11)
        r_sn.font.bold = True

        r_dn = p1.add_run(dept_name)
        r_dn.font.name = "Times New Roman"
        r_dn.font.size = Pt(10.5)
        r_dn.font.bold = True

        # Right cell: COLTECH Emblem
        c2 = tbl.cell(0, 2)
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if os.path.exists(COLTECH_LOGO_PATH):
            p2.add_run().add_picture(COLTECH_LOGO_PATH, width=Inches(1.0))

    else:
        # Official Central Crest layout: Left = School, Center = UBa Crest, Right = Department
        col_widths = [Cm(5.8), Cm(3.4), Cm(5.8)]
        for idx, w in enumerate(col_widths):
            tbl.rows[0].cells[idx].width = w
            set_cell_margins(tbl.rows[0].cells[idx], top=10, bottom=10, left=15, right=15)

        # Left cell: School Name
        c0 = tbl.cell(0, 0)
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.line_spacing = 1.15
        r_sn = p0.add_run(f"{school_name}\n")
        r_sn.font.name = "Times New Roman"
        r_sn.font.size = Pt(11)
        r_sn.font.bold = True

        # Center cell: Official UBa Crest
        c1 = tbl.cell(0, 1)
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if os.path.exists(UBA_LOGO_PATH):
            p1.add_run().add_picture(UBA_LOGO_PATH, width=Inches(1.15))

        # Right cell: Department Name
        c2 = tbl.cell(0, 2)
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.line_spacing = 1.15
        r_dn = p2.add_run(dept_name)
        r_dn.font.name = "Times New Roman"
        r_dn.font.size = Pt(11)
        r_dn.font.bold = True




def get_purpose_clause(doc_type: str, meta: DocumentMetadata) -> str:
    """Generates the official degree award purpose clause."""
    school_name = meta.faculty if meta.faculty else "the College of Technology"
    if "College of Technology" in school_name and "(COLTECH)" not in school_name:
        school_name += " (COLTECH)"

    deg = meta.degree
    dept, opt = resolve_department_and_option(meta.faculty_code, meta.department, meta.option)

    if doc_type == "project_btech":
        return (
            f"A Final Year Project Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda in Partial Fulfillment of the Requirements for the Award "
            f"of a Bachelor of Technology (B.Tech) Degree in {opt}."
        )
    elif doc_type == "project_hnd":
        return (
            f"A Capstone Project Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda in Partial Fulfillment of the Requirements for the Award "
            f"of a Higher National Diploma (HND) in {opt}."
        )
    elif doc_type == "dissertation_mtech":
        return (
            f"A Dissertation Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda in Partial Fulfillment of the Requirements for the Award "
            f"of a Master of Technology (M.Tech) Degree in {opt}."
        )
    elif doc_type == "dissertation_msc":
        return (
            f"A Dissertation Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda in Partial Fulfillment of the Requirements for the Award "
            f"of a Master of Science (M.Sc) Degree in {opt}."
        )
    elif doc_type == "thesis_phd":
        return (
            f"A Thesis Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda in Partial Fulfillment of the Requirements for the Award "
            f"of a Doctor of Philosophy (Ph.D) Degree in {opt}."
        )
    elif doc_type == "proposal":
        return (
            f"A Research Proposal Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda in Partial Fulfillment of the Requirements for the Degree "
            f"of {deg} in {opt}."
        )
    elif doc_type == "internship":
        return (
            f"An Internship Report Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda in Partial Fulfillment of the Requirements for the Award "
            f"of a {deg} Degree in {opt}."
        )
    elif doc_type == "assignment":
        return (
            f"Continuous Assessment Assignment Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda for Course {meta.course_code}: {meta.course_title}."
        )
    else:
        # Default BSc
        return (
            f"A Dissertation Submitted to the Department of {dept} in {school_name} "
            f"of The University of Bamenda in Partial Fulfillment of the Requirements for the Award "
            f"of a Bachelor of Science (B.Sc) Degree in {opt}."
        )


def build_cover_page(
    doc: docx.Document,
    meta: DocumentMetadata,
    doc_type: str = "dissertation_bsc",
    header_mode: str = "center_crest",
    add_page_break: bool = True,
    custom_rules: Optional[CustomFormattingRules] = None
):
    """Builds the official Cover Page conforming strictly to UBa and Establishment specifications."""
    rules = custom_rules or CustomFormattingRules()
    add_header_banner(doc, meta, doc_type, header_mode)

    # Document Title in a clean rectangular single-line box or unboxed if specified
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(10)
    p_sp.paragraph_format.space_after = Pt(2)
    if not rules.box_title:
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_before = Pt(14)
        p_title.paragraph_format.space_after = Pt(14)
        p_title.paragraph_format.line_spacing = 1.2
        r_t = p_title.add_run(meta.title.upper())
        r_t.font.name = rules.font_name
        r_t.font.size = Pt(13)
        r_t.font.bold = True
    else:
        add_boxed_title(doc, meta.title, font_name=rules.font_name)

    # Purpose Clause
    p_clause = doc.add_paragraph()
    p_clause.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_clause.paragraph_format.space_before = Pt(8)
    p_clause.paragraph_format.space_after = Pt(16)
    p_clause.paragraph_format.line_spacing = 1.3
    
    r_clause = p_clause.add_run(get_purpose_clause(doc_type, meta))
    r_clause.font.name = rules.font_name
    r_clause.font.size = Pt(12)

    # Candidate / Group / Supervision Section
    if doc_type == "assignment":
        is_group_ass = bool(meta.is_group_assignment or (meta.group_members and len(meta.group_members) > 1))

        if is_group_ass:
            members = meta.group_members if meta.group_members else []
            if not members:
                # Default group representative members when user toggles group mode
                cand_name = meta.author if meta.author else "Candidate 1"
                cand_mat = meta.reg_number if meta.reg_number else ""
                members = [
                    GroupMember(name=cand_name, matricule=cand_mat, participation="Lead / Coordinator", grade="____ / 20"),
                ]

            if len(members) > 5:
                # EXCESS MEMBERS: Will not fit on the cover page!
                # The cover page now is NOT going to have any place for names or member table.
                p_grp = doc.add_paragraph()
                p_grp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_grp.paragraph_format.space_before = Pt(20)
                p_grp.paragraph_format.space_after = Pt(20)
                
                r_gt = p_grp.add_run(f"PRESENTED BY:\n{meta.group_name.upper() if meta.group_name else 'GROUP PRESENTATION'}\n")
                r_gt.font.name = "Times New Roman"
                r_gt.font.size = Pt(13)
                r_gt.font.bold = True
                
                r_sub = p_grp.add_run("(Complete Register of Group Members & Evaluation Sheet Attached on Page 2)")
                r_sub.font.name = "Times New Roman"
                r_sub.font.size = Pt(11)
                r_sub.font.italic = True
            else:
                # FITS ON COVER PAGE: Render the member table right on the cover page
                p_grp = doc.add_paragraph()
                p_grp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_grp.paragraph_format.space_before = Pt(8)
                p_grp.paragraph_format.space_after = Pt(6)
                r_gt = p_grp.add_run(f"PRESENTED BY: {meta.group_name.upper() if meta.group_name else 'GROUP WORK'}")
                r_gt.font.name = "Times New Roman"
                r_gt.font.size = Pt(11)
                r_gt.font.bold = True
                
                show_grading = meta.show_grading_column
                cols_count = 4 if show_grading else 3
                
                tbl_members = doc.add_table(rows=1 + len(members), cols=cols_count)
                tbl_members.alignment = WD_TABLE_ALIGNMENT.CENTER
                tbl_members.autofit = False
                
                col_widths = [Cm(1.0), Cm(6.5), Cm(3.8), Cm(3.5)] if show_grading else [Cm(1.2), Cm(7.5), Cm(5.0)]
                for row in tbl_members.rows:
                    for idx, w in enumerate(col_widths):
                        row.cells[idx].width = w
                        set_cell_margins(row.cells[idx], top=15, bottom=15, left=20, right=20)
                
                hdr_cells = tbl_members.rows[0].cells
                hdr_titles = ["N°", "FULL NAME", "MATRICULE / REG. NO."] + (["EVALUATION ( /20)"] if show_grading else [])
                for c_idx, title in enumerate(hdr_titles):
                    p_c = hdr_cells[c_idx].paragraphs[0]
                    p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx != 1 else WD_ALIGN_PARAGRAPH.LEFT
                    r_c = p_c.add_run(title)
                    r_c.font.name = "Times New Roman"
                    r_c.font.size = Pt(9.0)
                    r_c.font.bold = True
                    set_cell_background(hdr_cells[c_idx], "0B2545")
                    r_c.font.color.rgb = RGBColor(255, 255, 255)
                
                for m_idx, m in enumerate(members):
                    row_cells = tbl_members.rows[1 + m_idx].cells
                    p0 = row_cells[0].paragraphs[0]
                    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p0.add_run(f"{m_idx + 1:02d}").font.size = Pt(9.0)
                    
                    p1 = row_cells[1].paragraphs[0]
                    p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    r1 = p1.add_run(m.name.upper() if m.name else f"STUDENT {m_idx + 1}")
                    r1.font.name = "Times New Roman"
                    r1.font.size = Pt(9.0)
                    r1.font.bold = True
                    
                    p2 = row_cells[2].paragraphs[0]
                    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r2 = p2.add_run(m.matricule.upper() if m.matricule else "UBA25PP000")
                    r2.font.name = "Times New Roman"
                    r2.font.size = Pt(9.0)
                    
                    if show_grading:
                        p3 = row_cells[3].paragraphs[0]
                        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        grade_val = m.grade if m.grade else (m.participation if m.participation else "____ / 20")
                        r3 = p3.add_run(grade_val)
                        r3.font.name = "Times New Roman"
                        r3.font.size = Pt(8.5)
                        r3.font.italic = True
                    
                    if m_idx % 2 == 1:
                        for cell in row_cells:
                            set_cell_background(cell, "F1F5F9")
        else:
            # Personal / Individual Assignment: single person name on cover page
            p_author = doc.add_paragraph()
            p_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_author.paragraph_format.space_before = Pt(12)
            p_author.paragraph_format.space_after = Pt(12)
            p_author.paragraph_format.line_spacing = 1.2

            r_by = p_author.add_run("PRESENTED BY:\n")
            r_by.font.name = "Times New Roman"
            r_by.font.size = Pt(12)
            r_by.font.bold = True

            r_name = p_author.add_run(f"{meta.author.upper()}\n")
            r_name.font.name = "Times New Roman"
            r_name.font.size = Pt(13)
            r_name.font.bold = True

            r_mat = p_author.add_run(f"REGISTRATION NUMBER: {meta.reg_number}\n")
            r_mat.font.name = "Times New Roman"
            r_mat.font.size = Pt(11)
            r_mat.font.bold = True

            r_qual = p_author.add_run(f"({meta.degree} Candidate, The University of Bamenda)")
            r_qual.font.name = "Times New Roman"
            r_qual.font.size = Pt(10.5)
            r_qual.font.italic = True

        # Course Lecturer & Academic Year
        p_ass = doc.add_paragraph()
        p_ass.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ass.paragraph_format.space_before = Pt(10)
        p_ass.paragraph_format.space_after = Pt(14)
        r_lec = p_ass.add_run(f"COURSE LECTURER / INSTRUCTOR:\n{meta.lecturer.upper() if meta.lecturer else 'COURSE INSTRUCTOR'}\n")
        r_lec.font.name = "Times New Roman"
        r_lec.font.size = Pt(11.5)
        r_lec.font.bold = True

        r_ay = p_ass.add_run(f"Academic Year: {meta.academic_year if meta.academic_year else '2025/2026'}")
        r_ay.font.name = "Times New Roman"
        r_ay.font.size = Pt(11)

    elif doc_type == "internship":
        # Internship Report Cover Page
        p_author = doc.add_paragraph()
        p_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_author.paragraph_format.space_before = Pt(10)
        p_author.paragraph_format.space_after = Pt(10)
        p_author.paragraph_format.line_spacing = 1.2

        r_by = p_author.add_run("PRESENTED BY:\n")
        r_by.font.name = "Times New Roman"
        r_by.font.size = Pt(12)
        r_by.font.bold = True

        r_name = p_author.add_run(f"{meta.author.upper()}\n")
        r_name.font.name = "Times New Roman"
        r_name.font.size = Pt(13)
        r_name.font.bold = True

        r_mat = p_author.add_run(f"REGISTRATION NUMBER: {meta.reg_number}\n")
        r_mat.font.name = "Times New Roman"
        r_mat.font.size = Pt(11)
        r_mat.font.bold = True

        r_qual = p_author.add_run(f"({meta.degree} Intern, The University of Bamenda)")
        r_qual.font.name = "Times New Roman"
        r_qual.font.size = Pt(10.5)
        r_qual.font.italic = True

        p_sup = doc.add_paragraph()
        p_sup.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_sup.paragraph_format.space_before = Pt(10)
        p_sup.paragraph_format.space_after = Pt(12)
        p_sup.paragraph_format.line_spacing = 1.2

        r_st = p_sup.add_run("SUPERVISED BY:\n")
        r_st.font.name = "Times New Roman"
        r_st.font.size = Pt(11)
        r_st.font.bold = True

        acad_sup = meta.supervisors[0] if meta.supervisors else "The Academic Supervisor"
        field_sup = meta.field_supervisor if meta.field_supervisor else "The Field Supervisor"
        host_co = meta.host_company if meta.host_company else "The Host Enterprise"

        r_as = p_sup.add_run(f"ACADEMIC SUPERVISOR: {acad_sup.upper()}\n")
        r_as.font.name = "Times New Roman"
        r_as.font.size = Pt(11)
        r_as.font.bold = True

        r_fs = p_sup.add_run(f"FIELD SUPERVISOR: {field_sup.upper()}\n")
        r_fs.font.name = "Times New Roman"
        r_fs.font.size = Pt(11)
        r_fs.font.bold = True

        r_hc = p_sup.add_run(f"HOST INSTITUTION: {host_co.upper()}")
        r_hc.font.name = "Times New Roman"
        r_hc.font.size = Pt(10.5)
        r_hc.font.italic = True

    else:
        # Standard Dissertation / Thesis / Capstone Project / Proposal (Page 11 Template)
        p_author = doc.add_paragraph()
        p_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_author.paragraph_format.space_before = Pt(14)
        p_author.paragraph_format.space_after = Pt(14)
        p_author.paragraph_format.line_spacing = 1.25

        r_by = p_author.add_run("BY:\n")
        r_by.font.name = "Times New Roman"
        r_by.font.size = Pt(12)
        r_by.font.bold = True

        r_name = p_author.add_run(f"{meta.author.upper()}\n")
        r_name.font.name = "Times New Roman"
        r_name.font.size = Pt(13)
        r_name.font.bold = True

        mat_label = "MATRICULE" if "CATUC" in meta.faculty_code.upper() else "REGISTRATION NUMBER"
        r_mat = p_author.add_run(f"{mat_label} : {meta.reg_number}")
        r_mat.font.name = "Times New Roman"
        r_mat.font.size = Pt(11.5)
        r_mat.font.bold = True

        p_sup = doc.add_paragraph()
        p_sup.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_sup.paragraph_format.space_before = Pt(14)
        p_sup.paragraph_format.space_after = Pt(18)
        p_sup.paragraph_format.line_spacing = 1.25

        r_stitle = p_sup.add_run("SUPERVISOR(S) :\n")
        r_stitle.font.name = "Times New Roman"
        r_stitle.font.size = Pt(12)
        r_stitle.font.bold = True

        for i, s_name in enumerate(meta.supervisors):
            s_rank = meta.supervisor_ranks[i] if i < len(meta.supervisor_ranks) else "Associate Professor"
            r_sup_name = p_sup.add_run(f"{s_name.upper()}\n")
            r_sup_name.font.name = "Times New Roman"
            r_sup_name.font.size = Pt(12)
            r_sup_name.font.bold = True
            
            r_sup_rank = p_sup.add_run(f"({s_rank})\n" if not s_rank.startswith("(") else f"{s_rank}\n")
            r_sup_rank.font.name = "Times New Roman"
            r_sup_rank.font.size = Pt(11)

    # Date at bottom (anchored cleanly towards bottom margin, matching Page 11 template at y ~ 110 pt)
    title_len = len(meta.title or "")
    num_sups = len(meta.supervisors or [1])
    date_space_before = 235
    if title_len > 120:
        date_space_before -= 35
    elif title_len < 60:
        date_space_before += 20
    if num_sups > 1:
        date_space_before -= (num_sups - 1) * 30
    date_space_before = max(70, date_space_before)

    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_date.paragraph_format.space_before = Pt(date_space_before)
    p_date.paragraph_format.space_after = Pt(0)
    
    r_date = p_date.add_run(f"{meta.submission_month.upper()} {meta.submission_year}")
    r_date.font.name = "Times New Roman"
    r_date.font.size = Pt(12)
    r_date.font.bold = True

    if add_page_break:
        doc.add_page_break()


def build_group_members_page(doc: docx.Document, meta: DocumentMetadata):
    """
    Renders dedicated Page 2 for group assignments when the roster exceeds 5 members.
    Includes full-width candidate register, role/participation breakdown, and lecturer evaluation block.
    """
    members = meta.group_members if meta.group_members else []
    if not members:
        cand_name = meta.author if meta.author else "Candidate 1"
        cand_mat = meta.reg_number if meta.reg_number else ""
        members = [
            GroupMember(name=cand_name, matricule=cand_mat, participation="Lead / Coordinator", grade="____ / 20"),
        ]

    # Page Header
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(6)
    p_inst.paragraph_format.space_after = Pt(2)
    p_inst.paragraph_format.line_spacing = 1.15
    r_inst = p_inst.add_run(f"THE UNIVERSITY OF BAMENDA\n{meta.faculty.upper()}\nDEPARTMENT OF {meta.department.upper()}")
    r_inst.font.name = "Times New Roman"
    r_inst.font.size = Pt(11)
    r_inst.font.bold = True

    p_head = doc.add_paragraph()
    p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_head.paragraph_format.space_before = Pt(12)
    p_head.paragraph_format.space_after = Pt(6)
    r_h = p_head.add_run("LIST OF GROUP MEMBERS & PRESENTATION EVALUATION ROSTER")
    r_h.font.name = "Times New Roman"
    r_h.font.size = Pt(13)
    r_h.font.bold = True

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_before = Pt(2)
    p_meta.paragraph_format.space_after = Pt(12)
    p_meta.paragraph_format.line_spacing = 1.2
    
    r_m = p_meta.add_run(
        f"Course: {meta.course_code} — {meta.course_title}\n"
        f"Group: {meta.group_name.upper() if meta.group_name else 'GROUP WORK'}  |  Academic Year: {meta.academic_year}\n"
        f"Assignment Topic: “{meta.title}”"
    )
    r_m.font.name = "Times New Roman"
    r_m.font.size = Pt(10.5)

    show_grading = meta.show_grading_column
    cols_count = 5 if show_grading else 4
    
    tbl = doc.add_table(rows=1 + len(members), cols=cols_count)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False

    col_widths = [Cm(1.0), Cm(5.8), Cm(3.2), Cm(3.0), Cm(2.0)] if show_grading else [Cm(1.2), Cm(6.5), Cm(3.8), Cm(3.5)]
    for row in tbl.rows:
        for idx, w in enumerate(col_widths):
            row.cells[idx].width = w
            set_cell_margins(row.cells[idx], top=15, bottom=15, left=20, right=20)

    hdr_cells = tbl.rows[0].cells
    hdr_titles = ["N°", "STUDENT FULL NAME", "MATRICULE", "CONTRIBUTION / ROLE"] + (["SCORE / 20"] if show_grading else [])
    for c_idx, title in enumerate(hdr_titles):
        p_c = hdr_cells[c_idx].paragraphs[0]
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx != 1 else WD_ALIGN_PARAGRAPH.LEFT
        r_c = p_c.add_run(title)
        r_c.font.name = "Times New Roman"
        r_c.font.size = Pt(9.0)
        r_c.font.bold = True
        set_cell_background(hdr_cells[c_idx], "0B2545")
        r_c.font.color.rgb = RGBColor(255, 255, 255)

    for m_idx, m in enumerate(members):
        row_cells = tbl.rows[1 + m_idx].cells
        # N°
        p0 = row_cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.add_run(f"{m_idx + 1:02d}").font.size = Pt(9.0)
        
        # Name
        p1 = row_cells[1].paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_nm = p1.add_run(m.name.upper() if m.name else f"STUDENT {m_idx + 1}")
        r_nm.font.name = "Times New Roman"
        r_nm.font.size = Pt(9.0)
        r_nm.font.bold = True
        
        # Matricule
        p2 = row_cells[2].paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.add_run(m.matricule.upper() if m.matricule else "UBA25PP000").font.size = Pt(9.0)
        
        # Role / Contribution
        p3 = row_cells[3].paragraphs[0]
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        role_txt = m.participation if m.participation else "100%"
        p3.add_run(role_txt).font.size = Pt(8.5)
        
        # Grading
        if show_grading:
            p4 = row_cells[4].paragraphs[0]
            p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
            score_txt = m.grade if m.grade else "____ / 20"
            r_sc = p4.add_run(score_txt)
            r_sc.font.name = "Times New Roman"
            r_sc.font.size = Pt(8.5)
            r_sc.font.italic = True

        if m_idx % 2 == 1:
            for cell in row_cells:
                set_cell_background(cell, "F1F5F9")

    # Lecturer / Examiner Remarks & Sign-off Block
    p_eval = doc.add_paragraph()
    p_eval.paragraph_format.space_before = Pt(16)
    p_eval.paragraph_format.space_after = Pt(2)
    r_ev = p_eval.add_run("EVALUATOR / COURSE LECTURER SIGN-OFF:\n")
    r_ev.font.name = "Times New Roman"
    r_ev.font.size = Pt(10.5)
    r_ev.font.bold = True

    p_com = doc.add_paragraph()
    p_com.paragraph_format.space_after = Pt(10)
    p_com.paragraph_format.line_spacing = 1.3
    r_com = p_com.add_run(
        f"Course Lecturer: {meta.lecturer.upper() if meta.lecturer else 'COURSE INSTRUCTOR'}\n"
        f"Remarks / Evaluation Feedback: _____________________________________________________________________\n"
        f"Lecturer Signature: ___________________________________      Date: _________________________________"
    )
    r_com.font.name = "Times New Roman"
    r_com.font.size = Pt(9.5)
    
    doc.add_page_break()


def build_internship_prelims(doc: docx.Document, meta: DocumentMetadata, parsed: ParsedDocument):
    """
    Builds official preliminary pages for Internship Reports conforming to UBa / FEMS / COLTECH standards.
    Order:
      1. Attestation / Certification of Internship Completion (Academic & Field Supervisors)
      2. Declaration of Originality of Internship Report
      3. Dedication
      4. Acknowledgements
      5. Executive Summary (Abstract)
    """
    # 1. Attestation of Internship Completion
    p_ch = doc.add_paragraph()
    p_ch.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ch.paragraph_format.space_before = Pt(24)
    p_ch.paragraph_format.space_after = Pt(20)
    
    r_ch = p_ch.add_run("ATTESTATION OF INTERNSHIP COMPLETION")
    r_ch.font.name = "Times New Roman"
    r_ch.font.size = Pt(14)
    r_ch.font.bold = True

    p_ct = doc.add_paragraph()
    p_ct.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_ct.paragraph_format.line_spacing = 1.5
    p_ct.paragraph_format.space_after = Pt(24)

    host_co = meta.host_company if meta.host_company else "the Host Enterprise / Organization"
    field_sup = meta.field_supervisor if meta.field_supervisor else "The Field / Professional Supervisor"
    acad_sup = meta.supervisors[0] if meta.supervisors else "The Academic Supervisor"

    cert_text = (
        f"This is to attest that {meta.author.upper()}, registration number {meta.reg_number}, "
        f"a candidate for the award of a {meta.degree} Degree in {meta.option} in {meta.faculty} "
        f"of The University of Bamenda, successfully carried out an academic internship at "
        f"{host_co}. This report titled “{meta.title}” reflects the practical and technical "
        f"duties executed under professional and academic supervision."
    )
    r_ct = p_ct.add_run(cert_text)
    r_ct.font.name = "Times New Roman"
    r_ct.font.size = Pt(12)

    # 2-Row Dual Supervisor Signature Block
    tbl_isig = doc.add_table(rows=2, cols=2)
    tbl_isig.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_isig.rows[0].cells[0].width = Cm(7.5)
    tbl_isig.rows[0].cells[1].width = Cm(7.5)
    tbl_isig.rows[1].cells[0].width = Cm(7.5)
    tbl_isig.rows[1].cells[1].width = Cm(7.5)
    set_cell_margins(tbl_isig.rows[0].cells[0], top=10, bottom=10, left=10, right=10)
    set_cell_margins(tbl_isig.rows[0].cells[1], top=10, bottom=10, left=10, right=10)
    set_cell_margins(tbl_isig.rows[1].cells[0], top=10, bottom=10, left=10, right=10)
    set_cell_margins(tbl_isig.rows[1].cells[1], top=10, bottom=10, left=10, right=10)

    p_fs = tbl_isig.rows[0].cells[0].paragraphs[0]
    p_fs.add_run(f"FIELD / PROFESSIONAL SUPERVISOR:\n{field_sup}\nSignature: _______________________\nDate: ___________________________").font.name = "Times New Roman"
    
    p_as = tbl_isig.rows[0].cells[1].paragraphs[0]
    p_as.add_run(f"ACADEMIC SUPERVISOR:\n{acad_sup}\nSignature: _______________________\nDate: ___________________________").font.name = "Times New Roman"

    p_hd = tbl_isig.rows[1].cells[0].paragraphs[0]
    p_hd.add_run(f"HEAD OF DEPARTMENT:\n{meta.hod_name}\nSignature: _______________________\nDate: ___________________________").font.name = "Times New Roman"

    p_dr = tbl_isig.rows[1].cells[1].paragraphs[0]
    p_dr.add_run(f"DEAN / DIRECTOR:\n{meta.director_name}\nSignature: _______________________\nDate: ___________________________").font.name = "Times New Roman"

    doc.add_page_break()

    # 2. Declaration of Originality
    p_dh = doc.add_paragraph()
    p_dh.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_dh.paragraph_format.space_before = Pt(24)
    p_dh.paragraph_format.space_after = Pt(20)
    r_dh = p_dh.add_run("DECLARATION")
    r_dh.font.name = "Times New Roman"
    r_dh.font.size = Pt(14)
    r_dh.font.bold = True

    p_dt = doc.add_paragraph()
    p_dt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_dt.paragraph_format.line_spacing = 1.5
    p_dt.paragraph_format.space_after = Pt(30)

    decl_text = (
        f"I, {meta.author.upper()}, registration N◦ : {meta.reg_number}, in the Department of "
        f"{meta.department} in {meta.faculty} of The University of Bamenda, hereby declare that this "
        f"internship report titled “{meta.title}” is an authentic record of the internship completed "
        f"at {host_co}. It has not been presented for any other academic qualification. All references "
        f"and secondary data sources have been duly cited."
    )
    r_dt = p_dt.add_run(decl_text)
    r_dt.font.name = "Times New Roman"
    r_dt.font.size = Pt(12)

    tbl_dsig = doc.add_table(rows=1, cols=2)
    tbl_dsig.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_dsig.rows[0].cells[0].width = Cm(7.5)
    tbl_dsig.rows[0].cells[1].width = Cm(7.5)
    p_s1 = tbl_dsig.rows[0].cells[0].paragraphs[0]
    p_s1.add_run("Date: ________________________").font.name = "Times New Roman"
    p_s2 = tbl_dsig.rows[0].cells[1].paragraphs[0]
    p_s2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_s2.add_run("Signature of Intern: ________________________").font.name = "Times New Roman"

    doc.add_page_break()

    # 3. Dedication
    p_ded = doc.add_paragraph()
    p_ded.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ded.paragraph_format.space_before = Pt(24)
    p_ded.paragraph_format.space_after = Pt(20)
    r_ded = p_ded.add_run("DEDICATION")
    r_ded.font.name = "Times New Roman"
    r_ded.font.size = Pt(14)
    r_ded.font.bold = True

    p_ded_t = doc.add_paragraph()
    p_ded_t.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_ded_t.paragraph_format.line_spacing = 1.5
    p_ded_t.paragraph_format.space_after = Pt(20)
    r_dtx = p_ded_t.add_run("This work is dedicated to my family and mentors whose unwavering encouragement and moral guidance have supported my academic and professional development.")
    r_dtx.font.name = "Times New Roman"
    r_dtx.font.size = Pt(12)
    r_dtx.font.italic = False

    doc.add_page_break()

    # 4. Acknowledgements
    p_ack = doc.add_paragraph()
    p_ack.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ack.paragraph_format.space_before = Pt(24)
    p_ack.paragraph_format.space_after = Pt(20)
    r_ack = p_ack.add_run("ACKNOWLEDGEMENTS")
    r_ack.font.name = "Times New Roman"
    r_ack.font.size = Pt(14)
    r_ack.font.bold = True

    p_ack_t = doc.add_paragraph()
    p_ack_t.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_ack_t.paragraph_format.line_spacing = 1.5
    p_ack_t.paragraph_format.space_after = Pt(20)
    r_atx = p_ack_t.add_run(
        f"I express sincere gratitude to the management and staff of {host_co} for offering me "
        f"the opportunity to undertake this practical internship. Special thanks go to my field supervisor, "
        f"{field_sup}, and my academic supervisor, {acad_sup}, for their pedagogical guidance and technical "
        f"supervision throughout the internship period. I also thank the Department of {meta.department}, "
        f"{meta.faculty}, and The University of Bamenda for their continual institutional support."
    )
    r_atx.font.name = "Times New Roman"
    r_atx.font.size = Pt(12)

    doc.add_page_break()

    # 5. Executive Summary
    p_es = doc.add_paragraph()
    p_es.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_es.paragraph_format.space_before = Pt(24)
    p_es.paragraph_format.space_after = Pt(20)
    r_es = p_es.add_run("EXECUTIVE SUMMARY")
    r_es.font.name = "Times New Roman"
    r_es.font.size = Pt(14)
    r_es.font.bold = True

    p_est = doc.add_paragraph()
    p_est.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_est.paragraph_format.line_spacing = 1.5
    p_est.paragraph_format.space_after = Pt(20)
    r_estx = p_est.add_run(
        f"This report presents the outcomes and professional experiences gained during the internship conducted at "
        f"{host_co} in partial fulfillment of the degree of {meta.degree} in {meta.option}. The report covers an "
        f"institutional overview of the enterprise, details of technical duties executed, operational challenges "
        f"encountered, and constructive recommendations formulated to enhance organizational workflows and productivity."
    )
    r_estx.font.name = "Times New Roman"
    r_estx.font.size = Pt(12)

    doc.add_page_break()


def build_statutory_prelims(doc: docx.Document, meta: DocumentMetadata, doc_type: str = "dissertation_bsc"):
    """Builds Copyright, Declaration, Certification, and Acceptance pages with zero-wrap signature tables."""
def build_statutory_prelims(doc: docx.Document, meta: DocumentMetadata, doc_type: str = "dissertation_bsc"):
    """Builds Declaration and Certification pages with zero-wrap signature tables."""
    resolved_dept, resolved_opt = resolve_department_and_option(meta.faculty_code, meta.department, meta.option)

    if doc_type == "proposal":
        # 1. Declaration of Originality of Proposal (Page ii)
        p_dh = doc.add_paragraph()
        p_dh.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_dh.paragraph_format.space_before = Pt(24)
        p_dh.paragraph_format.space_after = Pt(24)
        
        r_dh = p_dh.add_run("DECLARATION OF ORIGINALITY OF PROPOSAL")
        r_dh.font.name = "Times New Roman"
        r_dh.font.size = Pt(14)
        r_dh.font.bold = True

        p_dt = doc.add_paragraph()
        p_dt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_dt.paragraph_format.line_spacing = 1.5
        p_dt.paragraph_format.space_after = Pt(40)

        decl_text = (
            f"I, {meta.author.upper()}, registration N◦ : {meta.reg_number}, in the Department of "
            f"{resolved_dept} in {meta.faculty} of The University of Bamenda hereby declare that, "
            f"this research proposal titled “{meta.title}” is my original work. It has not been presented in any "
            f"application for a degree or any academic pursuit. I have acknowledged all borrowed ideas "
            f"nationally and internationally through citations."
        )
        r_dt = p_dt.add_run(decl_text)
        r_dt.font.name = "Times New Roman"
        r_dt.font.size = Pt(12)

        # 2-Column Signature Table
        tbl_sig = doc.add_table(rows=1, cols=2)
        tbl_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_sig.rows[0].cells[0].width = Cm(7.5)
        tbl_sig.rows[0].cells[1].width = Cm(7.5)
        set_cell_margins(tbl_sig.rows[0].cells[0], top=10, bottom=10, left=10, right=10)
        set_cell_margins(tbl_sig.rows[0].cells[1], top=10, bottom=10, left=10, right=10)

        p_s1 = tbl_sig.rows[0].cells[0].paragraphs[0]
        p_s1.add_run("Date: ________________________").font.name = "Times New Roman"
        p_s2 = tbl_sig.rows[0].cells[1].paragraphs[0]
        p_s2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_s2.add_run("Signature of Author: ________________________").font.name = "Times New Roman"

        doc.add_page_break()

    else:
        # Standard Dissertation / Thesis / Capstone Project
        # 1. Declaration of Originality of Study (Page ii)
        p_dh = doc.add_paragraph()
        p_dh.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_dh.paragraph_format.space_before = Pt(24)
        p_dh.paragraph_format.space_after = Pt(24)
        
        r_dh = p_dh.add_run("DECLARATION OF ORIGINALITY OF STUDY")
        r_dh.font.name = "Times New Roman"
        r_dh.font.size = Pt(14)
        r_dh.font.bold = True

        p_dt = doc.add_paragraph()
        p_dt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_dt.paragraph_format.line_spacing = 1.5
        p_dt.paragraph_format.space_after = Pt(40)

        decl_text = (
            f"I, {meta.author.upper()}, registration N◦ : {meta.reg_number}, in the Department of "
            f"{resolved_dept} in {meta.faculty} of The University of Bamenda hereby declare that, "
            f"this work titled “{meta.title}” is my original work. It has not been presented in any "
            f"application for a degree or any academic pursuit. I have acknowledged all borrowed ideas "
            f"nationally and internationally through citations."
        )
        r_dt = p_dt.add_run(decl_text)
        r_dt.font.name = "Times New Roman"
        r_dt.font.size = Pt(12)

        # 2-Column Signature Table
        tbl_sig = doc.add_table(rows=1, cols=2)
        tbl_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl_sig.rows[0].cells[0].width = Cm(7.5)
        tbl_sig.rows[0].cells[1].width = Cm(7.5)
        set_cell_margins(tbl_sig.rows[0].cells[0], top=10, bottom=10, left=10, right=10)
        set_cell_margins(tbl_sig.rows[0].cells[1], top=10, bottom=10, left=10, right=10)

        p_s1 = tbl_sig.rows[0].cells[0].paragraphs[0]
        p_s1.add_run("Date: ________________________").font.name = "Times New Roman"
        p_s2 = tbl_sig.rows[0].cells[1].paragraphs[0]
        p_s2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_s2.add_run("Signature of Author: ________________________").font.name = "Times New Roman"

        doc.add_page_break()

        # 2. Certification of Corrections after Defense (Page iii)
        p_ch = doc.add_paragraph()
        p_ch.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ch.paragraph_format.space_before = Pt(24)
        p_ch.paragraph_format.space_after = Pt(24)
        
        r_ch = p_ch.add_run("CERTIFICATION OF CORRECTIONS AFTER DEFENSE")
        r_ch.font.name = "Times New Roman"
        r_ch.font.size = Pt(14)
        r_ch.font.bold = True

        p_ct = doc.add_paragraph()
        p_ct.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ct.paragraph_format.line_spacing = 1.5
        p_ct.paragraph_format.space_after = Pt(30)

        doc_term = "dissertation" if "dissertation" in doc_type else ("project" if "project" in doc_type else "thesis")
        cert_text = (
            f"This is to certify that this {doc_term} titled “{meta.title}” is the original work of "
            f"{meta.author.upper()}. This work is submitted in partial fulfillment of the requirements for "
            f"the award of a {meta.degree} Degree in {resolved_opt} in {meta.faculty} of "
            f"The University of Bamenda, Cameroon."
        )
        r_ct = p_ct.add_run(cert_text)
        r_ct.font.name = "Times New Roman"
        r_ct.font.size = Pt(12)

        # Signatures
        sup_main = meta.supervisors[0] if (meta.supervisors and meta.supervisors[0]) else "The Academic Supervisor"
        sup_rank = meta.supervisor_ranks[0] if (meta.supervisor_ranks and meta.supervisor_ranks[0]) else "Supervisor"
        
        sigs = [
            ("Supervisor", f"{sup_main} ({sup_rank})"),
            ("The Head of Department", meta.hod_name),
            ("The Director / Dean", f"{meta.director_name} ({meta.director_title})")
        ]
        for role, name in sigs:
            p_s = doc.add_paragraph()
            p_s.paragraph_format.space_before = Pt(12)
            p_s.paragraph_format.space_after = Pt(2)
            r_sr = p_s.add_run(f"{role} : __________________________________________________\n")
            r_sr.font.name = "Times New Roman"
            r_sr.font.size = Pt(11)
            r_sr.font.bold = True
            
            r_sn = p_s.add_run(f"{name}\n")
            r_sn.font.name = "Times New Roman"
            r_sn.font.size = Pt(11)
            r_sn.font.italic = True

        doc.add_page_break()


def build_dissertation_dedication_and_ack(doc: docx.Document, meta: DocumentMetadata):
    """Builds official Dedication and Acknowledgements pages for Dissertations/Theses/Projects."""
    resolved_dept, resolved_opt = resolve_department_and_option(meta.faculty_code, meta.department, meta.option)

    # Dedication
    p_ded = doc.add_paragraph()
    p_ded.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ded.paragraph_format.space_before = Pt(24)
    p_ded.paragraph_format.space_after = Pt(20)
    r_ded = p_ded.add_run("DEDICATION")
    r_ded.font.name = "Times New Roman"
    r_ded.font.size = Pt(14)
    r_ded.font.bold = True

    p_ded_t = doc.add_paragraph()
    p_ded_t.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_ded_t.paragraph_format.line_spacing = 1.5
    p_ded_t.paragraph_format.space_after = Pt(20)
    r_dtx = p_ded_t.add_run("This work is dedicated to Almighty God, my family, and mentors whose constant prayers, sacrifices, and unwavering encouragement have guided and inspired this academic achievement.")
    r_dtx.font.name = "Times New Roman"
    r_dtx.font.size = Pt(12)
    r_dtx.font.italic = False

    doc.add_page_break()

    # Acknowledgements
    p_ack = doc.add_paragraph()
    p_ack.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ack.paragraph_format.space_before = Pt(24)
    p_ack.paragraph_format.space_after = Pt(20)
    r_ack = p_ack.add_run("ACKNOWLEDGEMENTS")
    r_ack.font.name = "Times New Roman"
    r_ack.font.size = Pt(14)
    r_ack.font.bold = True

    p_ack_t = doc.add_paragraph()
    p_ack_t.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_ack_t.paragraph_format.line_spacing = 1.5
    p_ack_t.paragraph_format.space_after = Pt(20)

    sup_main = meta.supervisors[0] if meta.supervisors else "the Academic Supervisor"
    ack_text = (
        f"I wish to express my deepest gratitude to my supervisor, {sup_main}, for the constructive critiques, "
        f"intellectual mentorship, and continuous guidance provided throughout the conception and realization of this work.\n\n"
        f"My appreciation goes to the Head of Department and the entire teaching faculty of the Department of {resolved_dept}, "
        f"{meta.faculty}, and The University of Bamenda for their dedication and academic support. "
        f"I also extend my heartfelt thanks to my colleagues and friends for their collaboration and shared experiences."
    )
    r_atx = p_ack_t.add_run(ack_text)
    r_atx.font.name = "Times New Roman"
    r_atx.font.size = Pt(12)

    doc.add_page_break()



def build_abstract_and_resume(doc: docx.Document, meta: DocumentMetadata, parsed: ParsedDocument):
    """Builds English Abstract and French Résumé pages."""
    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_h.paragraph_format.space_before = Pt(20)
    p_h.paragraph_format.space_after = Pt(16)
    r_h = p_h.add_run("ABSTRACT")
    r_h.font.name = "Times New Roman"
    r_h.font.size = Pt(14)
    r_h.font.bold = True

    p_ab = doc.add_paragraph()
    p_ab.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_ab.paragraph_format.line_spacing = 1.5
    p_ab.paragraph_format.space_after = Pt(20)

    sample_abstract = (
        f"This study investigates and presents the implementation of {meta.title} developed in the Department of "
        f"{meta.department} in {meta.faculty} at The University of Bamenda. The primary aim is to resolve "
        f"operational challenges through modern technological frameworks and rigorous system architecture. The results "
        f"demonstrate high reliability, performance efficiency, and adherence to academic and industrial standards."
    )
    r_ab = p_ab.add_run(sample_abstract)
    r_ab.font.name = "Times New Roman"
    r_ab.font.size = Pt(12)

    p_kw = doc.add_paragraph()
    p_kw.paragraph_format.space_before = Pt(14)
    r_kw_lbl = p_kw.add_run("Keywords: ")
    r_kw_lbl.font.name = "Times New Roman"
    r_kw_lbl.font.size = Pt(12)
    r_kw_lbl.font.bold = True

    r_kw = p_kw.add_run(f"System Architecture, {meta.option}, University of Bamenda, Engineering, Performance Optimization.")
    r_kw.font.name = "Times New Roman"
    r_kw.font.size = Pt(12)
    r_kw.font.italic = True
    doc.add_page_break()

    # French Résumé
    p_rh = doc.add_paragraph()
    p_rh.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_rh.paragraph_format.space_before = Pt(20)
    p_rh.paragraph_format.space_after = Pt(16)
    r_rh = p_rh.add_run("RÉSUMÉ")
    r_rh.font.name = "Times New Roman"
    r_rh.font.size = Pt(14)
    r_rh.font.bold = True

    p_rab = doc.add_paragraph()
    p_rab.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_rab.paragraph_format.line_spacing = 1.5
    p_rab.paragraph_format.space_after = Pt(20)

    french_abstract = (
        f"Cette étude examine et présente la conception et le développement de {meta.title} au sein du Département de "
        f"{meta.department} à {meta.faculty} de l'Université de Bamenda. L'objectif principal est de concevoir "
        f"une architecture robuste et hautement performante répondant aux exigences académiques et professionnelles."
    )
    r_rab = p_rab.add_run(french_abstract)
    r_rab.font.name = "Times New Roman"
    r_rab.font.size = Pt(12)

    p_mots = doc.add_paragraph()
    p_mots.paragraph_format.space_before = Pt(14)
    r_mk_lbl = p_mots.add_run("Mots-clés : ")
    r_mk_lbl.font.name = "Times New Roman"
    r_mk_lbl.font.size = Pt(12)
    r_mk_lbl.font.bold = True

    r_mk = p_mots.add_run(f"Architecture Système, {meta.option}, Université de Bamenda, Ingénierie, Optimisation.")
    r_mk.font.name = "Times New Roman"
    r_mk.font.size = Pt(12)
    r_mk.font.italic = True
    doc.add_page_break()


def build_assignment_acknowledgements(doc: docx.Document, meta: DocumentMetadata):
    """Builds official Acknowledgements page for Technical Course Assignments."""
    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_h.paragraph_format.space_before = Pt(30)
    p_h.paragraph_format.space_after = Pt(24)
    r_h = p_h.add_run("ACKNOWLEDGEMENTS")
    r_h.font.name = "Times New Roman"
    r_h.font.size = Pt(14)
    r_h.font.bold = True

    p_t = doc.add_paragraph()
    p_t.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_t.paragraph_format.line_spacing = 1.5
    p_t.paragraph_format.space_after = Pt(20)

    lec = meta.lecturer if meta.lecturer else "the Course Lecturer"
    course = f"{meta.course_code}: {meta.course_title}" if meta.course_code else "this technical course"
    school = meta.faculty if meta.faculty else "the College of Technology"
    dept = meta.department if meta.department else "Computer Engineering"

    ack_text = (
        f"I wish to express my sincere appreciation to the course lecturer, {lec}, for the invaluable guidance, "
        f"intellectual inspiration, and pedagogical support provided throughout the study of {course} in the Department "
        f"of {dept}, {school} of The University of Bamenda.\n\n"
        f"I am equally grateful to the Department for providing the technical infrastructure and academic environment "
        f"conducive to professional engineering practice. Gratitude is also extended to my fellow students and peers for "
        f"their constructive intellectual interactions and collaborative discussions during the execution of this assignment."
    )
    r_t = p_t.add_run(ack_text)
    r_t.font.name = "Times New Roman"
    r_t.font.size = Pt(12)

    doc.add_page_break()


def build_table_of_contents(
    doc: docx.Document,
    parsed: ParsedDocument,
    doc_type: str = "dissertation_bsc",
    body_paras: Optional[List[Dict[str, Any]]] = None,
    custom_rules: Optional[CustomFormattingRules] = None
):
    """Builds a formatted, dynamically accurate Table of Contents with dot leaders and aligned pages."""
    rules = custom_rules or CustomFormattingRules()
    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_h.paragraph_format.space_before = Pt(20)
    p_h.paragraph_format.space_after = Pt(24)
    r_h = p_h.add_run("TABLE OF CONTENTS")
    r_h.font.name = rules.font_name
    r_h.font.size = Pt(14)
    r_h.font.bold = True

    toc_items = []
    tables_present = bool(getattr(parsed, "tables_count", 0) > 0 or getattr(parsed, "extracted_tables", None))
    figures_present = bool(getattr(parsed, "figures_count", 0) > 0)

    # 1. Dynamic Preliminaries with accurate lower-Roman pagination
    if doc_type == "assignment":
        toc_items = [
            ("PRELIMINARY PAGES", "", 0, True),
            ("Acknowledgements", "ii", 1, False),
            ("Table of Contents", "iii", 1, False),
        ]
        if tables_present:
            toc_items.append(("List of Tables", "iv", 1, False))
        if figures_present:
            f_num = "v" if tables_present else "iv"
            toc_items.append(("List of Figures", f_num, 1, False))
        toc_items.append(("ASSIGNMENT TASKS & QUESTIONS", "1", 0, True))

    elif doc_type == "internship":
        toc_items = [
            ("PRELIMINARY PAGES", "", 0, True),
            ("Attestation of Internship Completion", "ii", 1, False),
            ("Declaration of Originality", "iii", 1, False),
            ("Dedication & Acknowledgements", "iv", 1, False),
            ("Executive Summary", "v", 1, False),
            ("Table of Contents", "vi", 1, False),
        ]
        next_roman_idx = 7
        romans_map = {7: "vii", 8: "viii", 9: "ix", 10: "x", 11: "xi"}
        if tables_present:
            toc_items.append(("List of Tables", romans_map.get(next_roman_idx, "vii"), 1, False))
            next_roman_idx += 1
        if figures_present:
            toc_items.append(("List of Figures", romans_map.get(next_roman_idx, "viii"), 1, False))
            next_roman_idx += 1
        toc_items.append(("List of Abbreviations & Acronyms", romans_map.get(next_roman_idx, "ix"), 1, False))

    elif doc_type == "proposal":
        toc_items = [
            ("PRELIMINARY PAGES", "", 0, True),
            ("Declaration of Originality of Proposal", "ii", 1, False),
            ("Abstract", "iii", 1, False),
            ("Résumé", "iv", 1, False),
            ("Table of Contents", "v", 1, False),
        ]
        next_roman_idx = 6
        romans_map = {6: "vi", 7: "vii", 8: "viii", 9: "ix", 10: "x"}
        if tables_present:
            toc_items.append(("List of Tables", romans_map.get(next_roman_idx, "vi"), 1, False))
            next_roman_idx += 1
        if figures_present:
            toc_items.append(("List of Figures", romans_map.get(next_roman_idx, "vii"), 1, False))
            next_roman_idx += 1
        toc_items.append(("List of Abbreviations & Acronyms", romans_map.get(next_roman_idx, "viii"), 1, False))

    else:
        # Dissertation / Thesis standard
        toc_items = [
            ("PRELIMINARY PAGES", "", 0, True),
            ("Declaration of Originality of Study", "ii", 1, False),
            ("Certification of Corrections after Defense", "iii", 1, False),
            ("Abstract", "iv", 1, False),
            ("Résumé", "v", 1, False),
            ("Dedication", "vi", 1, False),
            ("Acknowledgements", "vii", 1, False),
            ("Table of Contents", "viii", 1, False),
        ]
        next_roman_idx = 9
        romans_map = {9: "ix", 10: "x", 11: "xi", 12: "xii"}
        if tables_present:
            toc_items.append(("List of Tables", romans_map.get(next_roman_idx, "ix"), 1, False))
            next_roman_idx += 1
        if figures_present:
            toc_items.append(("List of Figures", romans_map.get(next_roman_idx, "x"), 1, False))
            next_roman_idx += 1
        toc_items.append(("List of Abbreviations & Acronyms", romans_map.get(next_roman_idx, "xi"), 1, False))

    # 2. Extract Substantive Body Chapters & Sections dynamically
    seen_chapters = set()
    seen_sections = set()
    cur_p = 1
    word_count = 0
    body_items = []

    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}
    ch_titles_default = {
        1: "INTRODUCTION",
        2: "LITERATURE REVIEW" if doc_type != "internship" else "HOST ORGANIZATION OVERVIEW",
        3: "MATERIALS AND METHODS" if doc_type not in ["proposal", "internship"] else ("PROPOSED METHODOLOGY" if doc_type == "proposal" else "INTERNSHIP ACTIVITIES"),
        4: "RESULTS AND DISCUSSION" if doc_type != "internship" else "SITUATIONAL AND CRITICAL APPRAISAL",
        5: "CONCLUSION AND RECOMMENDATIONS"
    }

    if body_paras:
        for bp in body_paras:
            txt = bp.get("text", "").strip()
            if not txt:
                continue

            words = len(txt.split())
            word_count += words
            if word_count > 300:
                cur_p += max(1, word_count // 300)
                word_count = word_count % 300

            # Match explicit chapter heading
            ch_m = re.match(r'^(?:CHAPTER|CHAPITRE)\s+(\d+|[IVXLCDM]+)(?:\s*[:\-–]\s*|\s+)(.*)$', txt, re.IGNORECASE)
            # Match section heading e.g. "1.1 Background"
            sec_m = re.match(r'^([1-9])\.(\d+)(?:\s*[:\-–]\s*|\s+)(.*)$', txt)
            # Match assignment questions/tasks
            task_m = re.match(r'^(?:QUESTION|TASK|EXERCISE|PROBLEM|PART|SECTION)\s*(\d+|[IVXLCDM]+)?(?:\s*[:\-–]\s*|\s+)(.*)$', txt, re.IGNORECASE)

            if ch_m:
                num_str = ch_m.group(1).upper()
                ch_num = roman_map.get(num_str, int(num_str) if num_str.isdigit() else 1)
                if ch_num not in seen_chapters:
                    seen_chapters.add(ch_num)
                    if ch_num > 1:
                        cur_p += 1
                        word_count = 0
                    sub = ch_m.group(2).strip().upper()
                    def_t = ch_titles_default.get(ch_num, "")
                    ch_title_text = f"CHAPTER {ch_num}: {sub}" if sub else (f"CHAPTER {ch_num}: {def_t}" if def_t else f"CHAPTER {ch_num}")
                    body_items.append((ch_title_text, str(cur_p), 0, True))

            elif sec_m:
                ch_num = int(sec_m.group(1))
                sec_num = int(sec_m.group(2))
                sec_key = f"{ch_num}.{sec_num}"
                if sec_key not in seen_sections:
                    seen_sections.add(sec_key)
                    # Auto-inject chapter if missing
                    if ch_num not in seen_chapters:
                        seen_chapters.add(ch_num)
                        if ch_num > 1:
                            cur_p += 1
                            word_count = 0
                        def_t = ch_titles_default.get(ch_num, f"CHAPTER {ch_num}")
                        body_items.append((f"CHAPTER {ch_num}: {def_t}".upper(), str(cur_p), 0, True))
                    sec_title = sec_m.group(3).strip() if sec_m.group(3) else txt
                    clean_sec_title = f"{ch_num}.{sec_num} {sec_title}"[:65].strip()
                    body_items.append((clean_sec_title, str(cur_p), 1, False))

            elif task_m and doc_type == "assignment":
                task_lbl = txt[:65].strip()
                if task_lbl not in seen_sections:
                    seen_sections.add(task_lbl)
                    body_items.append((task_lbl, str(cur_p), 1, False))

            elif txt.upper() in ["REFERENCES", "LIST OF REFERENCES", "BIBLIOGRAPHY", "REFERENCES CITED"]:
                if "REFERENCES" not in seen_sections:
                    seen_sections.add("REFERENCES")
                    cur_p += 1
                    word_count = 0
                    body_items.append(("REFERENCES", str(cur_p), 0, True))

            elif any(txt.upper().startswith(ap) for ap in ["APPENDIX", "APPENDICES", "ANNEX"]):
                if "APPENDICES" not in seen_sections:
                    seen_sections.add("APPENDICES")
                    cur_p += 1
                    word_count = 0
                    body_items.append((txt[:60].upper(), str(cur_p), 0, True))

    # Fallback only if no chapters or sections could be extracted from document text
    if not body_items:
        if doc_type == "assignment":
            body_items = [
                ("Task 1: System Requirements & Theoretical Analysis", "1", 1, False),
                ("Task 2: Architectural Design & Implementation", "3", 1, False),
                ("Task 3: Verification, Testing & Discussion of Results", "6", 1, False),
                ("Conclusion & Summary", "8", 1, False),
                ("REFERENCES", "9", 0, True),
            ]
        elif doc_type == "internship":
            body_items = [
                ("CHAPTER 1: INTRODUCTION & BACKGROUND", "1", 0, True),
                ("1.1 Background of Internship", "1", 1, False),
                ("1.2 Objectives of Internship", "3", 1, False),
                ("CHAPTER 2: OVERVIEW OF HOST ORGANIZATION", "5", 0, True),
                ("2.1 Organization Structure & Profile", "5", 1, False),
                ("CHAPTER 3: INTERNSHIP ACTIVITIES", "9", 0, True),
                ("3.1 Key Tasks and Technical Implementation", "9", 1, False),
                ("CHAPTER 4: CRITICAL APPRAISAL & LESSONS LEARNT", "15", 0, True),
                ("CHAPTER 5: CONCLUSION & RECOMMENDATIONS", "20", 0, True),
                ("REFERENCES", "22", 0, True),
            ]
        elif doc_type == "proposal":
            body_items = [
                ("CHAPTER 1: INTRODUCTION", "1", 0, True),
                ("1.1 Background of the Study", "1", 1, False),
                ("1.2 Problem Statement & Objectives", "3", 1, False),
                ("CHAPTER 2: LITERATURE REVIEW", "5", 0, True),
                ("2.1 Conceptual Framework & State of the Art", "5", 1, False),
                ("CHAPTER 3: PROPOSED RESEARCH METHODOLOGY", "9", 0, True),
                ("3.1 Research Design & Architecture", "9", 1, False),
                ("REFERENCES", "13", 0, True),
            ]
        else:
            body_items = [
                ("CHAPTER 1: INTRODUCTION", "1", 0, True),
                ("1.1 Background of the Study", "1", 1, False),
                ("1.2 Problem Statement & Research Objectives", "4", 1, False),
                ("CHAPTER 2: LITERATURE REVIEW", "8", 0, True),
                ("2.1 Theoretical Framework", "8", 1, False),
                ("CHAPTER 3: MATERIALS AND METHODS", "15", 0, True),
                ("3.1 Research Design & Technical Framework", "15", 1, False),
                ("CHAPTER 4: RESULTS AND DISCUSSION", "22", 0, True),
                ("4.1 Presentation and Analysis of Results", "22", 1, False),
                ("CHAPTER 5: CONCLUSION AND RECOMMENDATIONS", "30", 0, True),
                ("REFERENCES", "33", 0, True),
            ]

    toc_items.extend(body_items)

    for title, page_str, level, is_major in toc_items:
        p_row = doc.add_paragraph()
        p_row.paragraph_format.line_spacing = 1.15
        p_row.paragraph_format.space_before = Pt(3 if is_major else 1)
        p_row.paragraph_format.space_after = Pt(2)
        
        # Word Native Tab Stop at right margin (15.0 cm) with DOT leaders
        p_row.paragraph_format.tab_stops.add_tab_stop(Cm(15.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

        left_text = title
        if is_major:
            r_lt = p_row.add_run(left_text)
            r_lt.font.name = rules.font_name
            r_lt.font.size = Pt(11.5)
            r_lt.font.bold = True
        else:
            indent = "    " * (level - 1) if level > 1 else "  "
            r_lt = p_row.add_run(indent + left_text)
            r_lt.font.name = rules.font_name
            r_lt.font.size = Pt(11)

        if page_str:
            r_p = p_row.add_run(f"\t{page_str}")
            r_p.font.name = rules.font_name
            r_p.font.size = Pt(11)
            if is_major:
                r_p.font.bold = True




def is_standalone_prelim_header(text: str) -> bool:
    """Detects if a paragraph text represents a preliminary page header, draft cover, or TOC entry."""
    t = text.strip()
    if not t:
        return False
    if len(t) > 120:
        return False

    # Check for tabbed TOC items or dot leader lines (e.g. "Chapter 1... 1" or "1.1 Introduction\t1")
    if re.search(r'\t\s*\d+\s*$', t) or re.search(r'\.{3,}\s*\d+\s*$', t) or re.search(r'\t\d+', t):
        return True

    # Check for placeholder notes or tags
    if (t.startswith('[') and t.endswith(']')) or "REQUIRES_USER_REVIEW" in t:
        return True

    # Check for signature / date placeholder lines
    if "SIGNATURE OF" in t.upper() or "DATE: ____" in t.upper() or t.startswith("_____"):
        return True

    upper = t.upper()
    prelim_headers = [
        "REPUBLIC OF CAMEROON", "REPUBLIQUE DU CAMEROUN", "PEACE – WORK – FATHERLAND",
        "PEACE - WORK - FATHERLAND", "PAIX – TRAVAIL – PATRIE", "THE UNIVERSITY OF BAMENDA",
        "L'UNIVERSITE DE BAMENDA", "COLLEGE OF TECHNOLOGY", "COLTECH",
        "FACULTY OF SCIENCE", "FACULTY OF ARTS", "FACULTY OF EDUCATION",
        "FACULTY OF ECONOMICS", "FACULTY OF LAWS", "FACULTY OF HEALTH SCIENCES",
        "HIGHER INSTITUTE", "NATIONAL HIGHER POLYTECHNIC", "COVER PAGE", "TITLE PAGE",
        "COPYRIGHT", "ALL RIGHTS RESERVED", "DECLARATION OF ORIGINALITY",
        "CERTIFICATION OF CORRECTIONS", "ACCEPTANCE OF DISSERTATION", "DEDICATION",
        "ACKNOWLEDGEMENTS", "ACKNOWLEDGMENTS", "ABSTRACT", "RÉSUMÉ", "RESUME",
        "EXECUTIVE SUMMARY", "TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES",
        "LIST OF ABBREVIATIONS", "LIST OF ACRONYMS", "LIST OF SYMBOLS"
    ]
    for h in prelim_headers:
        if h in upper and len(t) < 90:
            return True

    cover_phrases = [
        "A DISSERTATION SUBMITTED", "A FINAL YEAR PROJECT SUBMITTED",
        "A CAPSTONE PROJECT SUBMITTED", "A RESEARCH PROPOSAL SUBMITTED",
        "AN INTERNSHIP REPORT SUBMITTED", "A THESIS SUBMITTED",
        "CONTINUOUS ASSESSMENT ASSIGNMENT SUBMITTED", "IN PARTIAL FULFILLMENT",
        "REGISTRATION NUMBER:", "REGISTRATION NO:", "MATRICULE:",
        "SUPERVISOR(S):", "SUPERVISOR :", "HEAD OF DEPARTMENT :",
        "CHAIRPERSON, MASTER’S DISSERTATION", "DATE :"
    ]
    for cp in cover_phrases:
        if cp in upper and len(t) < 100:
            return True

    return False


def find_true_body_start_index(paragraphs: List[Dict[str, Any]], doc_type: str = "dissertation_bsc") -> int:
    """
    Identifies the exact index where the substantive body begins,
    skipping all draft cover pages, draft prelims, and draft TOC tables.
    """
    if not paragraphs:
        return 0

    for idx, p in enumerate(paragraphs):
        t = p.get("text", "").strip()
        if not t:
            continue

        is_ch1 = bool(re.match(r'^(?:CHAPTER|CHAPITRE)\s+(?:1|I|ONE)\b', t, re.IGNORECASE))
        is_sec1 = bool(re.match(r'^1\.1(?:\s+|$)', t))
        is_task1 = bool(re.match(r'^(?:QUESTION|TASK|EXERCISE|PROBLEM|PART)\s+(?:1|I|ONE)\b', t, re.IGNORECASE))
        is_intro = (t.upper() in ["INTRODUCTION", "1. INTRODUCTION", "1.0 INTRODUCTION"])

        if is_ch1 or is_sec1 or is_task1 or is_intro:
            if '\t' in t or re.search(r'\.{3,}\s*\d+', t) or re.search(r'\d+$', t):
                continue
            if is_standalone_prelim_header(t):
                continue

            subsequent = paragraphs[idx+1:idx+16]
            has_prelim_leak = any(
                is_standalone_prelim_header(sp.get("text", "")) and
                any(k in sp.get("text", "").upper() for k in [
                    'REPUBLIC OF CAMEROON', 'DECLARATION OF ORIGINALITY', 'TABLE OF CONTENTS',
                    'CERTIFICATION OF CORRECTIONS', 'THE UNIVERSITY OF BAMENDA'
                ])
                for sp in subsequent
            )
            has_prose = any(
                len(sp.get("text", "").strip()) > 70 and not is_standalone_prelim_header(sp.get("text", ""))
                for sp in subsequent
            )

            if not has_prelim_leak and has_prose:
                return idx

    for idx, p in enumerate(paragraphs):
        t = p.get("text", "").strip()
        if len(t) > 120 and not is_standalone_prelim_header(t):
            subsequent = paragraphs[idx:idx+10]
            if not any(
                is_standalone_prelim_header(sp.get("text", "")) and
                any(k in sp.get("text", "").upper() for k in ['REPUBLIC OF CAMEROON', 'THE UNIVERSITY OF BAMENDA'])
                for sp in subsequent
            ):
                return idx

    return 0


CH_NUM_MAP = {
    '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
    'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'SEVEN': 7,
    'UN': 1, 'DEUX': 2, 'TROIS': 3, 'QUATRE': 4, 'CINQ': 5
}

def get_standard_chapter_title(ch_num: int, doc_type: str = "dissertation_bsc") -> str:
    if ch_num == 1:
        return "INTRODUCTION"
    elif ch_num == 2:
        return "LITERATURE REVIEW"
    elif ch_num == 3:
        return "PROPOSED RESEARCH METHODOLOGY" if doc_type == "proposal" else "MATERIALS AND METHODS"
    elif ch_num == 4:
        return "RESULTS AND DISCUSSIONS"
    elif ch_num == 5:
        return "CONCLUSION AND RECOMMENDATIONS"
    return f"CHAPTER {ch_num}"


def format_body_paragraph(
    p,
    text: str,
    is_chapter: bool = False,
    is_sub1: bool = False,
    is_sub2: bool = False,
    is_ref: bool = False,
    custom_rules: Optional[CustomFormattingRules] = None
):
    """Applies UBa/custom formatting, font family, indentation, and spacing to paragraphs."""
    rules = custom_rules or CustomFormattingRules()
    p.text = ""
    p.paragraph_format.line_spacing = rules.line_spacing

    if is_chapter:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after = Pt(18)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text.upper())
        run.font.name = rules.font_name
        run.font.size = Pt(rules.heading1_size_pt)
        run.font.bold = True
    elif is_sub1:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.font.name = rules.font_name
        run.font.size = Pt(rules.heading2_size_pt)
        run.font.bold = True
    elif is_sub2:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.font.name = rules.font_name
        run.font.size = Pt(rules.font_size_pt)
        run.font.bold = True
    elif is_ref:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = min(1.15, rules.line_spacing)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        run = p.add_run(text)
        run.font.name = rules.font_name
        run.font.size = Pt(rules.font_size_pt)
    else:
        p.alignment = rules.alignment
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.font.name = rules.font_name
        run.font.size = Pt(rules.font_size_pt)


def _transfer_and_format_drawing_paragraph(
    child,
    source_docx: docx.Document,
    dest_doc: docx.Document,
    rules: CustomFormattingRules,
    current_chapter: int,
    fig_counter: Dict[int, int],
    next_raw_t: str = ""
):
    """
    Safely copies a drawing/picture paragraph from source_docx into dest_doc,
    re-linking its binary image parts to prevent broken or missing images,
    centers the figure, and provides standard academic captioning below the figure.
    """
    p_copy = copy.deepcopy(child)
    embed_attr = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'
    rel_attr = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'

    # Re-link OpenXML drawings (a:blip) and legacy VML (v:imagedata)
    for elem in p_copy.iter():
        if elem.tag.endswith('blip'):
            if embed_attr in elem.attrib:
                rId = elem.attrib[embed_attr]
                if rId in source_docx.part.related_parts:
                    src_part = source_docx.part.related_parts[rId]
                    if hasattr(src_part, 'blob'):
                        new_rId, _ = dest_doc.part.get_or_add_image(io.BytesIO(src_part.blob))
                        elem.attrib[embed_attr] = new_rId
        elif elem.tag.endswith('imagedata'):
            if rel_attr in elem.attrib:
                rId = elem.attrib[rel_attr]
                if rId in source_docx.part.related_parts:
                    src_part = source_docx.part.related_parts[rId]
                    if hasattr(src_part, 'blob'):
                        new_rId, _ = dest_doc.part.get_or_add_image(io.BytesIO(src_part.blob))
                        elem.attrib[rel_attr] = new_rId

    # Strip text runs that might be inside the drawing paragraph to keep picture clean
    for r in list(p_copy):
        if r.tag.endswith('r'):
            has_draw = any(c.tag.endswith('drawing') or c.tag.endswith('pict') for c in r.iter())
            if not has_draw:
                p_copy.remove(r)

    # Insert drawing paragraph into destination body
    dest_doc._body._body._insert_p(p_copy)
    fig_p = docx.text.paragraph.Paragraph(p_copy, dest_doc)
    fig_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fig_p.paragraph_format.space_before = Pt(14)
    fig_p.paragraph_format.space_after = Pt(4)

    # Academic Figure Captioning: placed BELOW the figure
    # Check if the next paragraph or surrounding context has a caption
    has_next_caption = bool(re.match(r'^(?:Figure|Fig\.?)\s*(?:\d+|[IVXLCDM]+)?[:.\s]', next_raw_t, re.IGNORECASE))
    if not has_next_caption and rules.auto_label_unlabeled_figures:
        ch_key = current_chapter if current_chapter > 0 else 1
        fig_counter[ch_key] = fig_counter.get(ch_key, 0) + 1
        fig_num = fig_counter[ch_key]
        caption_text = f"Figure {ch_key}.{fig_num}: System Diagram and Illustration"
        p_cap = dest_doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(4)
        p_cap.paragraph_format.space_after = Pt(14)
        r_c = p_cap.add_run(caption_text)
        r_c.font.name = rules.font_name
        r_c.font.size = Pt(10.5)
        r_c.font.bold = True
        r_c.font.italic = True


def _transfer_and_format_table(
    child,
    dest_doc: docx.Document,
    rules: CustomFormattingRules,
    current_chapter: int,
    tbl_counter: Dict[int, int],
    prev_raw_t: str = ""
):
    """
    Safely copies a table from source_docx into dest_doc,
    applies professional academic captioning ABOVE the table if missing,
    centers the table, and standardizes fonts and borders.
    """
    ch_key = current_chapter if current_chapter > 0 else 1
    # Check if preceding paragraph was an explicit table caption
    has_prev_caption = bool(re.match(r'^(?:Table|Tableau)\s*(?:\d+|[IVXLCDM]+)?[:.\s]', prev_raw_t, re.IGNORECASE))

    if not has_prev_caption:
        # Generate clean identified table caption ABOVE table
        tbl_counter[ch_key] = tbl_counter.get(ch_key, 0) + 1
        tbl_num = tbl_counter[ch_key]

        headers = []
        for tc in child.xpath('.//w:tr[1]//w:tc'):
            p_elem = tc.xpath('.//w:p')
            if p_elem:
                txt = "".join(p_elem[0].xpath('.//text()')).strip()
                if txt and len(txt) < 30:
                    headers.append(txt)

        if headers:
            cap_title = f"Summary of {', '.join(headers[:3])}"
        else:
            cap_title = "Data and Specifications Matrix"

        p_cap = dest_doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(14)
        p_cap.paragraph_format.space_after = Pt(4)
        r_c = p_cap.add_run(f"Table {ch_key}.{tbl_num}: {cap_title}")
        r_c.font.name = rules.font_name
        r_c.font.size = Pt(10.5)
        r_c.font.bold = True

    # Copy and insert table
    tbl_copy = copy.deepcopy(child)
    dest_doc._body._body._insert_tbl(tbl_copy)
    t = docx.table.Table(tbl_copy, dest_doc)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Format table text and header row
    for r_idx, row in enumerate(t.rows):
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                for run in p.runs:
                    run.font.name = rules.font_name
                    run.font.size = Pt(9.5 if len(row.cells) > 4 else 10.0)
                    if r_idx == 0:
                        run.font.bold = True
            if r_idx == 0:
                set_cell_background(cell, "F1F5F9")


def restructure_document(parsed: ParsedDocument, req: ReformatRequest, output_path: str):
    """
    Core function that builds a complete, standard-compliant UBa/COLTECH document
    (or customized document matching specific user instructions) and writes it to output_path.
    """
    doc = docx.Document()
    meta = req.metadata if req.metadata else parsed.metadata
    rules = parse_custom_formatting_rules(meta, req)

    # Set default document style font
    try:
        norm_style = doc.styles['Normal']
        norm_style.font.name = rules.font_name
        norm_style.font.size = Pt(rules.font_size_pt)
    except Exception:
        pass

    # 1. Page Dimensions & Margins Setup (Standard 4.0cm binding or custom user margin)
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(rules.margin_left_cm)
    section.right_margin = Cm(rules.margin_right_cm)
    section.top_margin = Cm(rules.margin_top_cm)
    section.bottom_margin = Cm(rules.margin_bottom_cm)

    # 2. Extract Clean Document Body Content First (for dynamic TOC & section layout)
    start_idx = find_true_body_start_index(parsed.paragraphs, req.doc_type)
    raw_body_paras = parsed.paragraphs[start_idx:]

    body_paras = []
    for p in raw_body_paras:
        txt = p.get("text", "").strip()
        if not txt:
            continue
        if is_standalone_prelim_header(txt):
            continue
        if re.search(r'\t\s*\d+\s*$', txt) or re.search(r'\.{3,}\s*\d+\s*$', txt):
            continue
        body_paras.append(p)

    # 3. Build Cover Page & Title Page (Section 0 - unnumbered)
    has_title_page = (req.doc_type not in ["internship", "assignment"])
    build_cover_page(doc, meta, req.doc_type, req.header_mode, add_page_break=has_title_page, custom_rules=rules)
    if has_title_page:
        build_cover_page(doc, meta, req.doc_type, req.header_mode, add_page_break=False, custom_rules=rules)

    # 4. Add Section Break for Preliminaries (Section 1 - centered lowerRoman from ii)
    prelim_section = doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
    prelim_section.left_margin = Cm(rules.margin_left_cm)
    prelim_section.right_margin = Cm(rules.margin_right_cm)
    prelim_section.top_margin = Cm(rules.margin_top_cm)
    prelim_section.bottom_margin = Cm(rules.margin_bottom_cm)
    prelim_section.header.is_linked_to_previous = False
    prelim_section.footer.is_linked_to_previous = False

    pgNumType_prelim = parse_xml(r'<w:pgNumType %s w:fmt="lowerRoman" w:start="2"/>' % nsdecls('w'))
    prelim_section._sectPr.append(pgNumType_prelim)

    f_p_prelim = prelim_section.footer.paragraphs[0]
    f_p_prelim.alignment = WD_ALIGN_PARAGRAPH.CENTER  # Bottom Middle!
    f_run_p = f_p_prelim.add_run()
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    f_run_p._r.append(fldChar1)
    f_run_p._r.append(instrText)
    f_run_p._r.append(fldChar2)
    f_run_p._r.append(fldChar3)
    f_run_p.font.name = rules.font_name
    f_run_p.font.size = Pt(11)

    # 5. Build Preliminaries according to Document Type
    if req.doc_type == "assignment":
        is_group_ass = bool(meta.is_group_assignment or (meta.group_members and len(meta.group_members) > 1))
        members_count = len(meta.group_members) if meta.group_members else (4 if meta.is_group_assignment else 1)
        if is_group_ass and members_count > 5:
            build_group_members_page(doc, meta)
        build_table_of_contents(doc, parsed, req.doc_type, body_paras=body_paras, custom_rules=rules)
        doc.add_page_break()
        build_assignment_acknowledgements(doc, meta)

    elif req.doc_type == "internship":
        build_internship_prelims(doc, meta, parsed)
        build_table_of_contents(doc, parsed, req.doc_type, body_paras=body_paras, custom_rules=rules)

    else:
        build_statutory_prelims(doc, meta, req.doc_type)
        build_abstract_and_resume(doc, meta, parsed)
        if req.doc_type != "proposal":
            build_dissertation_dedication_and_ack(doc, meta)
        build_table_of_contents(doc, parsed, req.doc_type, body_paras=body_paras, custom_rules=rules)

    # 6. Add Section Break for Main Body (Section 2 - centered decimal from 1)
    body_section = doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
    body_section.left_margin = Cm(rules.margin_left_cm)
    body_section.right_margin = Cm(rules.margin_right_cm)
    body_section.top_margin = Cm(rules.margin_top_cm)
    body_section.bottom_margin = Cm(rules.margin_bottom_cm)
    body_section.header.is_linked_to_previous = False
    body_section.footer.is_linked_to_previous = False

    pgNumType_body = parse_xml(r'<w:pgNumType %s w:fmt="decimal" w:start="1"/>' % nsdecls('w'))
    body_section._sectPr.append(pgNumType_body)

    # Add page number to footer of body section (Bottom Middle!)
    f_p = body_section.footer.paragraphs[0]
    f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f_run = f_p.add_run()
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    f_run._r.append(fldChar1)
    f_run._r.append(instrText)
    f_run._r.append(fldChar2)
    f_run._r.append(fldChar3)
    f_run.font.name = rules.font_name
    f_run.font.size = Pt(11)

    def format_p(p, text, is_chapter=False, is_sub1=False, is_sub2=False, is_ref=False):
        return format_body_paragraph(p, text, is_chapter=is_chapter, is_sub1=is_sub1, is_sub2=is_sub2, is_ref=is_ref, custom_rules=rules)

    source_docx = None
    if getattr(parsed, "source_path", None) and parsed.source_path.lower().endswith(".docx") and os.path.exists(parsed.source_path):
        try:
            source_docx = docx.Document(parsed.source_path)
        except Exception:
            source_docx = None

    if len(body_paras) > 0:
        current_chapter = 0
        in_references = False
        fig_counter = {}
        tbl_counter = {}
        prev_raw_t = ""

        # Find starting child index in source_docx if available
        source_start_elem_idx = -1
        if source_docx:
            first_body_txt = body_paras[0].get("text", "").strip() if body_paras else ""
            clean_first = re.sub(r'\s+', ' ', first_body_txt).strip().upper()
            if clean_first:
                for s_idx, child in enumerate(source_docx.element.body):
                    if child.tag.endswith('p'):
                        p_test = docx.text.paragraph.Paragraph(child, source_docx)
                        clean_test = re.sub(r'\s+', ' ', p_test.text).strip().upper()
                        if clean_test == clean_first:
                            source_start_elem_idx = s_idx
                            break
                if source_start_elem_idx < 0:
                    for s_idx, child in enumerate(source_docx.element.body):
                        if child.tag.endswith('p'):
                            p_test = docx.text.paragraph.Paragraph(child, source_docx)
                            clean_test = re.sub(r'\s+', ' ', p_test.text).strip().upper()
                            if clean_first[:40] in clean_test or clean_test[:40] in clean_first:
                                source_start_elem_idx = s_idx
                                break
            if source_start_elem_idx < 0:
                for s_idx, child in enumerate(source_docx.element.body):
                    if child.tag.endswith('p'):
                        p_test = docx.text.paragraph.Paragraph(child, source_docx)
                        txt_up = p_test.text.strip().upper()
                        if re.match(r'^(?:CHAPTER\s+1|CHAPITRE\s+1|1\.1\b)', txt_up):
                            source_start_elem_idx = s_idx
                            break
            if source_start_elem_idx < 0:
                for s_idx, child in enumerate(source_docx.element.body):
                    if child.tag.endswith('p'):
                        p_test = docx.text.paragraph.Paragraph(child, source_docx)
                        txt_val = p_test.text.strip()
                        if txt_val and not is_standalone_prelim_header(txt_val):
                            source_start_elem_idx = s_idx
                            break
                if source_start_elem_idx < 0:
                    source_start_elem_idx = 0

        # Auto-inject Chapter 1 heading if missing
        first_text = body_paras[0].get("text", "").strip() if body_paras else ""
        has_explicit_ch1 = bool(re.match(r'^(?:CHAPTER|CHAPITRE)\s+(?:1|I|ONE)\b', first_text, re.IGNORECASE))
        is_sub_1_1 = bool(re.match(r'^1\.[01](?:\s+|$)', first_text))
        if is_sub_1_1 and not has_explicit_ch1 and req.doc_type != "assignment":
            p_ch1 = doc.add_paragraph()
            format_p(p_ch1, "CHAPTER 1\nINTRODUCTION", is_chapter=True)
            current_chapter = 1

        if source_docx and source_start_elem_idx >= 0:
            children = source_docx.element.body[source_start_elem_idx:]
            total_children = len(children)
            skip_next_elem = False

            for c_idx, child in enumerate(children):
                if skip_next_elem:
                    skip_next_elem = False
                    continue

                next_raw_t = ""
                for next_idx in range(c_idx + 1, min(c_idx + 3, total_children)):
                    if children[next_idx].tag.endswith('p'):
                        p_next = docx.text.paragraph.Paragraph(children[next_idx], source_docx)
                        if p_next.text.strip():
                            next_raw_t = p_next.text.strip()
                            break

                if child.tag.endswith('tbl'):
                    _transfer_and_format_table(child, doc, rules, current_chapter, tbl_counter, prev_raw_t=prev_raw_t)
                    prev_raw_t = ""
                    continue

                elif child.tag.endswith('p'):
                    sp = docx.text.paragraph.Paragraph(child, source_docx)
                    raw_t = sp.text.strip()
                    has_drawing = bool(child.xpath('.//w:drawing') or child.xpath('.//w:pict'))

                    if not raw_t and not has_drawing:
                        continue

                    if has_drawing:
                        _transfer_and_format_drawing_paragraph(
                            child, source_docx, doc, rules, current_chapter, fig_counter, next_raw_t=next_raw_t or raw_t
                        )
                        prev_raw_t = raw_t
                        continue

                    if is_standalone_prelim_header(raw_t):
                        continue
                    if re.search(r'\t\s*\d+\s*$', raw_t) or re.search(r'\.{3,}\s*\d+\s*$', raw_t):
                        continue

                    # Explicit figure caption
                    if re.match(r'^(?:Figure|Fig\.?)\s*(?:\d+|[IVXLCDM]+)?[:.\s]', raw_t, re.IGNORECASE):
                        p_cap = doc.add_paragraph()
                        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_cap.paragraph_format.space_before = Pt(4)
                        p_cap.paragraph_format.space_after = Pt(14)
                        r_c = p_cap.add_run(raw_t)
                        r_c.font.name = rules.font_name
                        r_c.font.size = Pt(10.5)
                        r_c.font.bold = True
                        r_c.font.italic = True
                        prev_raw_t = raw_t
                        continue

                    # Explicit table caption
                    if re.match(r'^(?:Table|Tableau)\s*(?:\d+|[IVXLCDM]+)?[:.\s]', raw_t, re.IGNORECASE):
                        p_cap = doc.add_paragraph()
                        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_cap.paragraph_format.space_before = Pt(14)
                        p_cap.paragraph_format.space_after = Pt(4)
                        r_c = p_cap.add_run(raw_t)
                        r_c.font.name = rules.font_name
                        r_c.font.size = Pt(10.5)
                        r_c.font.bold = True
                        prev_raw_t = raw_t
                        continue

                    # References header check
                    if raw_t.upper() in ["REFERENCES", "LIST OF REFERENCES", "BIBLIOGRAPHY", "REFERENCES CITED"]:
                        p_elem = doc.add_paragraph()
                        p_elem.paragraph_format.page_break_before = True
                        format_p(p_elem, "REFERENCES", is_chapter=True)
                        in_references = True
                        current_chapter = 99
                        prev_raw_t = raw_t
                        continue

                    # Appendices header check
                    if any(raw_t.upper().startswith(ap) for ap in ["APPENDIX", "APPENDICES", "ANNEX"]):
                        p_elem = doc.add_paragraph()
                        p_elem.paragraph_format.page_break_before = True
                        format_p(p_elem, raw_t.upper(), is_chapter=True)
                        in_references = False
                        current_chapter = 100
                        prev_raw_t = raw_t
                        continue

                    # Explicit chapter heading
                    ch_match = re.match(
                        r'^(?:CHAPTER|CHAPITRE)\s+([0-9]+|[IVXLCDM]+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|UN|DEUX|TROIS|QUATRE|CINQ)\b(?:\s*[:\-–—]\s*|\s*)(.*)$',
                        raw_t,
                        re.IGNORECASE
                    )
                    explicit_ch_num = None
                    if ch_match:
                        num_str = ch_match.group(1).upper()
                        explicit_ch_num = CH_NUM_MAP.get(num_str, int(num_str) if num_str.isdigit() else 1)

                    if explicit_ch_num is not None:
                        ch_sub = ch_match.group(2).strip().upper() if ch_match.group(2) else ""
                        if not ch_sub and next_raw_t:
                            if not re.match(r'^\d+\.\d+', next_raw_t) and not re.match(r'^(?:CHAPTER|CHAPITRE|Table|Figure)\b', next_raw_t, re.IGNORECASE) and len(next_raw_t) < 80:
                                ch_sub = next_raw_t.strip().upper()
                                skip_next_elem = True
                        if not ch_sub:
                            ch_sub = get_standard_chapter_title(explicit_ch_num, req.doc_type)

                        if explicit_ch_num == 1 and next_raw_t and INTRO_HEADING_PATTERN.match(next_raw_t.strip()):
                            skip_next_elem = True

                        p_elem = doc.add_paragraph()
                        if explicit_ch_num > 1:
                            p_elem.paragraph_format.page_break_before = True
                        ch_text = f"CHAPTER {explicit_ch_num}" + (f"\n{ch_sub}" if ch_sub else "")
                        format_p(p_elem, ch_text, is_chapter=True)
                        current_chapter = explicit_ch_num
                        in_references = False
                        prev_raw_t = raw_t
                        continue

                    # Standalone Introduction heading deduplication (prevents extra INTRODUCTION on first page)
                    if INTRO_HEADING_PATTERN.match(raw_t.strip()):
                        if current_chapter >= 1:
                            continue
                        elif current_chapter == 0 and req.doc_type != "assignment" and not in_references:
                            p_elem = doc.add_paragraph()
                            format_p(p_elem, "CHAPTER 1\nINTRODUCTION", is_chapter=True)
                            current_chapter = 1
                            prev_raw_t = raw_t
                            continue

                    # Standalone conclusion heading
                    concl_match = re.match(r'^(?:CONCLUSION|CONCLUSIONS)\b(?:\s*[:\-–—,\s])*(.*)$', raw_t, re.IGNORECASE)
                    if concl_match and current_chapter < 5 and req.doc_type != "assignment" and not in_references:
                        concl_sub = concl_match.group(1).strip().upper() if concl_match.group(1) else ""
                        if not concl_sub:
                            concl_sub = "CONCLUSION AND RECOMMENDATIONS"
                        p_elem = doc.add_paragraph()
                        p_elem.paragraph_format.page_break_before = True
                        format_p(p_elem, f"CHAPTER 5\n{concl_sub}", is_chapter=True)
                        current_chapter = 5
                        in_references = False
                        prev_raw_t = raw_t
                        continue

                    # Section promotion (only if chapter heading was omitted in manuscript)
                    sec_match = re.match(r'^([1-5])\.1(?:\s+|$)', raw_t)
                    if sec_match and req.doc_type != "assignment" and not in_references:
                        sec_ch_num = int(sec_match.group(1))
                        if sec_ch_num > current_chapter:
                            p_ch = doc.add_paragraph()
                            if sec_ch_num > 1:
                                p_ch.paragraph_format.page_break_before = True
                            ch_title = f"CHAPTER {sec_ch_num}\n{get_standard_chapter_title(sec_ch_num, req.doc_type)}"
                            format_p(p_ch, ch_title, is_chapter=True)
                            current_chapter = sec_ch_num

                    # Format paragraph
                    p_elem = doc.add_paragraph()
                    lvl = 0
                    is_h = False
                    style_name = sp.style.name if sp.style else "Normal"
                    if "Heading 1" in style_name or (sp.runs and sp.runs[0].bold and sp.runs[0].font.size and sp.runs[0].font.size.pt >= 14):
                        is_h = True
                        lvl = 1
                    elif "Heading 2" in style_name or re.match(r'^\d+\.\d+\s', raw_t):
                        is_h = True
                        lvl = 2
                    elif "Heading 3" in style_name or re.match(r'^\d+\.\d+\.\d+\s', raw_t):
                        is_h = True
                        lvl = 3

                    if in_references:
                        format_p(p_elem, raw_t, is_ref=True)
                    elif is_h:
                        if lvl == 1 or re.match(r'^(?:CHAPTER|CHAPITRE)\b', raw_t, re.IGNORECASE):
                            format_p(p_elem, raw_t, is_chapter=True)
                        elif lvl == 2:
                            format_p(p_elem, raw_t, is_sub1=True)
                        else:
                            format_p(p_elem, raw_t, is_sub2=True)
                    else:
                        format_p(p_elem, raw_t)
                    
                    prev_raw_t = raw_t
        else:
            # Fallback for plain body_paras (e.g. from PDF)
            skip_next_p = False
            for p_idx, p_info in enumerate(body_paras):
                if skip_next_p:
                    skip_next_p = False
                    continue
                raw_t = p_info["text"].strip()
                next_p_text = body_paras[p_idx + 1]["text"].strip() if p_idx + 1 < len(body_paras) else ""

                if raw_t.upper() in ["REFERENCES", "LIST OF REFERENCES", "BIBLIOGRAPHY", "REFERENCES CITED"]:
                    p_elem = doc.add_paragraph()
                    p_elem.paragraph_format.page_break_before = True
                    format_p(p_elem, "REFERENCES", is_chapter=True)
                    in_references = True
                    current_chapter = 99
                    continue
                if any(raw_t.upper().startswith(ap) for ap in ["APPENDIX", "APPENDICES", "ANNEX"]):
                    p_elem = doc.add_paragraph()
                    p_elem.paragraph_format.page_break_before = True
                    format_p(p_elem, raw_t.upper(), is_chapter=True)
                    in_references = False
                    current_chapter = 100
                    continue

                ch_match = re.match(
                    r'^(?:CHAPTER|CHAPITRE)\s+([0-9]+|[IVXLCDM]+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|UN|DEUX|TROIS|QUATRE|CINQ)\b(?:\s*[:\-–—]\s*|\s*)(.*)$',
                    raw_t,
                    re.IGNORECASE
                )
                explicit_ch_num = None
                if ch_match:
                    num_str = ch_match.group(1).upper()
                    explicit_ch_num = CH_NUM_MAP.get(num_str, int(num_str) if num_str.isdigit() else 1)

                if explicit_ch_num is not None:
                    ch_sub = ch_match.group(2).strip().upper() if ch_match.group(2) else ""
                    if not ch_sub and next_p_text:
                        if not re.match(r'^\d+\.\d+', next_p_text) and not re.match(r'^(?:CHAPTER|CHAPITRE|Table|Figure)\b', next_p_text, re.IGNORECASE) and len(next_p_text) < 80:
                            ch_sub = next_p_text.strip().upper()
                            skip_next_p = True
                    if not ch_sub:
                        ch_sub = get_standard_chapter_title(explicit_ch_num, req.doc_type)

                    if explicit_ch_num == 1 and next_p_text and INTRO_HEADING_PATTERN.match(next_p_text.strip()):
                        skip_next_p = True

                    p_elem = doc.add_paragraph()
                    if explicit_ch_num > 1:
                        p_elem.paragraph_format.page_break_before = True
                    ch_text = f"CHAPTER {explicit_ch_num}" + (f"\n{ch_sub}" if ch_sub else "")
                    format_p(p_elem, ch_text, is_chapter=True)
                    current_chapter = explicit_ch_num
                    in_references = False
                    continue

                # Standalone Introduction heading deduplication (prevents extra INTRODUCTION on first page)
                if INTRO_HEADING_PATTERN.match(raw_t.strip()):
                    if current_chapter >= 1:
                        continue
                    elif current_chapter == 0 and req.doc_type != "assignment" and not in_references:
                        p_elem = doc.add_paragraph()
                        format_p(p_elem, "CHAPTER 1\nINTRODUCTION", is_chapter=True)
                        current_chapter = 1
                        continue

                concl_match = re.match(r'^(?:CONCLUSION|CONCLUSIONS)\b(?:\s*[:\-–—,\s])*(.*)$', raw_t, re.IGNORECASE)
                if concl_match and current_chapter < 5 and req.doc_type != "assignment" and not in_references:
                    concl_sub = concl_match.group(1).strip().upper() if concl_match.group(1) else ""
                    if not concl_sub:
                        concl_sub = "CONCLUSION AND RECOMMENDATIONS"
                    p_elem = doc.add_paragraph()
                    p_elem.paragraph_format.page_break_before = True
                    format_p(p_elem, f"CHAPTER 5\n{concl_sub}", is_chapter=True)
                    current_chapter = 5
                    in_references = False
                    continue

                sec_match = re.match(r'^([1-5])\.1(?:\s+|$)', raw_t)
                if sec_match and req.doc_type != "assignment" and not in_references:
                    sec_ch_num = int(sec_match.group(1))
                    if sec_ch_num > current_chapter:
                        p_ch = doc.add_paragraph()
                        if sec_ch_num > 1:
                            p_ch.paragraph_format.page_break_before = True
                        ch_title = f"CHAPTER {sec_ch_num}\n{get_standard_chapter_title(sec_ch_num, req.doc_type)}"
                        format_p(p_ch, ch_title, is_chapter=True)
                        current_chapter = sec_ch_num

                p_elem = doc.add_paragraph()
                if in_references:
                    format_p(p_elem, raw_t, is_ref=True)
                elif p_info.get("is_heading"):
                    lvl = p_info.get("level", 1)
                    if lvl == 1 or re.match(r'^(?:CHAPTER|CHAPITRE)\b', raw_t, re.IGNORECASE):
                        format_p(p_elem, raw_t, is_chapter=True)
                    elif lvl == 2:
                        format_p(p_elem, raw_t, is_sub1=True)
                    else:
                        format_p(p_elem, raw_t, is_sub2=True)
                else:
                    format_p(p_elem, raw_t)
    else:
        # Default starter content if uploaded document had very few paragraphs
        p_ch1 = doc.add_paragraph()
        format_p(p_ch1, "CHAPTER 1\nINTRODUCTION", is_chapter=True)
        
        p_s1 = doc.add_paragraph()
        format_p(p_s1, "1.1 Background of the Study", is_sub1=True)
        
        p_b1 = doc.add_paragraph()
        format_p(p_b1, f"The University of Bamenda was established to drive excellence in higher education and professional training. Under {meta.faculty}, research and technical implementation are closely aligned with national development objectives. This work titled “{meta.title}” investigates key architectural principles and system methodologies.")

    doc.save(output_path)
    return output_path

