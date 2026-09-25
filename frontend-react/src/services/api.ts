import { AcademicData, AuditResult, DocumentMetadata, Eligibility, User } from '../types';

const API_BASE = ((import.meta as any)?.env?.VITE_API_URL ? String((import.meta as any).env.VITE_API_URL).replace(/\/+$/, '') : '') + '/api';

export function getDeviceFingerprint(): string {
  let devId = localStorage.getItem('acadformat_device_id');
  if (!devId) {
    devId = 'dev_' + Math.random().toString(36).substring(2, 12) + '_' + Date.now().toString(36);
    localStorage.setItem('acadformat_device_id', devId);
  }
  return devId;
}

export function getAuthToken(): string | null {
  return localStorage.getItem('acadformat_session_token');
}

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem('acadformat_session_token', token);
  } else {
    localStorage.removeItem('acadformat_session_token');
  }
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'X-Device-Id': getDeviceFingerprint()
  };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    headers['X-Session-Token'] = token;
  }
  return headers;
}

export async function fetchAcademicData(): Promise<AcademicData> {
  const res = await fetch(`${API_BASE}/academic-data`);
  if (!res.ok) throw new Error('Failed to load academic registry');
  return res.json();
}

export async function uploadDocument(
  file: File,
  docType: string,
  schoolType: string,
  headerMode: string = 'center_crest'
): Promise<{ token: string; filename: string; doc_type: string; school_type: string; header_mode?: string; audit: AuditResult; preview_pages?: string[]; preview_urls?: string[]; page_count?: number }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('doc_type', docType);
  formData.append('school_type', schoolType);
  formData.append('header_mode', headerMode);

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Failed to upload document');
  }
  return res.json();
}

export async function loadSample(sampleType: string): Promise<{ token: string; filename: string; doc_type: string; school_type: string; header_mode: string; audit: AuditResult; preview_pages?: string[]; preview_urls?: string[]; page_count?: number }> {
  const res = await fetch(`${API_BASE}/sample/${sampleType}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to load sample' }));
    throw new Error(err.detail || 'Sample load failed');
  }
  return res.json();
}

export async function reformatDocument(
  token: string,
  docType: string,
  schoolType: string,
  headerMode: string,
  metadata: DocumentMetadata
): Promise<{ status: string; token: string; preview_pages?: string[]; preview_urls?: string[]; audit: AuditResult }> {
  const formData = new FormData();
  formData.append('token', token);
  formData.append('doc_type', docType);
  formData.append('school_type', schoolType);
  formData.append('header_mode', headerMode);
  formData.append('metadata_json', JSON.stringify(metadata));

  const res = await fetch(`${API_BASE}/reformat`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Reformatting failed' }));
    throw new Error(err.detail || 'Reformatting process encountered an error');
  }
  return res.json();
}

export async function sendChatMessage(
  message: string,
  institution: string = 'uba',
  docType?: string,
  schoolType?: string,
  metadata?: any
): Promise<{
  status: string;
  reply: string;
  suggestions?: string[];
  engine?: string;
  applied_changes?: Record<string, any>;
  action_summary?: string;
}> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      institution,
      doc_type: docType,
      school_type: schoolType,
      metadata
    })
  });
  if (!res.ok) throw new Error('Chat assistant unavailable');
  return res.json();
}

export async function checkAuthMe(): Promise<{ authenticated: boolean; user?: User; eligibility?: Eligibility }> {
  const token = getAuthToken();
  if (!token) return { authenticated: false };

  const devId = getDeviceFingerprint();
  const res = await fetch(`${API_BASE}/auth/me?session_token=${encodeURIComponent(token)}&device_id=${encodeURIComponent(devId)}`, {
    headers: authHeaders()
  });
  if (!res.ok) return { authenticated: false };
  return res.json();
}

export async function loginUser(identifier: string, password: string): Promise<{ user: User; session_token: string; eligibility: Eligibility }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      identifier,
      password,
      device_id: getDeviceFingerprint()
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await res.json();
  setAuthToken(data.session_token);
  return data;
}

export async function signupUser(payload: {
  full_name: string;
  username: string;
  email: string;
  password: string;
  confirm_password?: string;
  privacy_accepted: boolean;
}): Promise<{ user: User; session_token: string; eligibility: Eligibility }> {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...payload,
      device_id: getDeviceFingerprint()
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Signup failed' }));
    throw new Error(err.detail || 'Signup failed');
  }
  const data = await res.json();
  setAuthToken(data.session_token);
  return data;
}

export async function logoutUser(): Promise<void> {
  setAuthToken(null);
  await fetch(`${API_BASE}/auth/logout`, { method: 'POST' }).catch(() => {});
}

export async function processMoMoPayment(payload: {
  operator: 'mtn_momo' | 'orange_money';
  phone_number: string;
  amount: number;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/payments/momo-checkout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify({
      ...payload,
      device_id: getDeviceFingerprint()
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Payment verification failed' }));
    throw new Error(err.detail || 'Payment failed');
  }
  return res.json();
}

export async function fetchAdminUsers(search?: string): Promise<{ users: User[] }> {
  const url = search ? `${API_BASE}/admin/users?search=${encodeURIComponent(search)}` : `${API_BASE}/admin/users`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new Error('Administrative privileges required');
  return res.json();
}

export async function extendUserPass(userId: number, extraDays: number = 7): Promise<any> {
  const res = await fetch(`${API_BASE}/admin/extend-user`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify({ user_id: userId, extra_days: extraDays })
  });
  if (!res.ok) throw new Error('Failed to extend subscription');
  return res.json();
}

export async function fetchAdminDocuments(): Promise<{ documents: any[] }> {
  const res = await fetch(`${API_BASE}/admin/documents`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Failed to load document logs');
  return res.json();
}

export async function fetchSuperAdminAnalytics(): Promise<any> {
  const res = await fetch(`${API_BASE}/superadmin/analytics`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Super Admin access required');
  return res.json();
}

export async function updateSystemConfig(payload: {
  trial_duration_hours: number;
  subscription_price_xaf: number;
  subscription_duration_days: number;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/superadmin/config`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to update system config');
  return res.json();
}

export async function updateUserRole(userId: number, newRole: string): Promise<any> {
  const res = await fetch(`${API_BASE}/superadmin/manage-role`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify({ target_user_id: userId, new_role: newRole })
  });
  if (!res.ok) throw new Error('Failed to update role');
  return res.json();
}
