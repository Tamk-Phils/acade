"""
AcadFormat Intelligent AI Academic Assistant Engine.
Supports Google Gemini 1.5 Flash (Free Tier) when configured in .env,
and includes an advanced, zero-latency local Natural Language Understanding (NLU) & Dialogue Engine
specifically attuned to The University of Bamenda (UBa) and Catholic University of Cameroon (CATUC) Bamenda standards.

Features:
- Understands natural language and voice-transcribed prompts.
- Extracts document metadata modifications (title, author, reg number, supervisor, department, school, group assignment roster).
- Returns applied_changes to dynamically update the active document in the web app.
- Delivers thoughtful, human-like academic guidance (abstracts, résumés, preliminaries, defence corrections).
"""
import os
import re
import json
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

from backend.academic_data import ALL_ESTABLISHMENTS, UNIVERSITIES, resolve_department_and_option

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()

# ---------------------------------------------------------
# Google Gemini Free Tier Integration
# ---------------------------------------------------------
SYSTEM_PROMPT = """You are the AcadFormat Senior Academic Formatting Director and AI Advisor for The University of Bamenda (UBa) and Catholic University of Cameroon (CATUC) Bamenda.
You think, advise, and speak with the warmth, precision, and authority of an experienced University Dean and Thesis Formatting Chairperson.

You understand spoken ideas, natural language instructions, and voice-transcribed dictation.

STATUTORY FORMATTING RULES YOU ENFORCE:
1. Margins: Mandatory 4.0 cm (1.57 in) inside binding margin (to prevent binding clamps from eating text); 2.5 cm outside, top, bottom. Font: Times New Roman 12pt, 1.5 line spacing.
2. Preliminary Pages Sequence: Cover Page -> Title Page (Page i, unnumbered) -> Copyright (ii) -> Declaration of Originality (iii) -> Certification of Corrections after Defense (iv, signed by Supervisor, HOD, Director/Dean) -> Acceptance of Dissertation (v, Examination Committee Chair) -> Abstract (vi, English, <=500 words) -> Résumé (vii, French) -> Dedication (viii) -> Acknowledgements (ix) -> Table of Contents -> Lists of Tables/Figures/Abbreviations.
3. COLTECH Page 11 Template: Top center 'THE UNIVERSITY OF BAMENDA', 3-column table header ('THE COLLEGE OF TECHNOLOGY' | 'UBa Official Crest' | 'DEPARTMENT OF [ORIGIN]'), bold uppercase title with clean rectangular border box, purpose clause, candidate BY: Name & REG NUMBER, SUPERVISOR(S): with academic ranks (Pr. / Dr.), Month Year at bottom. Note: Option/Specialization (e.g. Information Technology and Cybersecurity) belongs to the purpose clause and option field, while Department (e.g. Computer Engineering) appears in the header.
4. CATUC Bamenda: Motto 'Fides et Scientia', faculties (FBMS, SENG, FST, SHMS, FHSS, STANR, STHEO), matricule CATUC/XX/YYY, APA/IEEE reference standards.
5. Assignments & Internships: Only cover page (no title page). Can have Table of Contents & Acknowledgements. If Group Assignment: <=5 members displayed on Cover Page; >5 members moved to dedicated Page 2 Evaluation & Marks Sheet with columns (No, Name, Matricule, Participation/Score).

OUTPUT REQUIREMENTS:
If the user's prompt requests ANY change to their document, cover page, or metadata (title, author, registration number, supervisor, co-supervisor, department, option/specialization, faculty, institution, document type, group members, header mode, dedication, abstract, acknowledgements), you MUST return a valid JSON object in this exact schema:
{
  "reply": "Your warm, natural, human-like conversational response explaining what you did and offering constructive advice",
  "action_summary": "Brief 1-line summary of applied changes",
  "applied_changes": {
     "title": "optional string",
     "author": "optional string",
     "reg_number": "optional string",
     "supervisors": ["optional list of names"],
     "supervisor_ranks": ["optional list of ranks"],
     "hod_name": "optional string",
     "director_name": "optional string",
     "faculty": "optional string",
     "faculty_code": "optional string",
     "department": "optional string",
     "option": "optional string",
     "doc_type": "optional string",
     "school_type": "optional string",
     "institution": "uba or catuc",
     "header_mode": "center_crest or dual_logo",
     "is_group_assignment": true or false,
     "group_members": [
        {"name": "...", "matricule": "...", "participation": "", "grade": ""}
     ]
  },
  "suggestions": ["Next step 1", "Next step 2", "Next step 3"]
}

If no change is requested (user is asking an academic question or advice), set applied_changes to null and action_summary to null, and provide a rich, detailed, articulate response.
Respond ONLY with the JSON object.
"""

def call_gemini_free_tier(message: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Calls Google Gemini 1.5 Flash Free Tier via official REST endpoint."""
    if not GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    user_context = (
        f"Institution: {context.get('institution', 'uba').upper()}\n"
        f"Current School: {context.get('school_type', 'coltech')}\n"
        f"Current Document Type: {context.get('doc_type', 'dissertation_bsc')}\n"
        f"Current Metadata: {json.dumps(context.get('metadata', {}))}\n\n"
        f"User Message: {message}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"text": user_context}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)
                return {
                    "status": "success",
                    "reply": parsed.get("reply", "Changes noted and applied."),
                    "applied_changes": parsed.get("applied_changes"),
                    "action_summary": parsed.get("action_summary"),
                    "suggestions": parsed.get("suggestions", ["Check Table of Contents", "Review Cover Page", "Export Document"]),
                    "engine": "gemini_free_tier"
                }
    except Exception as e:
        print(f"[AcadFormat AI] Gemini API fallback: {e}")
    return None


# ---------------------------------------------------------
# Advanced Local Natural Language Dialogue & Action Engine
# ---------------------------------------------------------
def extract_supervisor_rank(name: str) -> str:
    """Infers official academic rank from prefix or returns Associate Professor by default."""
    low = name.lower()
    if "prof" in low or "pr." in low or "pr " in low:
        return "Professor"
    if "dr" in low:
        return "Senior Lecturer"
    if "mr" in low or "mrs" in low or "ms" in low:
        return "Lecturer"
    return "Associate Professor"

def parse_and_generate_local_nlp(
    message: str,
    institution: str = "uba",
    doc_type: Optional[str] = None,
    school_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Intelligent local NLU & Dialogue engine that runs instantly with 0 external network dependencies.
    Extracts intentions, executes metadata modifications, and crafts human-like academic advice.
    """
    clean_msg = message.strip()
    low = clean_msg.lower()
    meta = metadata or {}

    applied = {}
    actions = []

    # 1. Title Extraction
    title_match = re.search(
        r'(?:change|set|update|make)\s+(?:the\s+)?title\s+(?:to|as|into)?\s*[:"\'\s]+([^"\'\n\.\?]+?)(?=\s+(?:and\s+set|and\s+my|and\s+supervisor|and\s+matricule|supervisor|matricule|author|\.|\?|$)|$)|'
        r'title\s*[:=]\s*["\']?([^"\'\n]+)|'
        r'(?:my\s+)?(?:project|thesis|dissertation|paper|work)\s+(?:is\s+)?(?:titled|called|on|about)\s*[:"\'\s]+([^"\'\n\.\?]+?)(?=\s+(?:and\s+set|and\s+my|and\s+supervisor|and\s+matricule|supervisor|matricule|author|\.|\?|$)|$)',
        clean_msg,
        re.IGNORECASE
    )
    if title_match:
        raw_title = (title_match.group(1) or title_match.group(2) or title_match.group(3) or "").strip(" \"'.,;")
        if len(raw_title) > 3 and not re.search(r'^(to|is|a|the)$', raw_title, re.IGNORECASE):
            applied["title"] = raw_title.upper()
            actions.append(f"Title set to \"{raw_title.upper()}\"")

    # 2. Author / Candidate Name Extraction
    author_match = re.search(
        r'(?:change|set|update)\s+(?:the\s+)?(?:author|candidate|student|my\s+name)\s+(?:to|as)?\s*[:"\'\s]+([A-Za-z\s\-]+)|'
        r'(?:my\s+name\s+is|author\s*[:=]|by\s*:)\s*([A-Za-z\s\-]+)',
        clean_msg,
        re.IGNORECASE
    )
    if author_match:
        raw_author = (author_match.group(1) or author_match.group(2) or "").strip(" \"'.,;")
        # Avoid false positives on common words
        if len(raw_author.split()) >= 2 and not any(w in raw_author.lower() for w in ["supervisor", "university", "department", "assignment"]):
            applied["author"] = raw_author.upper()
            actions.append(f"Author name updated to \"{raw_author.upper()}\"")

    # 3. Matricule / Registration Number
    reg_match = re.search(
        r'(?:matricule|registration\s*number|reg\s*number|reg\s*no)\s*(?:is|to|as)?\s*[:=]?\s*([A-Za-z0-9\/]+)|'
        r'\b(UBA[0-9A-Za-z]+|CATUC\/[0-9A-Za-z\/]+)\b',
        clean_msg,
        re.IGNORECASE
    )
    if reg_match:
        raw_reg = (reg_match.group(1) or reg_match.group(2) or "").strip().upper()
        if len(raw_reg) >= 5 and raw_reg not in ["TO", "IS", "AS"]:
            applied["reg_number"] = raw_reg
            actions.append(f"Registration Number updated to \"{raw_reg}\"")

    # 4. Supervisor & Rank Extraction
    sup_match = re.search(
        r'(?:change|set|update)?\s*(?:the\s+)?supervisor\s*(?:to|is|as)?\s*[:"\'\s]+([A-Za-z\.\s\-]+?)(?=\s+(?:and\s+my|and\s+set|and\s+matricule|matricule|reg|with|department|\.|\?|$)|$)',
        clean_msg,
        re.IGNORECASE
    )
    if sup_match:
        raw_sup = (sup_match.group(1) or "").strip(" \"'.,;")
        if len(raw_sup) > 3 and not any(w in raw_sup.lower() for w in ["please", "how", "what", "can", "rule"]):
            cleaned_sup = raw_sup.title()
            if not cleaned_sup.startswith("Pr.") and not cleaned_sup.startswith("Prof") and not cleaned_sup.startswith("Dr."):
                cleaned_sup = f"Pr. {cleaned_sup}"
            rank = extract_supervisor_rank(cleaned_sup)
            applied["supervisors"] = [cleaned_sup]
            applied["supervisor_ranks"] = [rank]
            actions.append(f"Supervisor updated to \"{cleaned_sup}\" ({rank})")

    # 5. Institution & Establishment / Faculty
    has_switch_verb = any(cmd in low for cmd in ["switch", "change", "set", "make", "use", "convert", "select", "to catuc", "to coltech", "to uba"])
    is_info_query = any(q in low for q in ["tell me", "what are", "what is", "rules", "guidelines", "explain", "about catholic", "about catuc"])

    if has_switch_verb and not is_info_query:
        if "catuc" in low or "catholic university" in low:
            applied["institution"] = "catuc"
            target_school = "catuc_seng"
            # Check specific codes first: fbms, seng, fst, shms, fhss, stanr, stheo
            for code, est in ALL_ESTABLISHMENTS.items():
                if est["university"] == "catuc" and est["code"].lower() in low:
                    target_school = code
                    break
            else:
                for code, est in ALL_ESTABLISHMENTS.items():
                    if est["university"] == "catuc" and any(w in low for w in est["name_en"].lower().split() if len(w) > 4):
                        target_school = code
                        break
            est_obj = ALL_ESTABLISHMENTS.get(target_school, ALL_ESTABLISHMENTS["catuc_seng"])
            applied["school_type"] = target_school
            applied["faculty"] = est_obj["name_en"]
            applied["faculty_code"] = est_obj["code"]
            applied["motto"] = est_obj["motto"]
            actions.append(f"Switched institution to CATUC ({est_obj['name_en']})")
        elif "coltech" in low or "college of technology" in low:
            applied["institution"] = "uba"
            applied["school_type"] = "coltech"
            est_obj = ALL_ESTABLISHMENTS["coltech"]
            applied["faculty"] = est_obj["name_en"]
            applied["faculty_code"] = est_obj["code"]
            applied["motto"] = est_obj["motto"]
            actions.append("Configured COLTECH (College of Technology, UBa)")
        elif any(f in low for f in ["faculty of science", "fs uba", "nahpi", "htttc", "httc", "fems", "falsh"]):
            for code, est in ALL_ESTABLISHMENTS.items():
                if est["university"] == "uba" and (est["code"].lower() in low or any(w in low for w in est["name_en"].lower().split() if len(w) > 4)):
                    applied["institution"] = "uba"
                    applied["school_type"] = code
                    applied["faculty"] = est["name_en"]
                    applied["faculty_code"] = est["code"]
                    applied["motto"] = est["motto"]
                    actions.append(f"Switched faculty to {est['name_en']}")
                    break

    # 6. Department & Option Extraction
    dep_match = re.search(r'department\s+(?:of\s+)?([A-Za-z\s&]+?)(?=\s+(?:with\s+option|option|and\s+option|in\s+option|\.|\?|$)|$)', clean_msg, re.IGNORECASE)
    opt_match = re.search(r'(?:option|specialization|speciality|programme)\s*(?:of|is|to|as|in)?\s*[:"\'\s]+([A-Za-z\s&]+?)(?=\s+(?:and\s+set|and\s+department|\.|\?|$)|$)', clean_msg, re.IGNORECASE)

    raw_dep = dep_match.group(1).strip(" \"'.,;") if dep_match else None
    raw_opt = opt_match.group(1).strip(" \"'.,;") if opt_match else None

    # Check for direct mention of known options if not extracted
    if not raw_opt:
        for opt_candidate in [
            "Information Technology and Cybersecurity",
            "Software Engineering",
            "Computer Networks and Systems",
            "Artificial Intelligence and Data Science",
            "Power Systems and Renewable Energy",
            "Telecommunications and Networking",
            "Control Systems and Automation",
            "Automotive and Thermal Systems",
            "Manufacturing and Industrial Production"
        ]:
            if opt_candidate.lower() in low:
                raw_opt = opt_candidate
                break

    if raw_dep or raw_opt:
        curr_dept = raw_dep or meta.get("department", "Computer Engineering")
        curr_opt = raw_opt or meta.get("option", "")
        resolved_dept, resolved_opt = resolve_department_and_option(
            applied.get("faculty_code") or meta.get("faculty_code", "COLTECH"),
            curr_dept,
            curr_opt
        )
        applied["department"] = resolved_dept
        applied["option"] = resolved_opt
        actions.append(f"Department: \"{resolved_dept}\" | Option: \"{resolved_opt}\"")

    # 7. Document Type
    if "group assignment" in low or "group presentation" in low:
        applied["doc_type"] = "assignment"
        applied["is_group_assignment"] = True
        applied["header_mode"] = "dual_logo"
        actions.append("Converted to Group Technical Assignment (Dual Logo Header)")
    elif "assignment" in low or "coursework" in low:
        applied["doc_type"] = "assignment"
        applied["header_mode"] = "dual_logo"
        actions.append("Set Document Type to Technical Course Assignment")
    elif "internship" in low:
        applied["doc_type"] = "internship"
        actions.append("Set Document Type to Academic Internship Report")
    elif "mtech" in low:
        applied["doc_type"] = "dissertation_mtech"
        actions.append("Set Document Type to Master of Technology (MTech) Dissertation")
    elif "btech" in low:
        applied["doc_type"] = "project_btech"
        actions.append("Set Document Type to Bachelor of Technology (BTech) Capstone Project")
    elif "phd" in low or "doctorate" in low:
        applied["doc_type"] = "thesis_phd"
        actions.append("Set Document Type to Doctor of Philosophy (PhD) Thesis")

    # 8. Group Members parsing
    if ("group" in low or "members" in low) and any(kw in low for kw in ["member", "students", "names", "list", "1.", "1 -", ","]):
        # Check if list of students is provided
        members = []
        lines = re.split(r'[\n;,]|\d+[\.\)]', clean_msg)
        for chunk in lines:
            chunk = chunk.strip()
            if not chunk or len(chunk) < 4:
                continue
            # Look for "Name Matricule" or "Name (Matricule)"
            sub_m = re.search(r'([A-Za-z\s]+)(?:[\(\s]+(UBA[0-9A-Za-z]+|CATUC\/[0-9A-Za-z\/]+|[A-Za-z0-9\/]+)[\)]?)?', chunk)
            if sub_m:
                m_name = sub_m.group(1).strip()
                m_mat = (sub_m.group(2) or "").strip()
                if len(m_name.split()) >= 1 and not any(w in m_name.lower() for w in ["group", "member", "add", "please", "make", "change"]):
                    members.append({
                        "name": m_name.title(),
                        "matricule": m_mat.upper() if m_mat else f"UBA24TECH{len(members)+1:02d}",
                        "participation": "",
                        "grade": ""
                    })
        if members:
            applied["is_group_assignment"] = True
            applied["group_members"] = members
            applied["show_grading_column"] = True
            actions.append(f"Configured group roster with {len(members)} candidate(s)")

    # 9. Header Mode
    if "dual logo" in low or "dual crest" in low or "two logos" in low:
        applied["header_mode"] = "dual_logo"
        actions.append("Switched header layout to Dual Crest")
    elif "center crest" in low or "single logo" in low or "center logo" in low:
        applied["header_mode"] = "center_crest"
        actions.append("Switched header layout to Standard Centered Crest")

    # ---------------------------------------------------------
    # Synthesize Natural Conversational Responses
    # ---------------------------------------------------------
    if actions:
        action_summary = " • ".join(actions)
        reply = (
            f"I have understood your instructions and applied the following changes to your manuscript:\n\n"
            + "\n".join(f"• **{act}**" for act in actions)
            + "\n\n"
            f"The live preview and metadata fields in the form have been immediately updated to comply with the statutory formatting standards of **{institution.upper()}**."
        )
        suggestions = ["Verify Table of Contents", "Check Page Previews", "Download Re-formatted DOCX"]
        return {
            "status": "success",
            "reply": reply,
            "applied_changes": applied,
            "action_summary": action_summary,
            "suggestions": suggestions,
            "engine": "local_nlp_action_engine"
        }

    # Conversational Questions & Formatting Advice
    if any(kw in low for kw in ["margin", "binding", "border", "padding", "4cm", "4.0"]):
        reply = (
            "**Why 4.0 cm inside margin is mandatory at UBa & CATUC:**\n\n"
            "Academic binders in Bamenda use heavy dark-black buckram hardcover binding that clamps **1.5 inches (approximately 3.8 to 4.0 cm)** directly into the left edge of the page. "
            "If your inside margin is standard (2.5 cm), the binding machine literally eats your text! "
            "AcadFormat automatically sets your **inside binding margin to exactly 4.0 cm** and your outside/top/bottom margins to **2.5 cm**, ensuring your printed document opens cleanly without obscuring a single character."
        )
        suggestions = ["Apply 4.0cm Margins", "Check Preliminary Sequence", "COLTECH Cover Spec"]

    elif any(kw in low for kw in ["assignment", "table of contents", "toc"]):
        reply = (
            "**Yes! Academic Assignments can and should have a Table of Contents:**\n\n"
            "• **When to include:** Any technical assignment, laboratory report, or mini-project exceeding 5 pages requires a Table of Contents, followed by brief Acknowledgements.\n"
            "• **Cover Page Rules:** Unlike dissertations, assignments have **only a Cover Page** (no secondary Title Page).\n"
            "• **Group Assignments:** If you have up to 5 members, the roster appears directly on the cover page. If there are more than 5 members, AcadFormat places the group title on the cover page and moves the full roster with evaluation score marks to **Page 2**."
        )
        suggestions = ["Set as Group Assignment", "Add Group Members", "Switch to Dual Logo Header"]

    elif any(kw in low for kw in ["supervisor", "rank", "hod", "director", "mathias", "defense", "corrections"]):
        reply = (
            "**Official Defence & Sign-off Protocol (UBa Senate Rules):**\n\n"
            "1. **Supervisor Rank:** Official guidelines require the supervisor's exact academic rank (e.g. *Professor*, *Associate Professor*, *Senior Lecturer*).\n"
            "2. **Certification of Corrections after Defense:** Must be signed by:\n"
            "   • Your **Supervisor(s)** (e.g. Pr. Mathias Onabid)\n"
            "   • The **Head of Department (HOD)**\n"
            "   • The **Director of College / Dean of Faculty**\n"
            "3. **Acceptance of Dissertation:** Signed by the Chairperson of the Master's/BTech Examination Committee.\n\n"
            "You can tell me your supervisor's name right now (e.g., *\"Set supervisor to Dr. Emmanuel\"*) and I will update your document immediately!"
        )
        suggestions = ["Set Supervisor Name", "Add Certification Page", "View Acceptance Spec"]

    elif any(kw in low for kw in ["abstract", "resume", "résumé", "french", "translation"]):
        reply = (
            "**Abstract & Résumé Requirements:**\n\n"
            "• **Bilingual Standard:** The Republic of Cameroon is officially bilingual. Master's dissertations, BTech projects, and PhD theses require an **Abstract in English** (Page vi, maximum 500 words) immediately followed by a French translation entitled **Résumé** (Page vii).\n"
            "• **Structure:** Both must cover: 1) Problem Statement & Objective, 2) Methodology & Tools, 3) Key Findings/Results, 4) Practical Contribution.\n\n"
            "Would you like me to help you draft an abstract or translate your project objective into French?"
        )
        suggestions = ["Help me draft an Abstract", "Translate Abstract to French", "COLTECH Cover Layout"]

    elif any(kw in low for kw in ["catuc", "catholic", "catholic university", "fides", "fbms", "seng"]):
        reply = (
            "**Catholic University of Cameroon (CATUC) Formatting Guidelines:**\n\n"
            "• **Motto:** *Fides et Scientia* (Faith and Knowledge).\n"
            "• **Faculties:** Faculty of Business and Management Sciences (FBMS), Faculty of Engineering (SENG), Faculty of Science (FST), School of Health and Medical Sciences (SHMS), Faculty of Humanities (FHSS).\n"
            "• **Citations:** APA 7th Edition for FBMS/FHSS; IEEE for Engineering & Computer Science.\n"
            "• **Matricule:** Formatted as `CATUC/XX/YYY`.\n\n"
            "You can switch your document to CATUC at any time by saying *\"Switch to CATUC FBMS\"*."
        )
        suggestions = ["Switch to CATUC SENG", "Switch to CATUC FBMS", "CATUC Cover Specification"]
    elif any(kw in low for kw in ["price", "pricing", "cost", "momo", "orange", "250", "pay", "payment", "trial", "free trial"]):
        reply = (
            "**AcadFormat Access & Pricing Model:**\n\n"
            "• **3-Day (72-Hour) Free Trial:** Every newly registered student receives 72 hours of completely unrestricted document audits, formatting, and live previews.\n"
            "• **Export Pass:** After the trial concludes, activating unlimited **DOCX and PDF downloads** costs only **250 FCFA for 7 full days (1 week)**.\n"
            "• **Payment Methods:** Direct instant verification via **MTN Mobile Money (MoMo)** and **Orange Money**.\n"
            "• **Device Lock:** Accounts are bound to your verified device to protect against unauthorized sharing."
        )
        suggestions = ["Activate Free Trial", "How Device Lock Works", "Privacy Policy Law No. 2010/012"]

    else:
        inst_title = "Catholic University of Cameroon (CATUC)" if institution == "catuc" else "The University of Bamenda (UBa)"
        reply = (
            f"I am your **AcadFormat AI Academic Advisor** for **{inst_title}**.\n\n"
            "You can type or speak via the microphone button to prompt any adjustments:\n"
            "• *\"Set title to Cloud Computing in Rural Healthcare\"*\n"
            "• *\"My supervisor is Prof. Mathias Onabid\"*\n"
            "• *\"Make this a group assignment for 5 members: Alice, Bob, Charlie...\"*\n"
            "• *\"Switch to CATUC Faculty of Engineering\"*\n"
            "• *\"Change margins to 4cm inside binding\"*\n\n"
            "Whatever ideas you have, speak or prompt them and I will implement them directly into your manuscript!"
        )
        suggestions = [
            "Change my title",
            "Set supervisor name",
            "Configure group assignment",
            "What is the inside binding margin?"
        ]

    return {
        "status": "success",
        "reply": reply,
        "applied_changes": None,
        "action_summary": None,
        "suggestions": suggestions,
        "engine": "local_nlp_dialogue_engine"
    }


def generate_chat_response(
    message: str,
    institution: str = "uba",
    doc_type: Optional[str] = None,
    school_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Primary routing handler for AcadFormat AI.
    1. Attempts Google Gemini 1.5 Flash (Free Tier) if key is provided.
    2. Falls back to ultra-fast, zero-dependency local NLU action engine.
    """
    context = {
        "institution": institution,
        "doc_type": doc_type,
        "school_type": school_type,
        "metadata": metadata or {}
    }

    # 1. Try Gemini Free Tier if key is configured
    if GEMINI_API_KEY:
        gemini_res = call_gemini_free_tier(message, context)
        if gemini_res:
            return gemini_res

    # 2. Local Intelligent NLU & Dialogue Engine (Sub-15ms latency, 100% free)
    return parse_and_generate_local_nlp(
        message=message,
        institution=institution,
        doc_type=doc_type,
        school_type=school_type,
        metadata=metadata
    )
