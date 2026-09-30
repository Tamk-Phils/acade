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

import threading
import concurrent.futures
from backend.academic_data import ALL_ESTABLISHMENTS, UNIVERSITIES, resolve_department_and_option

load_dotenv()

# High-Performance Thread Pool for Sub-Second Cloud Fallback
_fast_ai_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="acadformat_ai")

# Multi-AI Model Keys (configured via environment variables or .env)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()

def clean_stars(text: str) -> str:
    """Completely strips all Markdown asterisks and stars (** or *) to ensure clean, human-readable prose."""
    if not text:
        return ""
    # Strip double/triple asterisks: **word** -> word
    text = re.sub(r'\*{2,3}(.*?)\*{2,3}', r'\1', text)
    # Strip single asterisks: *word* -> word
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'\1', text)
    # Convert bullet asterisks to clean bullet symbol
    text = re.sub(r'^\s*[\*\-]\s+', '• ', text, flags=re.MULTILINE)
    # Remove any remaining lone asterisks
    text = text.replace('*', '')
    return text.strip()

SYSTEM_PROMPT = """You are the AcadFormat Senior Academic Formatting Director and AI Advisor for The University of Bamenda (UBa) and Catholic University of Cameroon (CATUC) Bamenda.
You think, advise, and speak with the warmth, precision, and authority of an experienced University Dean and Thesis Formatting Chairperson.
You deeply understand natural language, free-form instructions, student questions, and voice-transcribed dictation.

CRITICAL INSTRUCTIONS ON FORMATTING YOUR OUTPUT:
1. Do NOT use any Markdown asterisks or stars (** or *) in your response. Never write **word** or *word*.
2. Write clean, natural, elegant text with normal punctuation. If you need emphasis, use UPPERCASE or clear wording.
3. If providing lists, use simple bullet points starting with a hyphen (-) or dot (•), never asterisks.

STATUTORY FORMATTING RULES YOU ENFORCE:
1. Margins: Mandatory 4.0 cm (1.57 in) inside binding margin (to prevent binding clamps from eating text); 2.5 cm outside, top, bottom. Font: Times New Roman 12pt, 1.5 line spacing.
2. Preliminary Pages Sequence: Cover Page -> Title Page (Page i, unnumbered) -> Copyright (ii) -> Declaration of Originality (iii) -> Certification of Corrections after Defense (iv, signed by Supervisor, HOD, Director/Dean) -> Acceptance of Dissertation (v, Examination Committee Chair) -> Abstract (vi, English, <=500 words) -> Résumé (vii, French) -> Dedication (viii) -> Acknowledgements (ix) -> Table of Contents -> Lists of Tables/Figures/Abbreviations.
3. Institutions:
   - HTTTC (Higher Technical Teacher Training College / ENSET Bambili): Technical teacher education, awards DIPET I, DIPET II, B.Tech, M.Tech.
   - HTTC (Higher Teacher Training College / ENS Bambili): General secondary teacher education, awards DIPES I, DIPES II, Postgraduate Diploma in Education.
   - COLTECH: College of Technology (BTech, MTech).
   - CATUC Bamenda: Motto 'Fides et Scientia', faculties (FBMS, SENG, FST, SHMS, FHSS, STANR, STHEO).
4. Custom Editing Instructions:
   If the user requests custom non-standard formatting (e.g. Arial 11pt, 1.15 spacing, 2.5cm margins, unboxed title), capture these under custom_instructions and individual fields so the restructuring engine applies them.

OUTPUT REQUIREMENTS:
If the user's prompt requests ANY change to their document, cover page, styling, or metadata (title, author, registration number, supervisor, department, option/specialization, faculty, institution, document type, group members, custom instructions, font, line spacing, margins, boxed/unboxed title), you MUST return a valid JSON object in this exact schema:
{
  "reply": "Your warm, natural, human-like conversational response explaining what you did and offering constructive advice (WITHOUT ANY ASTERISKS OR STARS)",
  "action_summary": "Brief 1-line summary of applied changes",
  "applied_changes": {
     "title": "optional string",
     "author": "optional string",
     "reg_number": "optional string",
     "supervisors": ["optional list of names"],
     "supervisor_ranks": ["optional list of ranks"],
     "department": "optional string",
     "option": "optional string",
     "faculty": "optional string",
     "faculty_code": "optional string",
     "school_type": "optional string",
     "institution": "uba or catuc",
     "doc_type": "optional string",
     "custom_instructions": "optional string describing user rules",
     "font_family": "optional string (e.g. Arial)",
     "font_size_pt": "optional float (e.g. 11.0)",
     "line_spacing": "optional float (e.g. 1.15)",
     "margin_left_cm": "optional float (e.g. 2.5)",
     "box_title": "optional boolean"
  },
  "suggestions": ["Next step 1", "Next step 2", "Next step 3"]
}

If no change is requested (the user is simply asking an academic question or advice), set applied_changes to null and action_summary to null, and provide a rich, detailed, articulate response.
Respond ONLY with the JSON object.
"""

def _extract_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """Helper to parse JSON from model output even if wrapped in markdown code blocks."""
    if not raw_text:
        return None
    raw_text = raw_text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except Exception:
        # Search for first JSON object
        match = re.search(r'(\{[\s\S]*\})', raw_text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
    return None

def call_groq_ai(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Calls Groq ultra-fast LPU inference (Qwen 27B / GPT-OSS 20B) within ultra-responsive bounds."""
    if not GROQ_API_KEY:
        return None
    # Prioritize fastest sub-second model: Qwen 27B (~490ms), then GPT-OSS 20B
    models = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]
    for model in models:
        try:
            with httpx.Client(timeout=3.5) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 600
                    }
                )
                if resp.status_code == 200:
                    raw_content = resp.json()["choices"][0]["message"]["content"]
                    parsed = _extract_json_response(raw_content)
                    if parsed and parsed.get("reply"):
                        return {
                            "status": "success",
                            "reply": clean_stars(parsed.get("reply", "")),
                            "applied_changes": parsed.get("applied_changes"),
                            "action_summary": clean_stars(parsed.get("action_summary", "")),
                            "suggestions": parsed.get("suggestions", ["Check Table of Contents", "Review Cover Page", "Export Document"]),
                            "engine": f"Groq ({model.split('/')[-1]})"
                        }
                    elif raw_content:
                        return {
                            "status": "success",
                            "reply": clean_stars(raw_content),
                            "applied_changes": None,
                            "action_summary": None,
                            "suggestions": ["Check Table of Contents", "Review Cover Page", "Export Document"],
                            "engine": f"Groq ({model.split('/')[-1]})"
                        }
                elif resp.status_code in [429, 503]:
                    continue
        except Exception:
            continue
    return None

def call_openrouter_ai(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Calls OpenRouter high-intelligence multi-model router."""
    if not OPENROUTER_API_KEY:
        return None
    models = [
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-small-24b-instruct-2501"
    ]
    for model in models:
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://acadformat.com",
                        "X-Title": "AcadFormat Academic AI"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 600
                    }
                )
                if resp.status_code == 200:
                    raw_content = resp.json()["choices"][0]["message"]["content"]
                    parsed = _extract_json_response(raw_content)
                    if parsed and parsed.get("reply"):
                        return {
                            "status": "success",
                            "reply": clean_stars(parsed.get("reply", "")),
                            "applied_changes": parsed.get("applied_changes"),
                            "action_summary": clean_stars(parsed.get("action_summary", "")),
                            "suggestions": parsed.get("suggestions", ["Check Table of Contents", "Review Cover Page", "Export Document"]),
                            "engine": f"OpenRouter ({model.split('/')[-1]})"
                        }
                    elif raw_content:
                        return {
                            "status": "success",
                            "reply": clean_stars(raw_content),
                            "applied_changes": None,
                            "action_summary": None,
                            "suggestions": ["Check Table of Contents", "Review Cover Page", "Export Document"],
                            "engine": f"OpenRouter ({model.split('/')[-1]})"
                        }
                elif resp.status_code in [429, 503]:
                    continue
        except Exception as e:
            print(f"[AcadFormat AI] OpenRouter ({model}) error: {e}")
            continue
    return None

def call_deepseek_ai(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Calls DeepSeek reasoning and natural language model."""
    if DEEPSEEK_API_KEY:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.2
                    }
                )
                if resp.status_code == 200:
                    raw_content = resp.json()["choices"][0]["message"]["content"]
                    parsed = _extract_json_response(raw_content)
                    if parsed:
                        return {
                            "status": "success",
                            "reply": clean_stars(parsed.get("reply", "")),
                            "applied_changes": parsed.get("applied_changes"),
                            "action_summary": clean_stars(parsed.get("action_summary", "")),
                            "suggestions": parsed.get("suggestions", ["Check Table of Contents", "Review Cover Page", "Export Document"]),
                            "engine": "DeepSeek Direct (deepseek-chat)"
                        }
        except Exception as e:
            print(f"[AcadFormat AI] DeepSeek Direct error: {e}")

    # Fallback to DeepSeek via OpenRouter
    if OPENROUTER_API_KEY:
        try:
            with httpx.Client(timeout=11.0) as client:
                resp = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://acadformat.com",
                        "X-Title": "AcadFormat Academic AI"
                    },
                    json={
                        "model": "deepseek/deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.2
                    }
                )
                if resp.status_code == 200:
                    raw_content = resp.json()["choices"][0]["message"]["content"]
                    parsed = _extract_json_response(raw_content)
                    if parsed:
                        return {
                            "status": "success",
                            "reply": clean_stars(parsed.get("reply", "")),
                            "applied_changes": parsed.get("applied_changes"),
                            "action_summary": clean_stars(parsed.get("action_summary", "")),
                            "suggestions": parsed.get("suggestions", ["Check Table of Contents", "Review Cover Page", "Export Document"]),
                            "engine": "DeepSeek (via OpenRouter)"
                        }
        except Exception as e:
            print(f"[AcadFormat AI] DeepSeek via OpenRouter error: {e}")
    return None

def call_gemini_api(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Calls Google Gemini API."""
    if not GEMINI_API_KEY:
        return None
    models = ["gemini-flash-latest", "gemini-pro-latest"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_prompt},
                        {"text": user_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }
        try:
            with httpx.Client(timeout=9.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = _extract_json_response(raw_text)
                    if parsed:
                        return {
                            "status": "success",
                            "reply": clean_stars(parsed.get("reply", "")),
                            "applied_changes": parsed.get("applied_changes"),
                            "action_summary": clean_stars(parsed.get("action_summary", "")),
                            "suggestions": parsed.get("suggestions", ["Check Table of Contents", "Review Cover Page", "Export Document"]),
                            "engine": f"Google Gemini ({model})"
                        }
        except Exception as e:
            print(f"[AcadFormat AI] Gemini API ({model}) error: {e}")
    return None

# Provider Rotation Pool for High-Volume Concurrency & Zero Restrictions
_ROTATION_PROVIDERS = [
    ("Groq Ultra-Fast", call_groq_ai),
    ("OpenRouter LLaMA 3.3 70B", call_openrouter_ai),
    ("DeepSeek Intelligence", call_deepseek_ai),
    ("Google Gemini", call_gemini_api),
]

_rotation_counter = 0
_rotation_lock = threading.Lock()

def get_rotating_providers():
    """Returns providers starting at round-robin counter and wrapping around."""
    with _rotation_lock:
        global _rotation_counter
        start_idx = _rotation_counter
        _rotation_counter = (_rotation_counter + 1) % len(_ROTATION_PROVIDERS)
    return [_ROTATION_PROVIDERS[(start_idx + i) % len(_ROTATION_PROVIDERS)] for i in range(len(_ROTATION_PROVIDERS))]


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
    action_summary = None

    # 1. Title Extraction
    title_match = re.search(
        r'(?:change|set|update|make)\s+(?:the\s+)?(?:dissertation\s+|project\s+|thesis\s+)?title\s+(?:to|as|into)?\s*[:"\'\s]+([^"\'\n\.\?]+?)(?=\s+(?:and\s+(?:my|set|supervisor|author|candidate|matricule|reg|font|margin|department|option|school|faculty|institution)|supervisor|matricule|author|\.|\?|$)|$)|'
        r'title\s*[:=]\s*["\']?([^"\'\n\.\?]+)|'
        r'(?:my\s+)?(?:project|thesis|dissertation|paper|work)\s+(?:is\s+)?(?:titled|called|on|about)\s*[:"\'\s]+([^"\'\n\.\?]+?)(?=\s+(?:and\s+(?:my|set|supervisor|author|candidate|matricule|reg|font|margin|department|option|school|faculty|institution)|supervisor|matricule|author|\.|\?|$)|$)',
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
        r'(?:(?:change|set|update|and)\s+(?:the\s+)?)?(?:author|candidate|student|my\s+name)\s*(?:to|as|is)?\s*[:"\'\s]+([A-Za-z\s\-]+?)(?=\s+(?:and\s+(?:my|set|supervisor|matricule|reg|title|font|margin|department|option|school|faculty|institution)|supervisor|matricule|reg|title|\.|\?|$)|$)|'
        r'(?:my\s+name\s+is|author\s*[:=]|by\s*:)\s*([A-Za-z\s\-]+?)(?=\s+(?:and\s+(?:my|set|supervisor|matricule|reg|title|font|margin|department|option|school|faculty|institution)|supervisor|matricule|reg|title|\.|\?|$)|$)',
        clean_msg,
        re.IGNORECASE
    )
    if author_match:
        raw_author = (author_match.group(1) or author_match.group(2) or "").strip(" \"'.,;")
        if len(raw_author.split()) >= 2 and not any(w in raw_author.lower() for w in ["supervisor", "university", "department", "assignment", "change", "please"]):
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
        r'(?:(?:change|set|update|and)\s+(?:the\s+)?)?(?:supervisor|supervised\s+by)\s*(?:to|is|as)?\s*[:"\'\s]+([A-Za-z\.\s\-]+?)(?=\s+(?:and\s+(?:my|set|author|candidate|student|matricule|reg|title|font|margin|department|option|school|faculty|institution)|matricule|reg|author|candidate|student|title|font|margin|department|option|with|\.|\?|$)|$)',
        clean_msg,
        re.IGNORECASE
    )
    if sup_match:
        raw_sup = (sup_match.group(1) or "").strip(" \"'.,;")
        if len(raw_sup) > 3 and not any(w in raw_sup.lower() for w in ["please", "how", "what", "can", "rule", "change", "author"]):
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
        elif "htttc" in low or "technical teacher" in low or "enset" in low:
            applied["institution"] = "uba"
            applied["school_type"] = "htttc"
            est_obj = ALL_ESTABLISHMENTS["htttc"]
            applied["faculty"] = est_obj["name_en"]
            applied["faculty_code"] = est_obj["code"]
            applied["motto"] = est_obj["motto"]
            actions.append("Configured HTTTC (Higher Technical Teacher Training College / ENSET Bambili)")
        elif "httc" in low or "ens bambili" in low or "teacher training college" in low:
            applied["institution"] = "uba"
            applied["school_type"] = "httc"
            est_obj = ALL_ESTABLISHMENTS["httc"]
            applied["faculty"] = est_obj["name_en"]
            applied["faculty_code"] = est_obj["code"]
            applied["motto"] = est_obj["motto"]
            actions.append("Configured HTTC (Higher Teacher Training College / ENS Bambili)")
        elif any(f in low for f in ["faculty of science", "fs uba", "nahpi", "fems", "falsh"]):
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
    if ("group" in low or "members" in low) and any(kw in low for kw in ["member", "students", "names", "list", "1.", "1 -", ",", "for "]):
        members = []
        raw_names = clean_msg
        m_match = re.search(r'(?:group\s+members?|members?|students?|candidates?|for)\s*(?:are\s*|is\s*|[:=]\s*)?([A-Za-z0-9\s,\.\(\)\/\-\n\&\;]+)', clean_msg, re.IGNORECASE)
        if m_match:
            raw_names = m_match.group(1).strip()
        
        parts = re.split(r'[\n;,]|\band\b|(?:\b\d+[\.\)]|\b\d+\s*-)', raw_names)
        for chunk in parts:
            chunk = chunk.strip(' :;.-')
            if not chunk or len(chunk) < 2:
                continue
            if any(w in chunk.lower() for w in ["assignment", "presentation", "please", "make", "change", "group", "members", "roster", "students"]):
                continue
            mat_match = re.search(r'\b(UBA[0-9A-Za-z]+|CATUC\/[0-9A-Za-z\/]+|[A-Z]{2,4}\d{4,})\b', chunk, re.IGNORECASE)
            mat = mat_match.group(1).upper() if mat_match else f"UBA24TECH{len(members)+1:02d}"
            name = re.sub(r'[\(\s]+(UBA[0-9A-Za-z]+|CATUC\/[0-9A-Za-z\/]+|[A-Z]{2,4}\d{4,})[\)]?', '', chunk, flags=re.IGNORECASE).strip(' ()')
            if len(name) >= 3:
                members.append({
                    "name": name.title(),
                    "matricule": mat,
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

    # 10. Custom Formatting & Editing Instructions (Deviations from Standard)
    custom_cands = []
    if any(k in low for k in ["arial", "calibri", "georgia", "garamond", "times new roman", "helvetica", "font to", "font size", "single space", "single spacing", "double space", "double spacing", "1.15", "1.0", "2.0", "margins to", "margin to", "unbox", "no box", "remove box", "without box", "box title", "boxed title", "custom instruction", "specific instruction"]):
        applied["custom_instructions"] = clean_msg
        if "arial" in low:
            applied["font_family"] = "Arial"
            custom_cands.append("Font: Arial")
        elif "calibri" in low:
            applied["font_family"] = "Calibri"
            custom_cands.append("Font: Calibri")
        elif "georgia" in low:
            applied["font_family"] = "Georgia"
            custom_cands.append("Font: Georgia")
        elif "garamond" in low:
            applied["font_family"] = "Garamond"
            custom_cands.append("Font: Garamond")
        elif "times new roman" in low:
            applied["font_family"] = "Times New Roman"
            custom_cands.append("Font: Times New Roman")

        f_size = re.search(r'\b(9|10|10\.5|11|11\.5|12|13|14)\s*(?:pt|points?)\b', low)
        if f_size:
            applied["font_size_pt"] = float(f_size.group(1))
            custom_cands.append(f"Font Size: {f_size.group(1)}pt")

        if "single space" in low or "single spacing" in low or " 1.0 " in f" {low} ":
            applied["line_spacing"] = 1.0
            custom_cands.append("Line Spacing: 1.0 Single")
        elif "1.15" in low:
            applied["line_spacing"] = 1.15
            custom_cands.append("Line Spacing: 1.15 Compact")
        elif "1.25" in low:
            applied["line_spacing"] = 1.25
            custom_cands.append("Line Spacing: 1.25")
        elif "double space" in low or "double spacing" in low or " 2.0 " in f" {low} ":
            applied["line_spacing"] = 2.0
            custom_cands.append("Line Spacing: 2.0 Double")

        if any(m in low for m in ["2.5cm", "2.54cm", "1 inch", "1in", "normal margin"]):
            applied["margin_left_cm"] = 2.54
            applied["margin_right_cm"] = 2.54
            applied["margin_top_cm"] = 2.54
            applied["margin_bottom_cm"] = 2.54
            custom_cands.append("Margins: 2.54cm (1 inch) Uniform")
        elif "4cm" in low or "4.0" in low:
            applied["margin_left_cm"] = 4.0
            custom_cands.append("Binding Margin: 4.0cm Left")

        if any(b in low for b in ["no box", "unboxed", "unbox", "remove box", "without box", "remove border"]):
            applied["box_title"] = False
            custom_cands.append("Cover Title: Unboxed (No border)")
        elif any(b in low for b in ["box title", "boxed title", "add box"]):
            applied["box_title"] = True
            custom_cands.append("Cover Title: Single-Line Boxed Border")

        actions.append(f"Recorded Custom Formatting Instructions: {', '.join(custom_cands) if custom_cands else clean_msg[:60]}")

    # ---------------------------------------------------------
    # Synthesize Natural Conversational Responses (Star-Free)
    # ---------------------------------------------------------
    if actions:
        action_summary = " • ".join(actions)
        reply = (
            f"I have understood your instructions and applied the following changes to your manuscript:\n\n"
            + "\n".join(f"• {act}" for act in actions)
            + "\n\n"
            f"The live preview and metadata fields in the form have been immediately updated to comply with the statutory formatting standards of {institution.upper()}."
        )
        suggestions = ["Verify Table of Contents", "Check Page Previews", "Download Re-formatted DOCX"]
        return {
            "status": "success",
            "reply": clean_stars(reply),
            "applied_changes": applied,
            "action_summary": clean_stars(action_summary),
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

    elif any(kw in low for kw in ["htttc", "httc", "enset", "ens bambili", "technical teacher"]):
        reply = (
            "**HTTTC (ENSET Bambili) vs HTTC (ENS Bambili) Institutional Differences:**\n\n"
            "• **HTTTC (Higher Technical Teacher Training College / ENSET Bambili):**\n"
            "  - Dedicated to **technical, industrial, and commercial education**.\n"
            "  - Awards: **DIPET I**, **DIPET II**, **B.Tech**, and **M.Tech**.\n"
            "  - Departments include Civil Engineering, Mechanical Engineering, Electrical & Power, Computer Science & IT, Administrative Techniques, etc.\n\n"
            "• **HTTC (Higher Teacher Training College / ENS Bambili):**\n"
            "  - Dedicated to **secondary general education and pedagogic training**.\n"
            "  - Awards: **DIPES I**, **DIPES II**, and **Postgraduate Diploma in Education**.\n"
            "  - Departments include English Modern Letters, French Modern Letters, Geography, History, Mathematics, Physics, Chemistry, Biology, etc.\n\n"
            "You can say *\"Switch to HTTTC\"* or *\"Switch to HTTC\"* and I will adjust your document configuration immediately!"
        )
        suggestions = ["Switch to HTTTC (ENSET)", "Switch to HTTC (ENS)", "View DIPET Regulations"]

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

    elif any(kw in low for kw in ["rewrite", "chapter 1", "chapter one", "re-write", "rewrite my chapter", "improve chapter", "refine chapter"]):
        inst_name = "Catholic University of Cameroon (CATUC)" if institution == "catuc" else "The University of Bamenda (UBa)"
        reply = (
            f"I am ready to help you rewrite and upgrade Chapter One of your manuscript for {inst_name}.\n\n"
            "Please paste the paragraphs of your current Chapter One draft here in the chat. I will refine it according to statutory university formatting and academic standards:\n\n"
            "• 1.1 Background to the Study (Global context -> African/Regional context -> Cameroonian context -> Local institutional context)\n"
            "• 1.2 Statement of the Problem (Clear gap in literature, practical operational deficiency, and research paradox)\n"
            "• 1.3 Objectives of the Study (One main overarching objective and 3 to 4 specific measurable objectives)\n"
            "• 1.4 Research Questions (Directly mirroring each specific objective)\n"
            "• 1.5 Research Hypotheses (where applicable for quantitative or mixed-methods studies)\n"
            "• 1.6 Significance of the Study (Benefits to educational policy, industry, academia, and society)\n"
            "• 1.7 Scope and Delimitation of the Study (Thematic, geographical, and temporal boundaries)\n"
            "• 1.8 Operational Definition of Key Terms\n\n"
            "Once you paste your draft, I will provide a refined, academically elevated version ready for your supervisor."
        )
        suggestions = ["How to write Problem Statement", "Draft Research Objectives", "Format Scope of Study"]

    elif any(kw in low for kw in ["problem statement", "statement of the problem"]):
        reply = (
            "**Formulating an Academic Statement of the Problem:**\n\n"
            "A standard Senate-compliant problem statement follows the Three-Pillar Formula:\n\n"
            "• **Pillar 1: The Ideal (The 'What Should Be'):** Describe the established statutory goal, standard, or expected benchmark.\n"
            "• **Pillar 2: The Reality & Defect (The 'What Is'):** Document the specific empirical failure, gap, or operational dilemma with citation/evidence.\n"
            "• **Pillar 3: The Consequence & Research Gap (The 'What Will Happen If Ignored'):** Demonstrate the critical damage if the gap is unaddressed, justifying your study as the solution.\n\n"
            "Paste your topic or initial notes and I will draft a powerful problem statement for your review."
        )
        suggestions = ["Help me draft Problem Statement", "Format Research Questions", "Review Chapter 1"]

    elif any(kw in low for kw in ["methodology", "chapter 3", "chapter three", "research design"]):
        reply = (
            "**Chapter Three: Research Methodology Structure:**\n\n"
            "The statutory research methodology sequence comprises:\n\n"
            "• **3.1 Research Design:** (e.g. Descriptive survey, quasi-experimental, action research, or software engineering prototyping methodology)\n"
            "• **3.2 Area / Setting of the Study:** Geographic and institutional context\n"
            "• **3.3 Population of the Study:** Target universe and accessible elements\n"
            "• **3.4 Sample and Sampling Techniques:** Purposive, stratified random, or convenience sampling with justification\n"
            "• **3.5 Instrumentation:** Questionnaire, interview guide, or technical development stack\n"
            "• **3.6 Validity and Reliability:** Cronbach's alpha, expert vetting, or pilot testing\n"
            "• **3.7 Method of Data Analysis:** Descriptive (mean, standard deviation) and inferential statistics (t-test, ANOVA, chi-square) or system test metrics."
        )
        suggestions = ["How to sample population", "Calculate Cronbach's Alpha", "Select Research Design"]

    elif any(kw in low for kw in ["literature review", "chapter 2", "chapter two"]):
        reply = (
            "**Chapter Two: Review of Related Literature Structure:**\n\n"
            "Senate guidelines require Chapter Two to be organized into four clear components:\n\n"
            "• **2.1 Conceptual Framework:** Clarification and definition of the core variables and constructs.\n"
            "• **2.2 Theoretical Framework:** 2 to 3 foundational academic theories grounding the research.\n"
            "• **2.3 Empirical Review:** Synthesizing previous research studies globally, regionally in Africa, and locally in Cameroon.\n"
            "• **2.4 Summary and Gap in Literature:** Explicitly detailing what prior authors missed and how your study fills that void."
        )
        suggestions = ["Identify Literature Gap", "Theoretical Framework tips", "Cite in APA 7th"]

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

    # Clean all stars from reply and action_summary before returning
    clean_reply = clean_stars(reply)
    clean_action = clean_stars(action_summary) if action_summary else None

    return {
        "status": "success",
        "reply": clean_reply,
        "applied_changes": applied if actions else None,
        "action_summary": clean_action,
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
    Sub-Second Intelligent Router for AcadFormat AI.
    1. Instantly runs local NLU & Action Engine (5-15ms).
    2. If an action/command is detected, returns immediately with applied_changes.
    3. If an open-ended question, queries Groq (Qwen 27B / GPT-OSS) with OpenRouter fallback.
    4. Guarantees 100% meaningful, natural language responses.
    """
    context = {
        "institution": institution,
        "doc_type": doc_type,
        "school_type": school_type,
        "metadata": metadata or {}
    }

    user_context = (
        f"Institution: {context.get('institution', 'uba').upper()}\n"
        f"Current School: {context.get('school_type', 'coltech')}\n"
        f"Current Document Type: {context.get('doc_type', 'dissertation_bsc')}\n"
        f"Current Metadata: {json.dumps(context.get('metadata', {}))}\n\n"
        f"User Message: {message}"
    )

    # 1. Instantly run local NLU action engine (takes ~5-15ms)
    local_res = parse_and_generate_local_nlp(
        message=message,
        institution=institution,
        doc_type=doc_type,
        school_type=school_type,
        metadata=metadata
    )

    # If the user prompt is an actionable instruction (e.g. title, supervisor, font, margin, school, etc.),
    # return immediately so the user experiences instantaneous execution!
    if local_res.get("applied_changes"):
        return local_res

    # 2. For open-ended questions, rewriting requests, or deep academic queries:
    # First attempt: Ultra-fast Groq LPU (Qwen 27B / GPT-OSS)
    if GROQ_API_KEY:
        try:
            future = _fast_ai_executor.submit(call_groq_ai, SYSTEM_PROMPT, user_context)
            groq_res = future.result(timeout=3.5)
            if groq_res and groq_res.get("status") == "success" and groq_res.get("reply"):
                return groq_res
        except concurrent.futures.TimeoutError:
            print("[AcadFormat AI] Groq timed out after 3.5s, trying OpenRouter...")
        except Exception as e:
            print(f"[AcadFormat AI] Groq query error: {e}")

    # Second attempt: High-capacity OpenRouter LLaMA-3.3 70B
    if OPENROUTER_API_KEY:
        try:
            future = _fast_ai_executor.submit(call_openrouter_ai, SYSTEM_PROMPT, user_context)
            or_res = future.result(timeout=3.5)
            if or_res and or_res.get("status") == "success" and or_res.get("reply"):
                return or_res
        except concurrent.futures.TimeoutError:
            print("[AcadFormat AI] OpenRouter timed out after 3.5s, falling back to local engine...")
        except Exception as e:
            print(f"[AcadFormat AI] OpenRouter query error: {e}")

    # 3. Third attempt: Enhanced local academic dialogue engine
    return local_res
