"""
Restructuring Engine for The University of Bamenda (UBa) and College of Technology (COLTECH).
Generates compliant DOCX manuscripts conforming to official Senate and Establishment regulations.
"""
import os
import re
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

def add_boxed_title(doc: docx.Document, title_text: str):
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
    r.font.name = "Times New Roman"
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


def build_cover_page(doc: docx.Document, meta: DocumentMetadata, doc_type: str = "dissertation_bsc", header_mode: str = "center_crest", add_page_break: bool = True):
    """Builds the official Cover Page conforming strictly to UBa and Establishment specifications."""
    add_header_banner(doc, meta, doc_type, header_mode)

    # Document Title in a clean rectangular single-line box
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(10)
    p_sp.paragraph_format.space_after = Pt(2)
    add_boxed_title(doc, meta.title)

    # Purpose Clause
    p_clause = doc.add_paragraph()
    p_clause.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_clause.paragraph_format.space_before = Pt(8)
    p_clause.paragraph_format.space_after = Pt(16)
    p_clause.paragraph_format.line_spacing = 1.3
    
    r_clause = p_clause.add_run(get_purpose_clause(doc_type, meta))
    r_clause.font.name = "Times New Roman"
    r_clause.font.size = Pt(12)

    # Candidate / Group / Supervision Section
    if doc_type == "assignment":
        is_group_ass = bool(meta.is_group_assignment or (meta.group_members and len(meta.group_members) > 1))

        if is_group_ass:
            members = meta.group_members if meta.group_members else []
            if not members:
                # Default group representative members when user toggles group mode
                members = [
                    GroupMember(name=meta.author, matricule=meta.reg_number, participation="Lead / Coordinator", grade="____ / 20"),
                    GroupMember(name="TANIFUM DONALD-HOPE NEBA", matricule="UBa23PH045", participation="System Architecture", grade="____ / 20"),
                    GroupMember(name="BIH CLAUDIA LUM", matricule="UBa24EN102", participation="Frontend & Testing", grade="____ / 20"),
                    GroupMember(name="NDIFOR KEVIN TITA", matricule="UBa24EN155", participation="Documentation", grade="____ / 20"),
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
        members = [
            GroupMember(name=meta.author, matricule=meta.reg_number, participation="Lead / Coordinator", grade="____ / 20"),
            GroupMember(name="TANIFUM DONALD-HOPE NEBA", matricule="UBa23PH045", participation="System Architecture", grade="____ / 20"),
            GroupMember(name="BIH CLAUDIA LUM", matricule="UBa24EN102", participation="Frontend & Testing", grade="____ / 20"),
            GroupMember(name="NDIFOR KEVIN TITA", matricule="UBa24EN155", participation="Documentation", grade="____ / 20"),
            GroupMember(name="FORBAH BRIAN CHE", matricule="UBa24EN210", participation="Database & Cloud Services", grade="____ / 20"),
            GroupMember(name="NGWA PRECIOUS SIRRI", matricule="UBa24EN289", participation="Literature & Verification", grade="____ / 20"),
            GroupMember(name="FON DESMOND ACHA", matricule="UBa24EN312", participation="Statistical Evaluation", grade="____ / 20"),
            GroupMember(name="MBIYDZENYUY KAREN", matricule="UBa24EN340", participation="Quality Assurance", grade="____ / 20"),
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
    r_dtx.font.italic = True

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
        sup_main = meta.supervisors[0] if meta.supervisors else "Pr. CHARLES FORBACHA"
        sup_rank = meta.supervisor_ranks[0] if meta.supervisor_ranks else "Associate Professor"
        
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
    r_dtx.font.italic = True

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

    p_fr_title = doc.add_paragraph()
    p_fr_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fr_title.paragraph_format.space_after = Pt(14)
    r_fr_title = p_fr_title.add_run(f"« {meta.title.upper()} »")
    r_fr_title.font.name = "Times New Roman"
    r_fr_title.font.size = Pt(12.5)
    r_fr_title.font.bold = True

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


def build_table_of_contents(doc: docx.Document, parsed: ParsedDocument, doc_type: str = "dissertation_bsc", body_paras: Optional[List[Dict[str, Any]]] = None):
    """Builds a formatted, dynamically accurate Table of Contents with dot leaders and aligned pages."""
    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_h.paragraph_format.space_before = Pt(20)
    p_h.paragraph_format.space_after = Pt(24)
    r_h = p_h.add_run("TABLE OF CONTENTS")
    r_h.font.name = "Times New Roman"
    r_h.font.size = Pt(14)
    r_h.font.bold = True

    toc_items = []
    
    if doc_type == "assignment":
        toc_items = [
            ("PRELIMINARY PAGES", "", 0, True),
            ("Acknowledgements", "ii", 1, False),
            ("ASSIGNMENT TASKS & QUESTIONS", "1", 0, True),
        ]
        task_found = False
        if body_paras:
            cur_p = 1
            w_count = 0
            for bp in body_paras:
                txt = bp.get("text", "").strip()
                w_count += len(txt.split())
                is_task = bool(re.match(r'^(?:QUESTION|TASK|EXERCISE|PROBLEM|PART|SECTION)\s*(?:\d+|[IVXLCDM]+)?[:.\s]', txt, re.IGNORECASE))
                is_h = bp.get("is_heading", False) and len(txt) < 80 and not any(k in txt.upper() for k in ["REPUBLIC", "UNIVERSITY", "TABLE OF CONTENTS", "ACKNOWLEDGEMENTS"])
                if is_task or (is_h and bp.get("level", 1) <= 2):
                    task_found = True
                    clean_lbl = txt[:60]
                    toc_items.append((clean_lbl, str(cur_p), 1, False))
                if w_count > 320:
                    cur_p += max(1, w_count // 320)
                    w_count = w_count % 320
        if not task_found:
            toc_items.extend([
                ("Task 1: System Requirements & Theoretical Analysis", "1", 1, False),
                ("Task 2: Architectural Design & Implementation", "3", 1, False),
                ("Task 3: Verification, Testing & Discussion of Results", "6", 1, False),
                ("Conclusion & Summary", "8", 1, False),
            ])
        toc_items.append(("REFERENCES", str(cur_p if (body_paras and task_found) else 9), 0, True))

    elif doc_type == "proposal":
        toc_items = [
            ("PRELIMINARY PAGES", "", 0, True),
            ("Declaration of Originality of Proposal", "ii", 1, False),
            ("Abstract", "iii", 1, False),
            ("Résumé", "iv", 1, False),
            ("Table of Contents", "v", 1, False),
            ("List of Abbreviations", "vi", 1, False),
            ("List of Tables", "vii", 1, False),
            ("List of Figures", "viii", 1, False),
        ]
        sections_found = False
        if body_paras:
            cur_p = 1
            w_count = 0
            cur_ch = 0
            for bp in body_paras:
                txt = bp.get("text", "").strip()
                w_count += len(txt.split())
                ch_m = re.match(r'^(?:CHAPTER|CHAPITRE)\s+(\d+|[IVXLCDM]+)(?:\s*[:\-–]\s*|\s+)(.*)$', txt, re.IGNORECASE)
                sec_m = re.match(r'^([1-3])\.\d+\s+(.*)$', txt)
                is_ref = txt.upper() in ["REFERENCES", "BIBLIOGRAPHY"]
                if ch_m:
                    sections_found = True
                    num_str = ch_m.group(1).upper()
                    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}
                    ch_num = roman_map.get(num_str, int(num_str) if num_str.isdigit() else 1)
                    if ch_num > 1 and ch_num > cur_ch:
                        cur_p += 1
                        w_count = 0
                    cur_ch = ch_num
                    sub = ch_m.group(2).strip()
                    toc_items.append((f"CHAPTER {ch_num}: {sub}".upper(), str(cur_p), 0, True))
                elif sec_m:
                    sec_ch = int(sec_m.group(1))
                    if sec_ch > cur_ch:
                        if cur_ch > 0:
                            cur_p += 1
                            w_count = 0
                        cur_ch = sec_ch
                        ch_names = {1: "INTRODUCTION", 2: "LITERATURE REVIEW", 3: "PROPOSED RESEARCH METHODOLOGY"}
                        toc_items.append((f"CHAPTER {sec_ch}: {ch_names.get(sec_ch, '')}", str(cur_p), 0, True))
                    if bp.get("level", 2) <= 2 or re.match(r'^\d+\.\d+\s', txt):
                        sections_found = True
                        toc_items.append((txt[:60], str(cur_p), 1, False))
                elif is_ref:
                    cur_p += 1
                    w_count = 0
                    toc_items.append(("REFERENCES", str(cur_p), 0, True))
                if w_count > 320:
                    cur_p += max(1, w_count // 320)
                    w_count = w_count % 320
        if not sections_found:
            toc_items.extend([
                ("CHAPTER 1: INTRODUCTION", "1", 0, True),
                ("1.1 Background of the Study", "1", 1, False),
                ("1.2 Description of the Research Problem", "2", 1, False),
                ("1.3 Research Questions and Objectives", "2", 1, False),
                ("1.4 Rationale (Significance and Motivation)", "3", 1, False),
                ("1.5 Scope and Delimitations", "3", 1, False),
                ("CHAPTER 2: LITERATURE REVIEW", "5", 0, True),
                ("2.1 Conceptual and Theoretical Framework", "5", 1, False),
                ("2.2 Review of State of the Art and Approaches", "5", 1, False),
                ("2.3 Summary and Research Gaps Identified", "6", 1, False),
                ("CHAPTER 3: PROPOSED RESEARCH METHODOLOGY", "7", 0, True),
                ("3.1 Research Design & Architecture Overview", "7", 1, False),
                ("3.2 Data Collection, Datasets & Tools", "8", 1, False),
                ("3.3 Model Development & Evaluation Metrics", "8", 1, False),
                ("3.4 Ethical Considerations & Indicative Timeline", "9", 1, False),
                ("REFERENCES", "10", 0, True),
                ("APPENDICES", "12", 0, True),
            ])

    elif doc_type == "internship":
        toc_items = [
            ("PRELIMINARY PAGES", "", 0, True),
            ("Attestation of Internship Completion", "ii", 1, False),
            ("Declaration of Originality", "iii", 1, False),
            ("Dedication & Acknowledgements", "iv", 1, False),
            ("Executive Summary", "v", 1, False),
            ("Table of Contents", "vi", 1, False),
            ("List of Abbreviations & Acronyms", "vii", 1, False),
            ("List of Tables", "viii", 1, False),
            ("List of Figures", "ix", 1, False),
            ("CHAPTER 1: INTRODUCTION", "1", 0, True),
            ("1.1 Background of Internship", "1", 1, False),
            ("1.2 Objectives of Internship", "3", 1, False),
            ("1.3 Significance of Internship", "4", 1, False),
            ("1.4 Organization of Internship", "6", 1, False),
            ("1.5 Definition of Terms", "8", 1, False),
            ("CHAPTER 2: OVERVIEW OF THE HOST ORGANIZATION", "10", 0, True),
            ("2.1 Brief History and Evolution", "10", 1, False),
            ("2.2 Organizational Structure and Governance", "13", 1, False),
            ("2.3 Products and Services Offered", "16", 1, False),
            ("CHAPTER 3: INTERNSHIP ACTIVITIES", "19", 0, True),
            ("3.1 Core Tasks & Departmental Activities", "19", 1, False),
            ("3.2 Challenges & Difficulties Encountered", "25", 1, False),
            ("CHAPTER 4: SITUATIONAL & CRITICAL APPRAISAL", "28", 0, True),
            ("4.1 SWOT Analysis of the Enterprise", "28", 1, False),
            ("4.2 Assessment of the Internship (Lessons Learnt)", "32", 1, False),
            ("CHAPTER 5: CONCLUSION AND RECOMMENDATIONS", "35", 0, True),
            ("5.1 Summary of Experience", "35", 1, False),
            ("5.2 Conclusion", "36", 1, False),
            ("5.3 Actionable Recommendations", "37", 1, False),
            ("LIST OF REFERENCES", "40", 0, True),
            ("APPENDICES", "42", 0, True),
        ]
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
            ("List of Tables", "ix", 1, False),
            ("List of Figures", "x", 1, False),
            ("List of Abbreviations & Acronyms", "xi", 1, False),
        ]
        sections_found = False
        if body_paras:
            cur_p = 1
            w_count = 0
            cur_ch = 0
            for bp in body_paras:
                txt = bp.get("text", "").strip()
                w_count += len(txt.split())
                ch_m = re.match(r'^(?:CHAPTER|CHAPITRE)\s+(\d+|[IVXLCDM]+)(?:\s*[:\-–]\s*|\s+)(.*)$', txt, re.IGNORECASE)
                sec_m = re.match(r'^([1-5])\.\d+\s+(.*)$', txt)
                is_ref = txt.upper() in ["REFERENCES", "BIBLIOGRAPHY"]
                if ch_m:
                    sections_found = True
                    num_str = ch_m.group(1).upper()
                    roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6}
                    ch_num = roman_map.get(num_str, int(num_str) if num_str.isdigit() else 1)
                    if ch_num > 1 and ch_num > cur_ch:
                        cur_p += 1
                        w_count = 0
                    cur_ch = ch_num
                    sub = ch_m.group(2).strip()
                    toc_items.append((f"CHAPTER {ch_num}: {sub}".upper(), str(cur_p), 0, True))
                elif sec_m:
                    sec_ch = int(sec_m.group(1))
                    if sec_ch > cur_ch:
                        if cur_ch > 0:
                            cur_p += 1
                            w_count = 0
                        cur_ch = sec_ch
                        ch_names = {
                            1: "INTRODUCTION", 2: "LITERATURE REVIEW",
                            3: "MATERIALS AND METHODS", 4: "RESULTS AND DISCUSSIONS",
                            5: "CONCLUSION AND RECOMMENDATIONS"
                        }
                        toc_items.append((f"CHAPTER {sec_ch}: {ch_names.get(sec_ch, '')}", str(cur_p), 0, True))
                    if bp.get("level", 2) <= 2 or re.match(r'^\d+\.\d+\s', txt):
                        sections_found = True
                        toc_items.append((txt[:60], str(cur_p), 1, False))
                elif is_ref:
                    cur_p += 1
                    w_count = 0
                    toc_items.append(("REFERENCES", str(cur_p), 0, True))
                if w_count > 320:
                    cur_p += max(1, w_count // 320)
                    w_count = w_count % 320
        if not sections_found:
            toc_items.extend([
                ("CHAPTER 1: INTRODUCTION", "1", 0, True),
                ("1.1 Background of the Study", "1", 1, False),
                ("1.2 Description of Research Problem Area(s)", "4", 1, False),
                ("1.3 Research Questions and Objectives", "6", 1, False),
                ("1.4 Rationale (Justification, Motivation, Significance)", "9", 1, False),
                ("1.5 Scope and Limitations of the Study", "11", 1, False),
                ("CHAPTER 2: LITERATURE REVIEW", "14", 0, True),
                ("2.1 Theoretical Framework", "14", 1, False),
                ("2.2 Empirical Review of Related Works", "19", 1, False),
                ("2.3 Summary of Knowledge Gaps", "26", 1, False),
                ("CHAPTER 3: MATERIALS AND METHODS", "29", 0, True),
                ("3.1 Research Design & Framework", "29", 1, False),
                ("3.2 Description of Study Site & Materials", "32", 1, False),
                ("3.3 Procedures, Ethical Considerations & Statistical Analysis", "36", 1, False),
                ("CHAPTER 4: RESULTS AND DISCUSSIONS", "41", 0, True),
                ("4.1 Presentation and Statistical Analysis of Data", "41", 1, False),
                ("4.2 Interpretation and Discussion of Findings", "52", 1, False),
                ("CHAPTER 5: CONCLUSION, RECOMMENDATIONS & PERSPECTIVES", "65", 0, True),
                ("5.1 Conclusions", "65", 1, False),
                ("5.2 Recommendations", "67", 1, False),
                ("5.3 Perspectives for Future Research", "69", 1, False),
                ("REFERENCES", "71", 0, True),
                ("APPENDICES", "78", 0, True),
            ])

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
            r_lt.font.name = "Times New Roman"
            r_lt.font.size = Pt(11.5)
            r_lt.font.bold = True
        else:
            indent = "    " * (level - 1) if level > 1 else "  "
            r_lt = p_row.add_run(indent + left_text)
            r_lt.font.name = "Times New Roman"
            r_lt.font.size = Pt(11)

        if page_str:
            r_p = p_row.add_run(f"\t{page_str}")
            r_p.font.name = "Times New Roman"
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


def format_body_paragraph(p, text: str, is_chapter: bool = False, is_sub1: bool = False, is_sub2: bool = False, is_ref: bool = False):
    """Applies strict UBa Times New Roman formatting, indentation, and spacing to paragraphs."""
    p.text = ""
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE

    if is_chapter:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(24)
        p.paragraph_format.space_after = Pt(18)
        run = p.add_run(text.upper())
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)
        run.font.bold = True
    elif is_sub1:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.bold = True
    elif is_sub2:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.bold = True
    elif is_ref:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


def restructure_document(parsed: ParsedDocument, req: ReformatRequest, output_path: str):
    """
    Core function that builds a complete, standard-compliant UBa/COLTECH document
    and writes it to output_path.
    """
    doc = docx.Document()

    # 1. Page Dimensions & 4.0 cm Binding Margin Setup
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(4.0)   # Mandatory 4.0 cm inner binding margin
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    meta = req.metadata if req.metadata else parsed.metadata

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
    build_cover_page(doc, meta, req.doc_type, req.header_mode, add_page_break=has_title_page)
    if has_title_page:
        build_cover_page(doc, meta, req.doc_type, req.header_mode, add_page_break=False)

    # 4. Add Section Break for Preliminaries (Section 1 - centered lowerRoman from ii)
    prelim_section = doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
    prelim_section.left_margin = Cm(4.0)
    prelim_section.right_margin = Cm(2.0)
    prelim_section.top_margin = Cm(2.0)
    prelim_section.bottom_margin = Cm(2.0)
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
    f_run_p.font.name = "Times New Roman"
    f_run_p.font.size = Pt(11)

    # 5. Build Preliminaries according to Document Type
    if req.doc_type == "assignment":
        is_group_ass = bool(meta.is_group_assignment or (meta.group_members and len(meta.group_members) > 1))
        members_count = len(meta.group_members) if meta.group_members else (4 if meta.is_group_assignment else 1)
        if is_group_ass and members_count > 5:
            build_group_members_page(doc, meta)
        build_table_of_contents(doc, parsed, req.doc_type, body_paras=body_paras)
        doc.add_page_break()
        build_assignment_acknowledgements(doc, meta)

    elif req.doc_type == "internship":
        build_internship_prelims(doc, meta, parsed)
        build_table_of_contents(doc, parsed, req.doc_type, body_paras=body_paras)

    else:
        build_statutory_prelims(doc, meta, req.doc_type)
        build_abstract_and_resume(doc, meta, parsed)
        if req.doc_type != "proposal":
            build_dissertation_dedication_and_ack(doc, meta)
        build_table_of_contents(doc, parsed, req.doc_type, body_paras=body_paras)

    # 6. Add Section Break for Main Body (Section 2 - centered decimal from 1)
    body_section = doc.add_section(docx.enum.section.WD_SECTION.NEW_PAGE)
    body_section.left_margin = Cm(4.0)
    body_section.right_margin = Cm(2.0)
    body_section.top_margin = Cm(2.0)
    body_section.bottom_margin = Cm(2.0)
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
    f_run.font.name = "Times New Roman"
    f_run.font.size = Pt(11)

    source_docx = None
    if getattr(parsed, "source_path", None) and parsed.source_path.lower().endswith(".docx") and os.path.exists(parsed.source_path):
        try:
            source_docx = docx.Document(parsed.source_path)
        except Exception:
            source_docx = None

    if len(body_paras) > 5:
        current_chapter = 0
        in_references = False

        # Find starting child index in source_docx if available
        source_start_elem_idx = -1
        if source_docx:
            first_body_txt = body_paras[0].get("text", "").strip() if body_paras else ""
            clean_first = re.sub(r'\s+', ' ', first_body_txt).strip().upper()
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
                        txt_up = p_test.text.strip().upper()
                        if re.match(r'^(?:CHAPTER\s+1|CHAPITRE\s+1|1\.1\b)', txt_up):
                            source_start_elem_idx = s_idx
                            break

        # Auto-inject Chapter 1 heading if missing
        first_text = body_paras[0].get("text", "").strip() if body_paras else ""
        has_explicit_ch1 = bool(re.match(r'^(?:CHAPTER|CHAPITRE)\s+(?:1|I|ONE)\b', first_text, re.IGNORECASE))
        is_sub_1_1 = bool(re.match(r'^1\.[01](?:\s+|$)', first_text))
        if is_sub_1_1 and not has_explicit_ch1 and req.doc_type != "assignment":
            p_ch1 = doc.add_paragraph()
            format_body_paragraph(p_ch1, "CHAPTER 1\nINTRODUCTION", is_chapter=True)
            current_chapter = 1

        if source_docx and source_start_elem_idx >= 0:
            for child in source_docx.element.body[source_start_elem_idx:]:
                if child.tag.endswith('tbl'):
                    tbl_copy = copy.deepcopy(child)
                    doc._body._body._insert_tbl(tbl_copy)
                    t = docx.table.Table(tbl_copy, doc)
                    t.alignment = WD_TABLE_ALIGNMENT.CENTER
                elif child.tag.endswith('p'):
                    sp = docx.text.paragraph.Paragraph(child, source_docx)
                    raw_t = sp.text.strip()
                    has_drawing = bool(child.xpath('.//w:drawing') or child.xpath('.//w:pict'))
                    if not raw_t and not has_drawing:
                        continue
                    if has_drawing and not raw_t:
                        p_copy = copy.deepcopy(child)
                        doc._body._body._insert_p(p_copy)
                        continue
                    if is_standalone_prelim_header(raw_t):
                        continue
                    if re.search(r'\t\s*\d+\s*$', raw_t) or re.search(r'\.{3,}\s*\d+\s*$', raw_t):
                        continue

                    # References header check
                    if raw_t.upper() in ["REFERENCES", "LIST OF REFERENCES", "BIBLIOGRAPHY", "REFERENCES CITED"]:
                        doc.add_page_break()
                        p_elem = doc.add_paragraph()
                        format_body_paragraph(p_elem, "REFERENCES", is_chapter=True)
                        in_references = True
                        current_chapter = 99
                        continue

                    # Appendices header check
                    if any(raw_t.upper().startswith(ap) for ap in ["APPENDIX", "APPENDICES", "ANNEX"]):
                        doc.add_page_break()
                        p_elem = doc.add_paragraph()
                        format_body_paragraph(p_elem, raw_t.upper(), is_chapter=True)
                        in_references = False
                        current_chapter = 100
                        continue

                    # Explicit chapter heading
                    ch_match = re.match(r'^(?:CHAPTER|CHAPITRE)\s+(\d+|[IVXLCDM]+)(?:\s*[:\-–]\s*|\s+)(.*)$', raw_t, re.IGNORECASE)
                    explicit_ch_num = None
                    if ch_match:
                        try:
                            num_str = ch_match.group(1).upper()
                            roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}
                            explicit_ch_num = roman_map.get(num_str, int(num_str) if num_str.isdigit() else 1)
                        except Exception:
                            explicit_ch_num = 1

                    if explicit_ch_num is not None:
                        if explicit_ch_num > 1:
                            doc.add_page_break()
                        p_elem = doc.add_paragraph()
                        ch_sub = ch_match.group(2).strip().upper() if ch_match.group(2) else ""
                        ch_text = f"CHAPTER {explicit_ch_num}" + (f"\n{ch_sub}" if ch_sub else "")
                        format_body_paragraph(p_elem, ch_text, is_chapter=True)
                        current_chapter = explicit_ch_num
                        in_references = False
                        continue

                    # Section promotion
                    sec_match = re.match(r'^([1-5])\.1(?:\s+|$)', raw_t)
                    if sec_match and req.doc_type != "assignment" and not in_references:
                        sec_ch_num = int(sec_match.group(1))
                        if sec_ch_num > current_chapter:
                            if sec_ch_num > 1:
                                doc.add_page_break()
                            p_ch = doc.add_paragraph()
                            if sec_ch_num == 1:
                                ch_title = "CHAPTER 1\nINTRODUCTION"
                            elif sec_ch_num == 2:
                                ch_title = "CHAPTER 2\nLITERATURE REVIEW"
                            elif sec_ch_num == 3:
                                ch_title = "CHAPTER 3\nPROPOSED RESEARCH METHODOLOGY" if req.doc_type == "proposal" else "CHAPTER 3\nMATERIALS AND METHODS"
                            elif sec_ch_num == 4:
                                ch_title = "CHAPTER 4\nRESULTS AND DISCUSSIONS"
                            elif sec_ch_num == 5:
                                ch_title = "CHAPTER 5\nCONCLUSION AND RECOMMENDATIONS"
                            else:
                                ch_title = f"CHAPTER {sec_ch_num}"
                            
                            format_body_paragraph(p_ch, ch_title, is_chapter=True)
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
                        format_body_paragraph(p_elem, raw_t, is_ref=True)
                    elif is_h:
                        if lvl == 1 or "CHAPTER" in raw_t.upper():
                            format_body_paragraph(p_elem, raw_t, is_chapter=True)
                        elif lvl == 2:
                            format_body_paragraph(p_elem, raw_t, is_sub1=True)
                        else:
                            format_body_paragraph(p_elem, raw_t, is_sub2=True)
                    else:
                        format_body_paragraph(p_elem, raw_t)
        else:
            # Fallback for plain body_paras (e.g. from PDF)
            for p_info in body_paras:
                raw_t = p_info["text"].strip()
                if raw_t.upper() in ["REFERENCES", "LIST OF REFERENCES", "BIBLIOGRAPHY", "REFERENCES CITED"]:
                    doc.add_page_break()
                    p_elem = doc.add_paragraph()
                    format_body_paragraph(p_elem, "REFERENCES", is_chapter=True)
                    in_references = True
                    current_chapter = 99
                    continue
                if any(raw_t.upper().startswith(ap) for ap in ["APPENDIX", "APPENDICES", "ANNEX"]):
                    doc.add_page_break()
                    p_elem = doc.add_paragraph()
                    format_body_paragraph(p_elem, raw_t.upper(), is_chapter=True)
                    in_references = False
                    current_chapter = 100
                    continue
                ch_match = re.match(r'^(?:CHAPTER|CHAPITRE)\s+(\d+|[IVXLCDM]+)(?:\s*[:\-–]\s*|\s+)(.*)$', raw_t, re.IGNORECASE)
                explicit_ch_num = None
                if ch_match:
                    try:
                        num_str = ch_match.group(1).upper()
                        roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}
                        explicit_ch_num = roman_map.get(num_str, int(num_str) if num_str.isdigit() else 1)
                    except Exception:
                        explicit_ch_num = 1
                if explicit_ch_num is not None:
                    if explicit_ch_num > 1:
                        doc.add_page_break()
                    p_elem = doc.add_paragraph()
                    ch_sub = ch_match.group(2).strip().upper() if ch_match.group(2) else ""
                    ch_text = f"CHAPTER {explicit_ch_num}" + (f"\n{ch_sub}" if ch_sub else "")
                    format_body_paragraph(p_elem, ch_text, is_chapter=True)
                    current_chapter = explicit_ch_num
                    in_references = False
                    continue
                sec_match = re.match(r'^([1-5])\.1(?:\s+|$)', raw_t)
                if sec_match and req.doc_type != "assignment" and not in_references:
                    sec_ch_num = int(sec_match.group(1))
                    if sec_ch_num > current_chapter:
                        if sec_ch_num > 1:
                            doc.add_page_break()
                        p_ch = doc.add_paragraph()
                        if sec_ch_num == 1:
                            ch_title = "CHAPTER 1\nINTRODUCTION"
                        elif sec_ch_num == 2:
                            ch_title = "CHAPTER 2\nLITERATURE REVIEW"
                        elif sec_ch_num == 3:
                            ch_title = "CHAPTER 3\nPROPOSED RESEARCH METHODOLOGY" if req.doc_type == "proposal" else "CHAPTER 3\nMATERIALS AND METHODS"
                        elif sec_ch_num == 4:
                            ch_title = "CHAPTER 4\nRESULTS AND DISCUSSIONS"
                        elif sec_ch_num == 5:
                            ch_title = "CHAPTER 5\nCONCLUSION AND RECOMMENDATIONS"
                        else:
                            ch_title = f"CHAPTER {sec_ch_num}"
                        format_body_paragraph(p_ch, ch_title, is_chapter=True)
                        current_chapter = sec_ch_num
                p_elem = doc.add_paragraph()
                if in_references:
                    format_body_paragraph(p_elem, raw_t, is_ref=True)
                elif p_info.get("is_heading"):
                    lvl = p_info.get("level", 1)
                    if lvl == 1 or "CHAPTER" in raw_t.upper():
                        format_body_paragraph(p_elem, raw_t, is_chapter=True)
                    elif lvl == 2:
                        format_body_paragraph(p_elem, raw_t, is_sub1=True)
                    else:
                        format_body_paragraph(p_elem, raw_t, is_sub2=True)
                else:
                    format_body_paragraph(p_elem, raw_t)
    else:
        # Default starter content if uploaded document had very few paragraphs
        p_ch1 = doc.add_paragraph()
        format_body_paragraph(p_ch1, "CHAPTER 1\nINTRODUCTION", is_chapter=True)
        
        p_s1 = doc.add_paragraph()
        format_body_paragraph(p_s1, "1.1 Background of the Study", is_sub1=True)
        
        p_b1 = doc.add_paragraph()
        format_body_paragraph(p_b1, f"The University of Bamenda was established to drive excellence in higher education and professional training. Under {meta.faculty}, research and technical implementation are closely aligned with national development objectives. This work titled “{meta.title}” investigates key architectural principles and system methodologies.")

    doc.save(output_path)
    return output_path

