"""
Pydantic data models for the University of Bamenda Formatting Platform.
Includes document structures, audit results, authentication, device locking, and mobile payments.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class GroupMember(BaseModel):
    name: str = ""
    matricule: str = ""
    participation: Optional[str] = ""
    grade: Optional[str] = ""

class DocumentMetadata(BaseModel):
    title: str = "TITLE OF THE WORK"
    author: str = "CANDIDATE FULL NAME"
    reg_number: str = "UBaXXYYZZZ"
    degree: str = "Bachelor of Science"
    degree_code: str = "BSc"  # "BSc", "BTech", "HND", "MSc", "MTech", "MEng", "PhD"
    option: str = "Computer Engineering"
    department: str = "Computer Engineering"
    faculty: str = "College of Technology"
    faculty_code: str = "COLTECH"
    motto: str = "Building capacities in innovative technology for development"
    supervisors: List[str] = ["Pr. CHARLES FORBACHA"]
    supervisor_ranks: List[str] = ["Associate Professor"]
    hod_name: str = "Pr. Head of Department"
    director_name: str = "Pr. Mathias Fru Fonteh"
    director_title: str = "Director"
    submission_month: str = "JUNE"
    submission_year: str = "2026"
    host_company: Optional[str] = None
    field_supervisor: Optional[str] = None
    course_code: Optional[str] = "CE401"
    course_title: Optional[str] = "Software Engineering Principles"
    lecturer: Optional[str] = "Dr. Lecturer Name"
    academic_year: Optional[str] = "2025/2026"
    
    # Group assignment parameters
    is_group_assignment: bool = False
    group_name: Optional[str] = "Group 1"
    group_members: List[GroupMember] = Field(default_factory=list)
    show_grading_column: bool = True
    grading_column_title: str = "Score / 20"

class AuditIssue(BaseModel):
    id: str
    category: str  # "structure", "typography", "margins", "preliminaries", "pagination", "references"
    severity: str  # "error", "warning", "info"
    message: str
    recommendation: str
    auto_fixable: bool = True

class AuditResult(BaseModel):
    doc_type: str
    school_type: str
    header_mode: str = "center_crest"
    compliance_score: int
    total_issues: int
    passed_checks: int
    issues: List[AuditIssue]
    detected_sections: List[str]
    missing_sections: List[str]
    metadata: DocumentMetadata
    stats: Dict[str, Any] = Field(default_factory=dict)

class ReformatRequest(BaseModel):
    doc_type: str = "dissertation_bsc"
    school_type: str = "coltech"
    header_mode: str = "center_crest"
    metadata: Optional[DocumentMetadata] = None
    apply_margins: bool = True
    apply_typography: bool = True
    apply_preliminaries: bool = True
    apply_toc: bool = True
    apply_pagination: bool = True

# ---------------------------------------------------------
# Auth, Mobile Payments & Admin Models
# ---------------------------------------------------------
class SignupRequest(BaseModel):
    full_name: str
    username: str
    email: str
    password: str
    confirm_password: Optional[str] = None
    privacy_accepted: bool
    device_id: str

class LoginRequest(BaseModel):
    identifier: str
    password: str
    device_id: Optional[str] = None

class PaymentRequest(BaseModel):
    operator: str  # "mtn_momo" or "orange_money"
    phone_number: str
    device_id: Optional[str] = None
    amount: int = 250

class ExtendUserRequest(BaseModel):
    user_id: int
    extra_days: int = 7

class UpdateRoleRequest(BaseModel):
    target_user_id: int
    new_role: str  # "user", "admin", "super_admin"

class UpdateConfigRequest(BaseModel):
    trial_duration_hours: int = 72
    subscription_price_xaf: int = 250
    subscription_duration_days: int = 7

class ChatRequest(BaseModel):
    message: str
    institution: Optional[str] = "uba"
    doc_type: Optional[str] = None
    school_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

