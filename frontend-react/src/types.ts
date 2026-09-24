export interface UniversityInfo {
  code: string;
  name_en: string;
  name_fr: string;
  motto: string;
  type: string;
  city: string;
  country: string;
}

export interface EstablishmentInfo {
  university: 'uba' | 'catuc';
  code: string;
  name_en: string;
  name_fr: string;
  motto: string;
  degrees: string[];
  default_doc_types: string[];
  departments: string[];
  department_options?: Record<string, string[]>;
}

export interface AcademicData {
  universities: Record<string, UniversityInfo>;
  establishments: Record<string, EstablishmentInfo>;
  uba_establishments: Record<string, EstablishmentInfo>;
  catuc_establishments: Record<string, EstablishmentInfo>;
  doc_types: Record<string, string>;
}

export interface GroupMember {
  name: string;
  matricule: string;
  participation?: string;
  grade?: string;
}

export interface DocumentMetadata {
  title: string;
  author: string;
  reg_number: string;
  degree: string;
  degree_code: string;
  option: string;
  department: string;
  faculty: string;
  faculty_code: string;
  motto: string;
  supervisors: string[];
  supervisor_ranks: string[];
  hod_name: string;
  director_name: string;
  director_title: string;
  submission_month: string;
  submission_year: string;
  host_company?: string;
  field_supervisor?: string;
  course_code?: string;
  course_title?: string;
  lecturer?: string;
  academic_year?: string;
  is_group_assignment?: boolean;
  group_name?: string;
  group_members?: GroupMember[];
  show_grading_column?: boolean;
  grading_column_title?: string;
}

export interface AuditIssue {
  id: string;
  category: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  recommendation: string;
  auto_fixable: boolean;
}

export interface AuditResult {
  doc_type: string;
  school_type: string;
  header_mode: string;
  compliance_score: number;
  total_issues: number;
  passed_checks: number;
  issues: AuditIssue[];
  detected_sections: string[];
  missing_sections: string[];
  metadata: DocumentMetadata;
  stats: Record<string, any>;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: 'user' | 'admin' | 'super_admin';
  device_id: string;
  trial_expires_at: string;
  subscription_expires_at?: string;
  created_at: string;
  last_login_at?: string;
  is_active: boolean;
}

export interface Eligibility {
  allowed: boolean;
  reason: 'free_trial' | 'paid_subscription' | 'trial_expired' | 'device_mismatch' | 'unauthorized';
  message: string;
  device_matched: boolean;
  trial_active: boolean;
  paid_active: boolean;
  trial_hours_remaining: number;
  paid_days_remaining: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  suggestions?: string[];
  engine?: string;
  applied_changes?: Record<string, any>;
  action_summary?: string;
}

