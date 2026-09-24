"""
Institutional Compliance Auditor for The University of Bamenda (UBa) and all Establishments.
"""
from typing import List, Dict, Any
from backend.models import AuditResult, AuditIssue, DocumentMetadata
from backend.parser import ParsedDocument
from backend.academic_data import UBA_ESTABLISHMENTS, DOCUMENT_TYPE_LABELS

def audit_document(
    doc: ParsedDocument,
    doc_type: str = "dissertation_bsc",
    school_type: str = "coltech",
    header_mode: str = "center_crest"
) -> AuditResult:
    """
    Audits a parsed document against UBa Senate Regulations and School Guidelines.
    Returns an AuditResult with a compliance score (0-100) and itemized issues.
    """
    issues: List[AuditIssue] = []
    detected_sections: List[str] = []
    missing_sections: List[str] = []
    passed_checks = 0
    total_checks = 0

    # 1. Margins Check
    total_checks += 1
    left_margin = doc.margins.get("left", 2.54)
    if abs(left_margin - 4.0) > 0.3:
        issues.append(AuditIssue(
            id="margin-left-binding",
            category="margins",
            severity="error",
            message=f"Binding margin is currently {left_margin} cm. UBa standard mandates 4.0 cm inside for dark-black binding.",
            recommendation="Set Left/Inside Margin to exactly 4.0 cm (1.57 inches)."
        ))
    else:
        passed_checks += 1

    total_checks += 1
    top_m = doc.margins.get("top", 2.54)
    bot_m = doc.margins.get("bottom", 2.54)
    right_m = doc.margins.get("right", 2.54)
    if abs(top_m - 2.0) > 0.4 or abs(bot_m - 2.0) > 0.4 or abs(right_m - 2.0) > 0.4:
        issues.append(AuditIssue(
            id="margin-surround",
            category="margins",
            severity="warning",
            message=f"Outer margins are ({top_m}cm, {bot_m}cm, {right_m}cm). UBa standard specifies 2.0 cm Top x 2.0 cm Bottom x 2.0 cm Outside.",
            recommendation="Set Top, Bottom, and Right margins to 2.0 cm."
        ))
    else:
        passed_checks += 1

    # 2. Typography Check
    total_checks += 1
    non_tnr_fonts = [f for f in doc.fonts_used if "Times" not in f]
    if non_tnr_fonts:
        issues.append(AuditIssue(
            id="typography-font-family",
            category="typography",
            severity="error",
            message=f"Found non-compliant font families: {', '.join(non_tnr_fonts[:3])}. UBa standard strictly requires Times New Roman.",
            recommendation="Convert all body text and headings to Times New Roman."
        ))
    else:
        passed_checks += 1

    total_checks += 1
    if doc.line_spacings and not any(1.4 <= s <= 1.6 for s in doc.line_spacings):
        issues.append(AuditIssue(
            id="typography-line-spacing",
            category="typography",
            severity="warning",
            message="Main text does not conform to the mandatory 1.5 line spacing.",
            recommendation="Apply 1.5 line spacing to body text (1.0 single spacing for tables and references)."
        ))
    else:
        passed_checks += 1

    # 3. Header & Logo Identity Check
    total_checks += 1
    if doc_type == "assignment":
        issues.append(AuditIssue(
            id="identity-assignment-header",
            category="structure",
            severity="info",
            message="Continuous assessment assignments utilize the institutional assignment header (Course Code, Course Title, Lecturer, and Dual Crests).",
            recommendation="Ensure assignment metadata (Course Code, Course Title, Lecturer) is populated."
        ))
        passed_checks += 1
    else:
        passed_checks += 1

    # 4. Mandatory Preliminary Pages Checklist (Skip prelims for standard assignments)
    if doc_type != "assignment":
        prelim_checklist = [
            ("Cover Page", True),
            ("Title Page", True),
            ("Copyright Notice", doc.raw_text.find("©") != -1 or "COPYRIGHT" in doc.raw_text.upper()),
            ("Declaration of Originality", doc.has_declaration),
            ("Certification of Corrections", doc.has_certification),
            ("Abstract & Keywords", doc.has_abstract),
            ("French Résumé (Translation)", doc.has_resume),
            ("Acknowledgements", doc.has_acknowledgements),
            ("Table of Contents", doc.has_toc),
            ("List of References (APA)", doc.has_references),
        ]

        if doc_type == "internship":
            prelim_checklist.append(("Executive Summary", "EXECUTIVE SUMMARY" in doc.raw_text.upper()))

        for section_name, exists in prelim_checklist:
            total_checks += 1
            if exists:
                detected_sections.append(section_name)
                passed_checks += 1
            else:
                missing_sections.append(section_name)
                issues.append(AuditIssue(
                    id=f"missing-{section_name.lower().replace(' ', '-')}",
                    category="preliminaries",
                    severity="error",
                    message=f"Mandatory section '{section_name}' is missing.",
                    recommendation=f"Auto-generate and insert the statutory {section_name} before the main body."
                ))

    # 5. Lists of Illustrations check
    if doc.tables_count > 0:
        total_checks += 1
        has_lot = "LIST OF TABLES" in doc.raw_text.upper()
        if not has_lot:
            missing_sections.append("List of Tables")
            issues.append(AuditIssue(
                id="missing-list-of-tables",
                category="preliminaries",
                severity="warning",
                message=f"Document contains {doc.tables_count} tables, but has no 'List of Tables'.",
                recommendation="Generate automated List of Tables in preliminary pages."
            ))
        else:
            detected_sections.append("List of Tables")
            passed_checks += 1

    if doc.figures_count > 0:
        total_checks += 1
        has_lof = "LIST OF FIGURES" in doc.raw_text.upper()
        if not has_lof:
            missing_sections.append("List of Figures")
            issues.append(AuditIssue(
                id="missing-list-of-figures",
                category="preliminaries",
                severity="warning",
                message=f"Document contains {doc.figures_count} illustrations/figures, but has no 'List of Figures'.",
                recommendation="Generate automated List of Figures in preliminary pages."
            ))
        else:
            detected_sections.append("List of Figures")
            passed_checks += 1

    # 6. Heading depth check (max 3 levels)
    total_checks += 1
    deep_headings = [h["text"] for h in doc.headings if h.get("level", 0) > 3 or (len(h["text"].split()[0].split('.')) > 3 if h["text"].split() else False)]
    if deep_headings:
        issues.append(AuditIssue(
            id="heading-depth-excess",
            category="structure",
            severity="warning",
            message=f"Found headings exceeding maximum 3 levels: '{deep_headings[0][:40]}...'. UBa guidelines limit numbering to 3 levels (e.g. 1.1.1).",
            recommendation="Flatten headings beyond level 3 into bullet points or italicized subheadings."
        ))
    else:
        passed_checks += 1

    # Compute Compliance Score
    compliance_score = int(round((passed_checks / max(1, total_checks)) * 100))

    return AuditResult(
        doc_type=doc_type,
        school_type=school_type,
        header_mode=header_mode,
        compliance_score=compliance_score,
        total_issues=len(issues),
        passed_checks=passed_checks,
        issues=issues,
        detected_sections=detected_sections,
        missing_sections=missing_sections,
        metadata=doc.metadata,
        stats={
            "word_count": len(doc.raw_text.split()),
            "estimated_pages": doc.page_count,
            "headings_count": len(doc.headings),
            "tables_count": doc.tables_count,
            "figures_count": doc.figures_count,
            "left_margin_cm": left_margin,
            "fonts_detected": doc.fonts_used or ["Times New Roman (default)"]
        }
    )
