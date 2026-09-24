import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { HeroBanner } from './components/HeroBanner';
import { UploadZone } from './components/UploadZone';
import { ConfigPanel } from './components/ConfigPanel';
import { AuditScorecard } from './components/AuditScorecard';
import { LivePreview } from './components/LivePreview';
import { AIChatDrawer } from './components/AIChatDrawer';
import { AuthModal } from './components/AuthModal';
import { PaywallModal } from './components/PaywallModal';
import { AdminPortal } from './components/AdminPortal';
import { PrivacyModal } from './components/PrivacyModal';
import { Footer } from './components/Footer';

import {
  fetchAcademicData,
  uploadDocument,
  loadSample,
  reformatDocument,
  checkAuthMe,
  logoutUser
} from './services/api';
import {
  AcademicData,
  AuditResult,
  DocumentMetadata,
  Eligibility,
  User
} from './types';

const defaultMetadata: DocumentMetadata = {
  title: 'DESIGN AND IMPLEMENTATION OF AN ENTERPRISE ACADEMIC REPOSITORY',
  author: 'NJITAPON AHMED SAID ASSAN',
  reg_number: 'UBA2SPP228',
  degree: 'Bachelor of Technology',
  degree_code: 'BTech',
  option: 'Computer Engineering',
  department: 'Computer Engineering',
  faculty: 'COLLEGE OF TECHNOLOGY',
  faculty_code: 'COLTECH',
  motto: 'Building capacities in innovative technology for development',
  supervisors: ['Pr. ONABID MATHIAS'],
  supervisor_ranks: ['Professor'],
  hod_name: 'Pr. Head of Department',
  director_name: 'Pr. Mathias Fru Fonteh',
  director_title: 'Director',
  submission_month: 'JUNE',
  submission_year: '2026',
  is_group_assignment: false,
  group_name: 'Group 1',
  group_members: [],
  show_grading_column: true,
  grading_column_title: 'Score / 20'
};

export const App: React.FC = () => {
  const [academicData, setAcademicData] = useState<AcademicData | null>(null);
  const [institution, setInstitution] = useState<'uba' | 'catuc'>('uba');
  const [schoolType, setSchoolType] = useState<string>('coltech');
  const [docType, setDocType] = useState<string>('dissertation_bsc');
  const [headerMode, setHeaderMode] = useState<string>('center_crest');
  const [metadata, setMetadata] = useState<DocumentMetadata>(defaultMetadata);

  const [currentDocToken, setCurrentDocToken] = useState<string | null>(null);
  const [currentFilename, setCurrentFilename] = useState<string | undefined>();
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [previewPages, setPreviewPages] = useState<string[]>([]);

  // Auth & Subscription
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [eligibility, setEligibility] = useState<Eligibility | null>(null);

  // Loaders
  const [loadingUpload, setLoadingUpload] = useState<boolean>(false);
  const [reformatting, setReformatting] = useState<boolean>(false);
  const [downloading, setDownloading] = useState<boolean>(false);

  // Modals
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);
  const [isAuthOpen, setIsAuthOpen] = useState<boolean>(false);
  const [isPaywallOpen, setIsPaywallOpen] = useState<boolean>(false);
  const [isAdminOpen, setIsAdminOpen] = useState<boolean>(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState<boolean>(false);
  const [aiPrefilledPrompt, setAiPrefilledPrompt] = useState<string>('');

  const handlePromptAI = (prompt: string) => {
    setAiPrefilledPrompt(prompt);
    setIsChatOpen(true);
  };

  // Initialize data and check session
  useEffect(() => {
    fetchAcademicData()
      .then((data) => setAcademicData(data))
      .catch((err) => console.error('Academic data fetch error:', err));

    checkAuthMe()
      .then((res) => {
        if (res.authenticated && res.user) {
          setCurrentUser(res.user);
          setEligibility(res.eligibility || null);
        }
      })
      .catch(() => {});
  }, []);

  // Sync establishment changes when switching institution
  const handleSelectInstitution = (inst: 'uba' | 'catuc') => {
    setInstitution(inst);
    if (!academicData?.establishments) return;

    if (inst === 'uba') {
      setSchoolType('coltech');
      const est = academicData.establishments['coltech'];
      if (est) {
        setMetadata((prev) => ({
          ...prev,
          faculty: est.name_en,
          faculty_code: est.code,
          motto: est.motto,
          department: est.departments[0] || prev.department
        }));
      }
    } else {
      setSchoolType('catuc_seng');
      const est = academicData.establishments['catuc_seng'];
      if (est) {
        setMetadata((prev) => ({
          ...prev,
          faculty: est.name_en,
          faculty_code: est.code,
          motto: est.motto,
          department: est.departments[0] || prev.department
        }));
      }
    }
  };

  const handleSchoolTypeChange = (newSchool: string) => {
    setSchoolType(newSchool);
    const est = academicData?.establishments[newSchool];
    if (est) {
      setMetadata((prev) => ({
        ...prev,
        faculty: est.name_en,
        faculty_code: est.code,
        motto: est.motto,
        department: est.departments[0] || prev.department
      }));
    }
  };

  const handleDocTypeChange = (newDocType: string) => {
    setDocType(newDocType);
    if (newDocType === 'assignment') {
      setHeaderMode('dual_logo');
    } else {
      setHeaderMode('center_crest');
    }
  };

  // Upload handler
  const handleFileUpload = async (file: File) => {
    setLoadingUpload(true);
    setPreviewPages([]); // CLEAR previous preview immediately
    try {
      const resp = await uploadDocument(file, docType, schoolType, headerMode);
      setCurrentDocToken(resp.token);
      setCurrentFilename(resp.filename);
      setAudit(resp.audit);
      if (resp.audit.metadata) {
        setMetadata((prev) => ({ ...prev, ...resp.audit.metadata }));
      }
    } catch (err: any) {
      alert(err.message || 'Error processing document');
    } finally {
      setLoadingUpload(false);
    }
  };

  // Sample load handler
  const handleLoadSample = async (sampleType: string) => {
    setLoadingUpload(true);
    setPreviewPages([]); // CLEAR previous preview immediately
    try {
      const resp = await loadSample(sampleType);
      setCurrentDocToken(resp.token);
      setCurrentFilename(resp.filename);
      setDocType(resp.doc_type);
      setSchoolType(resp.school_type);
      setHeaderMode(resp.header_mode);
      setAudit(resp.audit);
      if (resp.audit.metadata) {
        setMetadata((prev) => ({ ...prev, ...resp.audit.metadata }));
      }
    } catch (err: any) {
      alert(err.message || 'Failed to load sample');
    } finally {
      setLoadingUpload(false);
    }
  };

  // Reformat & Generate Previews
  const handleReformat = async () => {
    if (!currentDocToken) {
      alert('Please upload a document or load a sample first.');
      return;
    }

    setReformatting(true);
    setPreviewPages([]); // CLEAR to avoid mixing
    try {
      const resp = await reformatDocument(
        currentDocToken,
        docType,
        schoolType,
        headerMode,
        metadata
      );
      setPreviewPages(resp.preview_pages || resp.preview_urls || []);
      setAudit(resp.audit);
    } catch (err: any) {
      alert(err.message || 'Reformatting failed');
    } finally {
      setReformatting(false);
    }
  };

  // AI Assistant Document Mutation Handler
  const handleApplyAIChanges = async (changes: Record<string, any>) => {
    if (!changes) return;

    let updatedMetadata: DocumentMetadata = { ...metadata };
    let newDocType = docType;
    let newSchoolType = schoolType;
    let newInstitution = institution;
    let newHeaderMode = headerMode;

    if (changes.title) updatedMetadata.title = changes.title;
    if (changes.author) updatedMetadata.author = changes.author;
    if (changes.reg_number) updatedMetadata.reg_number = changes.reg_number;
    if (changes.supervisors) updatedMetadata.supervisors = changes.supervisors;
    if (changes.supervisor_ranks) updatedMetadata.supervisor_ranks = changes.supervisor_ranks;
    if (changes.department) updatedMetadata.department = changes.department;
    if (changes.option) updatedMetadata.option = changes.option;
    if (changes.faculty) updatedMetadata.faculty = changes.faculty;
    if (changes.faculty_code) updatedMetadata.faculty_code = changes.faculty_code;
    if (changes.motto) updatedMetadata.motto = changes.motto;
    if (changes.is_group_assignment !== undefined) updatedMetadata.is_group_assignment = changes.is_group_assignment;
    if (changes.group_members) updatedMetadata.group_members = changes.group_members;
    if (changes.show_grading_column !== undefined) updatedMetadata.show_grading_column = changes.show_grading_column;

    if (changes.institution && changes.institution !== institution) {
      newInstitution = changes.institution as 'uba' | 'catuc';
      setInstitution(newInstitution);
    }
    if (changes.school_type && changes.school_type !== schoolType) {
      newSchoolType = changes.school_type;
      setSchoolType(newSchoolType);
    }
    if (changes.doc_type && changes.doc_type !== docType) {
      newDocType = changes.doc_type;
      setDocType(newDocType);
    }
    if (changes.header_mode && changes.header_mode !== headerMode) {
      newHeaderMode = changes.header_mode;
      setHeaderMode(newHeaderMode);
    }

    setMetadata(updatedMetadata);

    // If an active manuscript is loaded, trigger restructuring with updated metadata immediately
    if (currentDocToken) {
      setReformatting(true);
      try {
        const resp = await reformatDocument(
          currentDocToken,
          newDocType,
          newSchoolType,
          newHeaderMode,
          updatedMetadata
        );
        setPreviewPages(resp.preview_pages || resp.preview_urls || []);
        if (resp.audit) setAudit(resp.audit);
      } catch (err: any) {
        console.error('Auto-reformat error after AI changes:', err);
      } finally {
        setReformatting(false);
      }
    }
  };

  // Download Handler with Auth & Paywall Guard
  const handleDownload = async (fmt: 'docx' | 'pdf') => {
    if (!currentDocToken) {
      alert('No formatted manuscript ready for download.');
      return;
    }

    // 1. If not logged in, prompt sign in
    if (!currentUser) {
      setIsAuthOpen(true);
      return;
    }

    setDownloading(true);
    try {
      const token = localStorage.getItem('acadformat_session_token');
      const devId = localStorage.getItem('acadformat_device_id') || '';

      const downloadUrl = `/api/download/${currentDocToken}/${fmt}`;
      const res = await fetch(downloadUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
          'X-Session-Token': token || '',
          'X-Device-Id': devId
        }
      });

      if (res.status === 401) {
        setIsAuthOpen(true);
        return;
      }

      if (res.status === 402) {
        const errorData = await res.json().catch(() => ({}));
        setEligibility({
          allowed: false,
          reason: errorData.reason || 'trial_expired',
          message: errorData.message || 'Payment required to export.',
          device_matched: errorData.device_matched ?? true,
          trial_active: errorData.trial_active ?? false,
          paid_active: errorData.paid_active ?? false,
          trial_hours_remaining: 0,
          paid_days_remaining: 0
        });
        setIsPaywallOpen(true);
        return;
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Download failed' }));
        throw new Error(err.detail || 'Download failed');
      }

      // Trigger browser file download
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${institution.toUpperCase()}_${schoolType.toUpperCase()}_${docType.toUpperCase()}_Official.${fmt}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(err.message || 'Download error');
    } finally {
      setDownloading(false);
    }
  };

  const handleLogout = async () => {
    await logoutUser();
    setCurrentUser(null);
    setEligibility(null);
  };

  return (
    <div className="app-root">
      {/* Navigation Header */}
      <Navbar
        institution={institution}
        onSelectInstitution={handleSelectInstitution}
        onOpenChat={() => setIsChatOpen(true)}
        onOpenAuth={() => setIsAuthOpen(true)}
        onOpenAdmin={() => setIsAdminOpen(true)}
        user={currentUser}
        eligibility={eligibility}
        onLogout={handleLogout}
      />

      {/* Hero & Standards Banner */}
      <HeroBanner
        institution={institution}
        onOpenPrivacy={() => setIsPrivacyOpen(true)}
      />

      {/* Main Workspace Layout */}
      <main className="main-container">
        {/* Left Column: Workflow Controls & Form */}
        <section className="sidebar-panel">
          <UploadZone
            onFileUpload={handleFileUpload}
            onLoadSample={handleLoadSample}
            loading={loadingUpload}
            currentFilename={currentFilename}
          />

          <ConfigPanel
            academicData={academicData}
            institution={institution}
            schoolType={schoolType}
            onSchoolTypeChange={handleSchoolTypeChange}
            docType={docType}
            onDocTypeChange={handleDocTypeChange}
            headerMode={headerMode}
            onHeaderModeChange={setHeaderMode}
            metadata={metadata}
            onMetadataChange={setMetadata}
            onReformat={handleReformat}
            reformatting={reformatting}
            canReformat={Boolean(currentDocToken)}
          />

          <AuditScorecard audit={audit} />
        </section>

        {/* Right Column: Live Document Inspection Viewport */}
        <section className="workspace-panel">
          <LivePreview
            previewPages={previewPages}
            docType={docType}
            token={currentDocToken || undefined}
            onDownload={handleDownload}
            downloading={downloading}
            metadata={metadata}
            onPromptAI={handlePromptAI}
          />
        </section>
      </main>

      {/* Footer */}
      <Footer onOpenPrivacy={() => setIsPrivacyOpen(true)} />

      {/* Floating AI Assistant Drawer */}
      <AIChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        institution={institution}
        docType={docType}
        schoolType={schoolType}
        metadata={metadata}
        onApplyChanges={handleApplyAIChanges}
        prefilledPrompt={aiPrefilledPrompt}
        onClearPrefilledPrompt={() => setAiPrefilledPrompt('')}
      />

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={(u, el) => {
          setCurrentUser(u);
          setEligibility(el);
        }}
        onOpenPrivacy={() => {
          setIsAuthOpen(false);
          setIsPrivacyOpen(true);
        }}
      />

      {/* MoMo / Orange Paywall Modal */}
      <PaywallModal
        isOpen={isPaywallOpen}
        onClose={() => setIsPaywallOpen(false)}
        eligibility={eligibility}
        onPaymentSuccess={() => {
          checkAuthMe().then((res) => {
            if (res.user) {
              setCurrentUser(res.user);
              setEligibility(res.eligibility || null);
            }
          });
        }}
      />

      {/* Admin / Super Admin Portal */}
      {currentUser && (currentUser.role === 'admin' || currentUser.role === 'super_admin') && (
        <AdminPortal
          isOpen={isAdminOpen}
          onClose={() => setIsAdminOpen(false)}
          currentUser={currentUser}
        />
      )}

      {/* Statutory Privacy Policy Modal */}
      <PrivacyModal
        isOpen={isPrivacyOpen}
        onClose={() => setIsPrivacyOpen(false)}
      />
    </div>
  );
};
