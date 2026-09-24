"""
FastAPI application for the University of Bamenda Academic Identity & Formatting Platform (AcadFormat).
Includes document analysis, UBa standard restructuring, authentication, device locking,
MTN MoMo / Orange Money paywall (250 FCFA / 7 days), and segmented Admin / Super Admin console.
"""
import os
import sys

# Ensure root dir and parent dirs are on sys.path in serverless runtime
_curr_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_curr_dir)
for _p in [_root_dir, _curr_dir, os.getcwd()]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

import uuid
import shutil
import json
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.models import (
    AuditResult, ReformatRequest, DocumentMetadata,
    SignupRequest, LoginRequest, PaymentRequest,
    ExtendUserRequest, UpdateRoleRequest, UpdateConfigRequest,
    ChatRequest
)
from backend.academic_data import (
    UNIVERSITIES, ALL_ESTABLISHMENTS, UBA_ESTABLISHMENTS,
    CATUC_ESTABLISHMENTS, DOCUMENT_TYPE_LABELS
)
from backend.chatbot import generate_chat_response
from backend.parser import parse_document
from backend.auditor import audit_document
from backend.restructurer import restructure_document
from backend.converter import convert_docx_to_pdf, generate_page_previews
from backend.database import (
    save_document_record, save_reformat_record, is_supabase_configured, list_recent_documents,
    create_user, authenticate_user, create_session, get_user_by_session, check_download_eligibility,
    record_payment, list_all_users, extend_user_subscription, update_user_role,
    get_financial_analytics, get_system_config, update_system_config, get_database_status
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _resolve_storage_dir():
    if os.environ.get("STORAGE_DIR"):
        return os.environ["STORAGE_DIR"]
    local_storage = os.path.join(BASE_DIR, "storage")
    try:
        os.makedirs(local_storage, exist_ok=True)
        test_file = os.path.join(local_storage, ".write_test")
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return local_storage
    except Exception:
        fallback = "/tmp/acadformat_storage"
        os.makedirs(fallback, exist_ok=True)
        return fallback

STORAGE_DIR = _resolve_storage_dir()

REACT_DIST_DIR = os.path.join(BASE_DIR, "frontend-react", "dist")
FRONTEND_DIR = REACT_DIST_DIR if os.path.isdir(REACT_DIST_DIR) else os.path.join(BASE_DIR, "frontend")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

try:
    os.makedirs(STORAGE_DIR, exist_ok=True)
except Exception:
    pass

try:
    os.makedirs(FRONTEND_DIR, exist_ok=True)
except Exception:
    pass

app = FastAPI(
    title="AcadFormat — University of Bamenda Academic Identity & Formatting Platform",
    description="Automated audit, restructuring, authentication, and compliance conforming to official UBa Senate standards.",
    version="2.3.0",
    redirect_slashes=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def api_path_prefix_middleware(request, call_next):
    """Normalizes request path so routes work with or without /api/ prefix in serverless environments."""
    path = request.scope.get("path", "")
    if path and not path.startswith("/api/") and path != "/api":
        target = f"/api{path}"
        for route in app.routes:
            route_path = getattr(route, "path", None)
            if route_path and (route_path == target or route_path == f"{target}/" or target == f"{route_path}/"):
                request.scope["path"] = target
                break
    return await call_next(request)

SESSIONS = {}

def get_or_restore_session(token: str):
    """Retrieves document processing session from memory or reconstructs it from disk storage."""
    if token in SESSIONS:
        return SESSIONS[token]
    session_dir = os.path.join(STORAGE_DIR, token)
    if not os.path.isdir(session_dir):
        return None
    for ext in [".docx", ".pdf", ".docx.bak"]:
        orig = os.path.join(session_dir, f"original{ext}")
        if os.path.exists(orig):
            try:
                parsed = parse_document(orig)
                audit_res = audit_document(parsed)
                session = {
                    "parsed": parsed,
                    "audit": audit_res,
                    "upload_path": orig,
                    "session_dir": session_dir,
                    "doc_type": "dissertation_bsc",
                    "school_type": "coltech",
                    "header_mode": "center_crest"
                }
                docx_path = os.path.join(session_dir, "formatted.docx")
                pdf_path = os.path.join(session_dir, "formatted.pdf")
                prev_dir = os.path.join(session_dir, "previews")
                if os.path.exists(docx_path):
                    session["formatted_docx"] = docx_path
                if os.path.exists(pdf_path):
                    session["formatted_pdf"] = pdf_path
                if os.path.isdir(prev_dir):
                    pages = sorted([os.path.join(prev_dir, f) for f in os.listdir(prev_dir) if f.endswith(".png")])
                    if pages:
                        session["preview_pages"] = pages
                SESSIONS[token] = session
                return session
            except Exception:
                pass
    return None

# ---------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------
def extract_auth_token(
    session_token: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
) -> Optional[str]:
    if session_token:
        return session_token.strip()
    if x_session_token:
        return x_session_token.strip()
    if authorization and authorization.startswith("Bearer "):
        return authorization.split("Bearer ", 1)[1].strip()
    return None

def get_current_user_from_headers(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
) -> Optional[dict]:
    token = extract_auth_token(authorization=authorization, x_session_token=x_session_token)
    if not token:
        return None
    return get_user_by_session(token)


# ---------------------------------------------------------
# Academic Registry & Metadata
# ---------------------------------------------------------
@app.get("/api/academic-data")
async def get_academic_data():
    """Returns the full registry of UBa & CATUC establishments, departments, degrees, and document types."""
    return {
        "universities": UNIVERSITIES,
        "establishments": ALL_ESTABLISHMENTS,
        "uba_establishments": UBA_ESTABLISHMENTS,
        "catuc_establishments": CATUC_ESTABLISHMENTS,
        "doc_types": DOCUMENT_TYPE_LABELS
    }


# ---------------------------------------------------------
# Ultra-Fast Localized AI Academic Assistant Chatbot
# ---------------------------------------------------------
@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    """
    Ultra-fast localized assistant for UBa & CATUC academic formatting rules.
    Sub-15ms response latency optimized for low-bandwidth environments.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Chat message cannot be empty.")

    resp = generate_chat_response(
        message=payload.message,
        institution=payload.institution or "uba",
        doc_type=payload.doc_type,
        school_type=payload.school_type,
        metadata=payload.metadata
    )
    return resp



# ---------------------------------------------------------
# Authentication Endpoints (Sign Up, Sign In, Profile, Logout)
# ---------------------------------------------------------
@app.post("/api/auth/signup")
async def auth_signup(payload: SignupRequest):
    """
    Registers a new student or researcher account:
    - Binds the account to the current device fingerprint.
    - Activates the 3-day (72-hour) free trial.
    - Validates privacy policy consent under Cameroonian Law No. 2010/012.
    """
    if not payload.privacy_accepted:
        raise HTTPException(
            status_code=400,
            detail="You must accept the AcadFormat Privacy Policy under Cameroonian Law No. 2010/012 to register."
        )

    if not payload.full_name or len(payload.full_name.strip()) < 3:
        raise HTTPException(status_code=400, detail="Full name must be at least 3 characters.")
    if not payload.username or len(payload.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if not payload.email or "@" not in payload.email:
        raise HTTPException(status_code=400, detail="A valid institutional or personal email is required.")
    if not payload.password or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if payload.confirm_password and payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    device_id = payload.device_id.strip() if payload.device_id else str(uuid.uuid4())

    success, msg, user_data = create_user(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        device_id=device_id,
        role="user"
    )

    if not success:
        raise HTTPException(status_code=400, detail=msg)

    # Issue session
    session_token = create_session(user_data["id"], device_id)
    eligibility = check_download_eligibility(user_data["id"], device_id)

    return {
        "status": "success",
        "message": "Account created successfully with 72-hour Free Trial!",
        "session_token": session_token,
        "user": user_data,
        "eligibility": eligibility
    }


@app.post("/api/auth/login")
async def auth_login(payload: LoginRequest):
    """
    Authenticates a user and performs device locking check.
    If the account is logged into from a new device, flags mismatch.
    """
    if not payload.identifier or not payload.password:
        raise HTTPException(status_code=400, detail="Username/Email and Password are required.")

    device_id = payload.device_id.strip() if payload.device_id else None

    success, msg, user = authenticate_user(payload.identifier, payload.password, device_id)
    if not success:
        raise HTTPException(status_code=401, detail=msg)

    session_token = create_session(user["id"], device_id)
    eligibility = check_download_eligibility(user["id"], device_id)

    return {
        "status": "success",
        "message": "Login successful.",
        "session_token": session_token,
        "user": user,
        "eligibility": eligibility
    }


@app.get("/api/auth/me")
async def auth_me(
    session_token: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    x_device_id: Optional[str] = Header(None)
):
    """Returns current user status, trial hours left, subscription active status, and role."""
    token = extract_auth_token(session_token, authorization, x_session_token)
    dev_id = device_id or (x_device_id.strip() if x_device_id else None)

    if not token:
        return JSONResponse(status_code=401, content={"authenticated": False, "message": "Not authenticated."})

    user = get_user_by_session(token)
    if not user:
        return JSONResponse(status_code=401, content={"authenticated": False, "message": "Session expired or invalid."})

    eligibility = check_download_eligibility(user["id"], dev_id)

    return {
        "authenticated": True,
        "user": user,
        "eligibility": eligibility
    }


@app.post("/api/auth/logout")
async def auth_logout():
    return {"status": "success", "message": "Signed out successfully."}


# ---------------------------------------------------------
# Mobile Money Payment Gateway (MTN MoMo & Orange Money)
# ---------------------------------------------------------
@app.post("/api/payments/momo-checkout")
async def momo_checkout(
    payload: PaymentRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    """
    Cameroon Mobile Money checkout endpoint:
    - Accepts MTN MoMo or Orange Money.
    - Prompts 250 FCFA for 7 days of full export access.
    - Re-binds and authorizes the paying device upon approval.
    """
    token = extract_auth_token(authorization=authorization, x_session_token=x_session_token)
    user = get_user_by_session(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to process payment.")

    operator = payload.operator.lower().strip()
    if operator not in ["mtn_momo", "orange_money"]:
        raise HTTPException(status_code=400, detail="Operator must be 'mtn_momo' or 'orange_money'.")

    phone = payload.phone_number.replace(" ", "").replace("-", "").strip()
    if not (phone.startswith("6") or phone.startswith("+2376") or phone.startswith("2376")):
        raise HTTPException(status_code=400, detail="Invalid Cameroonian Mobile Money number. Must begin with 6XXXXXXXX.")

    device_id = payload.device_id.strip() if payload.device_id else user.get("registered_device_id")

    success, msg, pay_info = record_payment(
        user_id=user["id"],
        operator=operator,
        phone_number=phone,
        device_id=device_id,
        amount=payload.amount or 250
    )

    if not success:
        raise HTTPException(status_code=500, detail=msg)

    # Return refreshed eligibility
    eligibility = check_download_eligibility(user["id"], device_id)

    return {
        "status": "success",
        "message": msg,
        "payment": pay_info,
        "eligibility": eligibility
    }


# ---------------------------------------------------------
# Document Auditing & Restructuring
# ---------------------------------------------------------
@app.post("/api/audit")
@app.post("/api/audit/")
@app.post("/api/upload")
@app.post("/api/upload/")
@app.post("/upload")
@app.post("/upload/")
@app.post("/audit")
@app.post("/audit/")
@app.post("/api/document/upload")
@app.post("/api/documents/upload")
async def audit_endpoint(
    file: UploadFile = File(...),
    doc_type: str = Form("dissertation_bsc"),
    school_type: str = Form("coltech"),
    header_mode: str = Form("center_crest")
):
    """Audits an uploaded document in milliseconds and returns the compliance scorecard."""
    token = str(uuid.uuid4())
    session_dir = os.path.join(STORAGE_DIR, token)
    os.makedirs(session_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".docx", ".pdf"]:
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported.")

    upload_path = os.path.join(session_dir, f"original{file_ext}")
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        parsed = parse_document(upload_path)

        # Infer school and doc_type from parsed metadata if detected
        if parsed.metadata.faculty_code and parsed.metadata.faculty_code.lower() in UBA_ESTABLISHMENTS:
            school_type = parsed.metadata.faculty_code.lower()
        
        if parsed.metadata.degree_code == "MTech":
            doc_type = "dissertation_mtech"
        elif parsed.metadata.degree_code == "BTech":
            doc_type = "project_btech"
        elif parsed.metadata.degree_code == "HND":
            doc_type = "project_hnd"
        elif parsed.metadata.degree_code == "PhD":
            doc_type = "thesis_phd"
        elif parsed.metadata.degree_code == "MSc":
            doc_type = "dissertation_msc"

        audit_res = audit_document(parsed, doc_type=doc_type, school_type=school_type, header_mode=header_mode)
        
        # Persist document record
        try:
            save_document_record(
                token=token,
                filename=file.filename,
                doc_type=doc_type,
                school_type=school_type,
                compliance_score=audit_res.compliance_score,
                metadata=parsed.metadata.dict(),
                issues_count=len(audit_res.issues)
            )
        except Exception as db_err:
            print(f"[AcadFormat] Error saving audit to database: {db_err}")

        SESSIONS[token] = {
            "parsed": parsed,
            "audit": audit_res,
            "upload_path": upload_path,
            "session_dir": session_dir,
            "doc_type": doc_type,
            "school_type": school_type,
            "header_mode": header_mode
        }

        return {
            "token": token,
            "filename": file.filename,
            "doc_type": doc_type,
            "school_type": school_type,
            "header_mode": header_mode,
            "audit": audit_res.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@app.post("/api/reformat")
@app.post("/api/reformat/")
@app.post("/reformat")
@app.post("/reformat/")
async def reformat_endpoint(
    token: str = Form(...),
    doc_type: str = Form("dissertation_bsc"),
    school_type: str = Form("coltech"),
    header_mode: str = Form("center_crest"),
    metadata_json: Optional[str] = Form(None)
):
    """Restructures the document into standard-compliant .docx and print-ready .pdf with page previews."""
    session = get_or_restore_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session expired or token not found. Please upload again.")

    parsed = session["parsed"]
    session_dir = session["session_dir"]

    # Clean existing generated outputs to prevent any residual page accumulation
    out_docx_path = os.path.join(session_dir, "formatted.docx")
    out_pdf_path = os.path.join(session_dir, "formatted.pdf")
    preview_dir = os.path.join(session_dir, "previews")
    if os.path.exists(out_docx_path):
        os.remove(out_docx_path)
    if os.path.exists(out_pdf_path):
        os.remove(out_pdf_path)

    # Parse metadata overrides if supplied
    meta = parsed.metadata
    if metadata_json:
        try:
            m_dict = json.loads(metadata_json)
            meta = DocumentMetadata(**m_dict)
        except Exception:
            pass

    # Ensure school and department consistency
    if school_type in ALL_ESTABLISHMENTS:
        est = ALL_ESTABLISHMENTS[school_type]
        meta.faculty = est["name_en"]
        meta.faculty_code = est["code"]
        meta.motto = est["motto"]

    req = ReformatRequest(
        doc_type=doc_type,
        school_type=school_type,
        header_mode=header_mode,
        metadata=meta
    )

    try:
        # 1. Restructure to standard DOCX
        restructure_document(parsed, req, out_docx_path)

        # 2. Convert to PDF via headless LibreOffice (if installed on system)
        out_pdf_path = None
        preview_pages = []
        try:
            out_pdf_path = convert_docx_to_pdf(out_docx_path, session_dir)
            preview_pages = generate_page_previews(out_pdf_path, preview_dir, dpi=120)
        except Exception as conv_err:
            print(f"[AcadFormat] Notice: PDF/Preview generation skipped: {conv_err}")

        session["formatted_docx"] = out_docx_path
        if out_pdf_path and os.path.exists(out_pdf_path):
            session["formatted_pdf"] = out_pdf_path
        session["preview_pages"] = preview_pages
        session["doc_type"] = doc_type
        session["school_type"] = school_type

        # Persist reformat output to database
        try:
            save_reformat_record(token, out_docx_path, out_pdf_path, len(preview_pages))
        except Exception as db_err:
            print(f"[AcadFormat] Error saving reformat to database: {db_err}")

        return {
            "token": token,
            "status": "success",
            "page_count": len(preview_pages),
            "preview_urls": [f"/api/preview/{token}/{i}" for i in range(len(preview_pages))],
            "preview_pages": [f"/api/preview/{token}/{i}" for i in range(len(preview_pages))],
            "download_docx": f"/api/download/{token}/docx",
            "download_pdf": f"/api/download/{token}/pdf" if out_pdf_path else None,
            "pdf_available": bool(out_pdf_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reformatting failed: {str(e)}")


@app.get("/api/preview/{token}/{page_idx}")
async def get_preview_page(token: str, page_idx: int):
    """Serves the rendered PNG image for the given page index."""
    session = get_or_restore_session(token)
    if not session or "preview_pages" not in session:
        raise HTTPException(status_code=404, detail="Preview not available.")
    
    pages = session["preview_pages"]
    if page_idx < 0 or page_idx >= len(pages):
        raise HTTPException(status_code=404, detail="Page index out of bounds.")

    return FileResponse(pages[page_idx], media_type="image/png")


# ---------------------------------------------------------
# Paywall Enforced Document Download
# ---------------------------------------------------------
@app.get("/api/download/{token}/{fmt}")
async def download_file(
    token: str,
    fmt: str,
    session_token: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    x_device_id: Optional[str] = Header(None)
):
    """
    Downloads either the restructured .docx or the print-ready .pdf.
    Enforces authentication, device locking, and 72-hour trial / 250 FCFA paywall rules.
    """
    session = get_or_restore_session(token)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # 1. Check Authentication
    auth_tok = extract_auth_token(session_token, authorization, x_session_token)
    if not auth_tok:
        return JSONResponse(status_code=401, content={
            "status": "unauthorized",
            "error": "authentication_required",
            "message": "Please sign in or create a free account to export official documents."
        })

    user = get_user_by_session(auth_tok)
    if not user:
        return JSONResponse(status_code=401, content={
            "status": "unauthorized",
            "error": "session_expired",
            "message": "Your session has expired. Please sign in again."
        })

    # 2. Check Device Lock & Free Trial / Paid Subscription Eligibility
    dev_id = device_id or (x_device_id.strip() if x_device_id else None)
    eligibility = check_download_eligibility(user["id"], dev_id)

    if not eligibility.get("allowed", False):
        return JSONResponse(status_code=402, content={
            "status": "payment_required",
            "reason": eligibility.get("reason", "trial_expired"),
            "message": eligibility.get("message", "Payment required to export."),
            "device_matched": eligibility.get("device_matched", True),
            "trial_active": eligibility.get("trial_active", False),
            "paid_active": eligibility.get("paid_active", False),
            "price_xaf": 250,
            "validity_days": 7,
            "operators": ["mtn_momo", "orange_money"]
        })

    # 3. Serve File
    doc_type = session.get("doc_type", "dissertation_bsc")
    school = session.get("school_type", "coltech").upper()
    prefix = f"UBa_{school}_{doc_type.capitalize()}"

    if fmt == "docx":
        path = session.get("formatted_docx")
        if not path or not os.path.exists(path):
            raise HTTPException(status_code=404, detail="DOCX file not generated.")
        return FileResponse(path, filename=f"{prefix}_Official.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    elif fmt == "pdf":
        path = session.get("formatted_pdf")
        if not path or not os.path.exists(path):
            raise HTTPException(
                status_code=404,
                detail="PDF export requires LibreOffice on the server. Please download the DOCX format, or deploy the backend with Docker/LibreOffice."
            )
        return FileResponse(path, filename=f"{prefix}_Official.pdf", media_type="application/pdf")
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'docx' or 'pdf'.")


# ---------------------------------------------------------
# Sample Loader for Instant Demonstrations
# ---------------------------------------------------------
@app.get("/api/sample/{sample_type}")
@app.post("/api/sample/{sample_type}")
@app.get("/sample/{sample_type}")
@app.post("/sample/{sample_type}")
async def load_sample(sample_type: str):
    """Loads a bundled sample document for immediate testing."""
    token = str(uuid.uuid4())
    session_dir = os.path.join(STORAGE_DIR, token)
    os.makedirs(session_dir, exist_ok=True)

    if sample_type == "coltech_dissertation":
        source_file = os.path.join(BASE_DIR, "assets", "sample_dissertation.docx")
        doc_type = "dissertation_bsc"
        school_type = "coltech"
        header_mode = "center_crest"
    elif sample_type == "user_proposal":
        source_file = os.path.join(BASE_DIR, "storage", "5460b15f-a9d3-4474-a318-d787960598a6", "original.docx")
        doc_type = "dissertation_mtech"
        school_type = "coltech"
        header_mode = "center_crest"
    else:
        source_file = os.path.join(BASE_DIR, "Format for internship Report.pdf")
        doc_type = "internship"
        school_type = "fems"
        header_mode = "center_crest"

    if not os.path.exists(source_file):
        raise HTTPException(status_code=404, detail="Sample file not found on disk.")

    target_copy = os.path.join(session_dir, os.path.basename(source_file))
    shutil.copyfile(source_file, target_copy)

    parsed = parse_document(target_copy)
    audit_res = audit_document(parsed, doc_type=doc_type, school_type=school_type, header_mode=header_mode)

    try:
        save_document_record(
            token=token,
            filename=os.path.basename(source_file),
            doc_type=doc_type,
            school_type=school_type,
            compliance_score=audit_res.compliance_score,
            metadata=parsed.metadata.dict(),
            issues_count=len(audit_res.issues)
        )
    except Exception as db_err:
        print(f"[AcadFormat] Error saving sample to database: {db_err}")

    SESSIONS[token] = {
        "parsed": parsed,
        "audit": audit_res,
        "upload_path": target_copy,
        "session_dir": session_dir,
        "doc_type": doc_type,
        "school_type": school_type,
        "header_mode": header_mode
    }

    return {
        "token": token,
        "sample_type": sample_type,
        "filename": os.path.basename(source_file),
        "doc_type": doc_type,
        "school_type": school_type,
        "header_mode": header_mode,
        "audit": audit_res.dict()
    }


# ---------------------------------------------------------
# Segmented Admin & Super Admin APIs
# ---------------------------------------------------------
def require_admin(authorization: Optional[str] = Header(None), x_session_token: Optional[str] = Header(None)):
    token = extract_auth_token(authorization=authorization, x_session_token=x_session_token)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required.")
    user = get_user_by_session(token)
    if not user or user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Administrative privileges required.")
    return user

def require_super_admin(authorization: Optional[str] = Header(None), x_session_token: Optional[str] = Header(None)):
    token = extract_auth_token(authorization=authorization, x_session_token=x_session_token)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required.")
    user = get_user_by_session(token)
    if not user or user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super Administrator privileges required.")
    return user


@app.get("/api/admin/users")
async def admin_list_users(
    search: Optional[str] = None,
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """Admin & Super Admin: Lists registered users, trial status, and device fingerprints."""
    users = list_all_users(search=search, limit=limit)
    return {"status": "success", "count": len(users), "users": users}


@app.post("/api/admin/extend-user")
async def admin_extend_user(
    payload: ExtendUserRequest,
    admin: dict = Depends(require_admin)
):
    """Admin & Super Admin: Manually grants 7 (or custom) additional days of subscription."""
    success, msg = extend_user_subscription(payload.user_id, payload.extra_days)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}


@app.get("/api/admin/documents")
async def admin_list_documents(
    limit: int = 50,
    admin: dict = Depends(require_admin)
):
    """Admin & Super Admin: Lists recently processed and reformatted documents."""
    docs = list_recent_documents(limit=limit)
    return {"status": "success", "count": len(docs), "documents": docs}


@app.get("/api/superadmin/analytics")
async def superadmin_analytics(
    sadmin: dict = Depends(require_super_admin)
):
    """Super Admin Only: Revenue ledger, MTN vs Orange breakdown, and platform stats."""
    analytics = get_financial_analytics()
    config = get_system_config()
    return {
        "status": "success",
        "analytics": analytics,
        "config": config
    }


@app.post("/api/superadmin/config")
async def superadmin_update_config(
    payload: UpdateConfigRequest,
    sadmin: dict = Depends(require_super_admin)
):
    """Super Admin Only: Adjusts pricing, trial duration, and pass duration."""
    update_system_config(
        trial_hours=payload.trial_duration_hours,
        price_xaf=payload.subscription_price_xaf,
        validity_days=payload.subscription_duration_days
    )
    return {
        "status": "success",
        "message": "System configuration updated successfully.",
        "config": get_system_config()
    }


@app.post("/api/superadmin/manage-role")
async def superadmin_manage_role(
    payload: UpdateRoleRequest,
    sadmin: dict = Depends(require_super_admin)
):
    """Super Admin Only: Promotes or demotes user roles ('user', 'admin', 'super_admin')."""
    success, msg = update_user_role(payload.target_user_id, payload.new_role)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}


# ---------------------------------------------------------
# Privacy Policy & Institutional Compliance
# ---------------------------------------------------------
@app.get("/api/privacy-policy")
async def get_privacy_policy():
    """Returns statutory privacy policy complying with Cameroonian Law No. 2010/012."""
    return {
        "status": "success",
        "jurisdiction": "Republic of Cameroon",
        "governing_law": "Law No. 2010/012 of 21 December 2010 on Cybersecurity and Cybercrime in Cameroon",
        "institution": "University of Bamenda (UBa)",
        "effective_date": "2026-01-01",
        "summary": "AcadFormat strictly processes academic manuscripts to enforce UBa Senate formatting guidelines. Personal data and uploaded documents are encrypted and never shared with unauthorized third parties.",
        "device_binding_notice": "In compliance with digital integrity and fraud prevention measures, user sessions are bound to a verified hardware identifier to prevent unauthorized account sharing."
    }


@app.get("/api/health")
async def health_check():
    """Returns platform health and multi-engine database status (Cloudflare D1, Supabase, Local SQLite)."""
    return {
        "status": "healthy",
        "app": "AcadFormat",
        "version": "2.3.0",
        "database": get_database_status()
    }


@app.get("/api/history")
async def get_history(limit: int = 15):
    """Returns recent document audit and restructuring history."""
    docs = list_recent_documents(limit=limit)
    return {
        "count": len(docs),
        "documents": docs
    }


# Unified Static Asset Handler (serves both Vite JS/CSS bundles and institutional logos)
@app.get("/assets/{file_path:path}")
async def serve_assets(file_path: str):
    # 1. Check in React build assets (dist/assets)
    react_asset = os.path.join(FRONTEND_DIR, "assets", file_path)
    if os.path.isfile(react_asset):
        return FileResponse(react_asset)
    # 2. Check in project assets (assets/)
    proj_asset = os.path.join(ASSETS_DIR, file_path)
    if os.path.isfile(proj_asset):
        return FileResponse(proj_asset)
    raise HTTPException(status_code=404, detail="Asset not found")

# Root route fallback for health status
@app.get("/")
async def root_index():
    return {
        "status": "online",
        "app": "AcadFormat Academic Identity API",
        "version": "2.3.0"
    }

# Top-level error catching middleware to prevent opaque 500 FUNCTION_INVOCATION_FAILED errors
@app.middleware("http")
async def global_exception_logging_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[AcadFormat Unhandled Error] {exc}\n{tb}", file=sys.stderr)
        return JSONResponse(status_code=500, content={
            "status": "error",
            "error": "internal_server_error",
            "message": str(exc),
            "traceback": tb.split("\n"),
            "path": request.url.path
        })
