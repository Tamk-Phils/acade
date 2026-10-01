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
  downloadDirectDocument,
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
  title: '',
  author: '',
  reg_number: '',
  degree: '',
  degree_code: '',
  option: '',
  department: '',
  faculty: '',
  faculty_code: '',
  motto: '',
  supervisors: [],
  supervisor_ranks: [],
  hod_name: '',
  director_name: '',
  director_title: '',
  submission_month: '',
  submission_year: '',
  is_group_assignment: false,
  group_name: '',
  group_members: [],
  show_grading_column: true,
  grading_column_title: 'Score / 20',
  custom_instructions: ''
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
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [currentSampleType, setCurrentSampleType] = useState<string | null>(null);
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
    setCurrentFile(file);
    setCurrentSampleType(null);
    setLoadingUpload(true);
    setPreviewPages([]); // CLEAR previous preview immediately
    try {
      const resp = await uploadDocument(file, docType, schoolType, headerMode, metadata.custom_instructions);
      setCurrentDocToken(resp.token);
      setCurrentFilename(resp.filename);
      setAudit(resp.audit);
      if (resp.audit.metadata) {
        setMetadata((prev) => ({ ...prev, ...resp.audit.metadata }));
      }
      const pages = resp.preview_pages || resp.preview_urls || [];
      if (pages.length > 0) {
        setPreviewPages(pages);
      }
    } catch (err: any) {
      alert(err.message || 'Error processing document');
    } finally {
      setLoadingUpload(false);
    }
  };

  // Sample load handler
  const handleLoadSample = async (sampleType: string) => {
    setCurrentSampleType(sampleType);
    setCurrentFile(null);
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
      const pages = resp.preview_pages || resp.preview_urls || [];
      if (pages.length > 0) {
        setPreviewPages(pages);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to load sample');
    } finally {
      setLoadingUpload(false);
    }
  };

  // Reformat & Generate Previews
  const handleReformat = async () => {
    if (!currentDocToken && !currentFile && !currentSampleType) {
      alert('Please upload a document or load a sample first.');
      return;
    }

    setReformatting(true);
    try {
      const resp = await reformatDocument(
        currentDocToken || 'direct',
        docType,
        schoolType,
        headerMode,
        metadata,
        currentFile,
        currentSampleType
      );
      if (resp.token) setCurrentDocToken(resp.token);
      const pages = resp.preview_pages || resp.preview_urls || [];
      if (pages.length > 0) {
        setPreviewPages(pages);
      }
      if (resp.audit) setAudit(resp.audit);
    } catch (err: any) {
      alert(err.message || 'Reformatting failed');
    } finally {
      setReformatting(false);
    }
  };

  // AI-Driven Changes Application Handler
  const handleApplyAIChanges = async (changes: Partial<DocumentMetadata> & { institution?: string; doc_type?: string; school_type?: string; header_mode?: string }) => {
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
    if (changes.custom_instructions !== undefined) updatedMetadata.custom_instructions = changes.custom_instructions;
    if (changes.font_family) updatedMetadata.font_family = changes.font_family;
    if (changes.font_size_pt) updatedMetadata.font_size_pt = changes.font_size_pt;
    if (changes.line_spacing) updatedMetadata.line_spacing = changes.line_spacing;
    if (changes.margin_left_cm) updatedMetadata.margin_left_cm = changes.margin_left_cm;
    if (changes.margin_right_cm) updatedMetadata.margin_right_cm = changes.margin_right_cm;
    if (changes.margin_top_cm) updatedMetadata.margin_top_cm = changes.margin_top_cm;
    if (changes.margin_bottom_cm) updatedMetadata.margin_bottom_cm = changes.margin_bottom_cm;
    if (changes.box_title !== undefined) updatedMetadata.box_title = changes.box_title;

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
    if (currentDocToken || currentFile || currentSampleType) {
      setReformatting(true);
      try {
        const resp = await reformatDocument(
          currentDocToken || 'direct',
          newDocType,
          newSchoolType,
          newHeaderMode,
          updatedMetadata,
          currentFile,
          currentSampleType
        );
        if (resp.token) setCurrentDocToken(resp.token);
        const pages = resp.preview_pages || resp.preview_urls || [];
        if (pages.length > 0) {
          setPreviewPages(pages);
        }
        if (resp.audit) setAudit(resp.audit);
      } catch (err: any) {
        console.error('Auto-reformat error after AI changes:', err);
      } finally {
        setReformatting(false);
      }
    } else {
      // If no manuscript loaded yet, auto-load default sample with the updated metadata so user can cross-check
      try {
        const sampleType = newDocType.includes('assignment') ? 'assignment' : newDocType.includes('internship') ? 'internship' : 'coltech';
        setCurrentSampleType(sampleType);
        const resp = await loadSample(sampleType);
        setCurrentDocToken(resp.token);
        setCurrentFilename(resp.filename);
        if (resp.audit?.metadata) {
          setMetadata((prev) => ({ ...prev, ...resp.audit.metadata, ...updatedMetadata }));
        }
        const pages = resp.preview_pages || resp.preview_urls || [];
        if (pages.length > 0) {
          setPreviewPages(pages);
        }
      } catch (err) {
        console.error('Auto-load sample failed:', err);
      }
    }
  };

  // Download Handler with Auth & Paywall Guard
  const handleDownload = async (fmt: 'docx' | 'pdf') => {
    if (!currentDocToken) {
      alert('No formatted manuscript ready for download.');
      return;
    }

    setDownloading(true);
    try {
      const token = localStorage.getItem('acadformat_session_token');
      const devId = localStorage.getItem('acadformat_device_id') || '';

      const downloadUrl = `/api/download/${currentDocToken}/${fmt}`;
      let res = await fetch(downloadUrl, {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
          'X-Session-Token': token || '',
          'X-Device-Id': devId
        }
      });

      if ((res.status === 404 || !res.ok) && (currentFile || currentSampleType)) {
        res = await downloadDirectDocument(docType, schoolType, headerMode, metadata, currentFile, currentSampleType, fmt);
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
            canReformat={Boolean(currentDocToken || currentFile || currentSampleType)}
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
            isProcessing={loadingUpload || reformatting}
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
