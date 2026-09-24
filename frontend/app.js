/**
 * University of Bamenda Academic Identity & Formatting Platform (AcadFormat)
 * Frontend Interactive Engine v2.3
 * Features:
 *  - Instant structural parsing & institutional scorecard
 *  - Automated UBa & COLTECH standard restructuring
 *  - Accurate dynamic Table of Contents & preliminary generation
 *  - Clean preview rendering with zero page accumulation
 *  - Authentication & 3-day (72h) free trial
 *  - Hardware-level device fingerprint binding & locking
 *  - Cameroon Mobile Money paywall (MTN MoMo & Orange Money - 250 FCFA / 7 days)
 *  - Segmented Admin & Super Admin governance console
 *  - Statutory Cameroonian Law No. 2010/012 Privacy Policy
 */

document.addEventListener('DOMContentLoaded', async () => {
  // ==========================================
  // STATE MANAGEMENT
  // ==========================================
  let currentToken = null;
  let currentAudit = null;
  let currentPageIndex = 0;
  let totalPages = 1;
  let currentZoom = 1.0;
  let fsZoom = 1.0;
  let previewUrls = [];
  let academicData = null;

  // Device & Auth State
  function getOrCreateDeviceId() {
    let devId = localStorage.getItem('acadformat_device_id');
    if (!devId) {
      devId = 'dev_' + (crypto.randomUUID ? crypto.randomUUID() : (Math.random().toString(36).substring(2) + Date.now()));
      localStorage.setItem('acadformat_device_id', devId);
    }
    return devId;
  }

  const currentDeviceId = getOrCreateDeviceId();
  let currentSessionToken = localStorage.getItem('acadformat_session_token') || null;
  let currentUser = null;
  let currentEligibility = null;
  let pendingDownloadFmt = null;

  // ==========================================
  // DOM ELEMENTS
  // ==========================================
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const statusBar = document.getElementById('statusBar');
  const statusText = document.getElementById('statusText');
  const resultsGrid = document.getElementById('resultsGrid');
  
  const docTypeSelect = document.getElementById('docTypeSelect');
  const schoolSelect = document.getElementById('schoolSelect');
  const deptSelect = document.getElementById('deptSelect');
  const headerModeSelect = document.getElementById('headerModeSelect');
  
  const btnLoadUserProposal = document.getElementById('btnLoadUserProposal');
  const btnLoadColtechSample = document.getElementById('btnLoadColtechSample');
  const btnLoadInternshipSample = document.getElementById('btnLoadInternshipSample');
  
  const documentMetaSummary = document.getElementById('documentMetaSummary');
  const scoreValue = document.getElementById('scoreValue');
  const scoreGauge = document.getElementById('scoreGauge');
  const statMargin = document.getElementById('statMargin');
  const statPages = document.getElementById('statPages');
  const statFont = document.getElementById('statFont');
  const statIllustrations = document.getElementById('statIllustrations');
  
  const btnReformat = document.getElementById('btnReformat');
  const btnEditMeta = document.getElementById('btnEditMeta');
  const issuesCount = document.getElementById('issuesCount');
  const sectionsCount = document.getElementById('sectionsCount');
  const issuesList = document.getElementById('issuesList');
  const sectionsList = document.getElementById('sectionsList');
  
  const btnDownloadDocx = document.getElementById('btnDownloadDocx');
  const btnDownloadPdf = document.getElementById('btnDownloadPdf');
  
  const previewImage = document.getElementById('previewImage');
  const pageViewport = document.getElementById('pageViewport');
  const pageNumberInput = document.getElementById('pageNumberInput');
  const totalPagesSpan = document.getElementById('totalPagesSpan');
  const btnPrevPage = document.getElementById('btnPrevPage');
  const btnNextPage = document.getElementById('btnNextPage');
  const btnZoomIn = document.getElementById('btnZoomIn');
  const btnZoomOut = document.getElementById('btnZoomOut');
  const zoomLevelText = document.getElementById('zoomLevelText');
  const thumbnailStrip = document.getElementById('thumbnailStrip');
  
  // Fullscreen Elements
  const btnFullScreen = document.getElementById('btnFullScreen');
  const fsModal = document.getElementById('fsModal');
  const btnCloseFs = document.getElementById('btnCloseFs');
  const fsPreviewImage = document.getElementById('fsPreviewImage');
  const fsPageWrapper = document.getElementById('fsPageWrapper');
  const fsDocTitle = document.getElementById('fsDocTitle');
  const fsPageBadge = document.getElementById('fsPageBadge');
  const fsBtnPrev = document.getElementById('fsBtnPrev');
  const fsBtnNext = document.getElementById('fsBtnNext');
  const fsBtnZoomIn = document.getElementById('fsBtnZoomIn');
  const fsBtnZoomOut = document.getElementById('fsBtnZoomOut');
  const fsZoomText = document.getElementById('fsZoomText');

  // Metadata Modal Elements
  const metaModal = document.getElementById('metaModal');
  const btnCloseModal = document.getElementById('btnCloseModal');
  const btnCancelMeta = document.getElementById('btnCancelMeta');
  const btnSaveMeta = document.getElementById('btnSaveMeta');
  
  const metaTitle = document.getElementById('metaTitle');
  const metaAuthor = document.getElementById('metaAuthor');
  const metaRegNo = document.getElementById('metaRegNo');
  const metaDept = document.getElementById('metaDept');
  const metaDegree = document.getElementById('metaDegree');
  const metaSupervisor = document.getElementById('metaSupervisor');
  const metaRank = document.getElementById('metaRank');
  const metaMonth = document.getElementById('metaMonth');
  const metaYear = document.getElementById('metaYear');
  const metaCourseCode = document.getElementById('metaCourseCode');
  const metaLecturer = document.getElementById('metaLecturer');
  const assignmentMetaFields = document.getElementById('assignmentMetaFields');
  const internshipMetaFields = document.getElementById('internshipMetaFields');
  const metaHostCompany = document.getElementById('metaHostCompany');
  const metaFieldSupervisor = document.getElementById('metaFieldSupervisor');
  const metaAssignmentType = document.getElementById('metaAssignmentType');
  const groupNameWrapper = document.getElementById('groupNameWrapper');
  const metaGroupName = document.getElementById('metaGroupName');
  const groupMembersSection = document.getElementById('groupMembersSection');
  const groupOverflowNotice = document.getElementById('groupOverflowNotice');
  const chkShowGrading = document.getElementById('chkShowGrading');
  const btnAddMember = document.getElementById('btnAddMember');
  const membersTableBody = document.getElementById('membersTableBody');

  // Auth Header Controls
  const loggedOutControls = document.getElementById('loggedOutControls');
  const loggedInControls = document.getElementById('loggedInControls');
  const btnOpenSignIn = document.getElementById('btnOpenSignIn');
  const btnOpenSignUp = document.getElementById('btnOpenSignUp');
  const navUserAvatar = document.getElementById('navUserAvatar');
  const navUserName = document.getElementById('navUserName');
  const navUserRole = document.getElementById('navUserRole');
  const navUserStatus = document.getElementById('navUserStatus');
  const btnNavAdmin = document.getElementById('btnNavAdmin');
  const btnNavLogout = document.getElementById('btnNavLogout');

  // Auth Modal Elements
  const authModal = document.getElementById('authModal');
  const btnCloseAuthModal = document.getElementById('btnCloseAuthModal');
  const tabBtnSignIn = document.getElementById('tabBtnSignIn');
  const tabBtnSignUp = document.getElementById('tabBtnSignUp');
  const formSignIn = document.getElementById('formSignIn');
  const formSignUp = document.getElementById('formSignUp');
  const authAlert = document.getElementById('authAlert');
  const loginIdentifier = document.getElementById('loginIdentifier');
  const loginPassword = document.getElementById('loginPassword');
  const regFullName = document.getElementById('regFullName');
  const regUsername = document.getElementById('regUsername');
  const regEmail = document.getElementById('regEmail');
  const regPassword = document.getElementById('regPassword');
  const regConfirmPassword = document.getElementById('regConfirmPassword');
  const chkPrivacyConsent = document.getElementById('chkPrivacyConsent');
  const linkSwitchToSignUp = document.getElementById('linkSwitchToSignUp');
  const linkSwitchToSignIn = document.getElementById('linkSwitchToSignIn');
  const linkOpenPrivacy = document.getElementById('linkOpenPrivacy');

  // Paywall Modal Elements
  const paywallModal = document.getElementById('paywallModal');
  const btnClosePaywall = document.getElementById('btnClosePaywall');
  const paywallBannerTitle = document.getElementById('paywallBannerTitle');
  const paywallBannerText = document.getElementById('paywallBannerText');
  const cardMtnMomo = document.getElementById('cardMtnMomo');
  const cardOrangeMoney = document.getElementById('cardOrangeMoney');
  const momoPhone = document.getElementById('momoPhone');
  const momoSimState = document.getElementById('momoSimState');
  const simStateTitle = document.getElementById('simStateTitle');
  const simStateDesc = document.getElementById('simStateDesc');
  const btnExecuteMomoPay = document.getElementById('btnExecuteMomoPay');

  // Admin Portal Elements
  const adminModal = document.getElementById('adminModal');
  const btnCloseAdminModal = document.getElementById('btnCloseAdminModal');
  const adminRoleDisplay = document.getElementById('adminRoleDisplay');
  const adminUserSearchInput = document.getElementById('adminUserSearchInput');
  const btnRefreshUsers = document.getElementById('btnRefreshUsers');
  const adminUsersTableBody = document.getElementById('adminUsersTableBody');
  const btnRefreshDocs = document.getElementById('btnRefreshDocs');
  const adminDocsTableBody = document.getElementById('adminDocsTableBody');
  const kpiRevenue = document.getElementById('kpiRevenue');
  const kpiTxCount = document.getElementById('kpiTxCount');
  const kpiUserCount = document.getElementById('kpiUserCount');
  const operatorBreakdownGrid = document.getElementById('operatorBreakdownGrid');
  const adminPaymentsTableBody = document.getElementById('adminPaymentsTableBody');
  const formSystemConfig = document.getElementById('formSystemConfig');
  const cfgTrialHours = document.getElementById('cfgTrialHours');
  const cfgPriceXaf = document.getElementById('cfgPriceXaf');
  const cfgValidityDays = document.getElementById('cfgValidityDays');
  const formStaffRole = document.getElementById('formStaffRole');
  const targetUserIdInput = document.getElementById('targetUserIdInput');
  const targetUserRoleSelect = document.getElementById('targetUserRoleSelect');

  // Privacy Modal & Footer Links
  const privacyModal = document.getElementById('privacyModal');
  const btnClosePrivacyModal = document.getElementById('btnClosePrivacyModal');
  const btnDismissPrivacy = document.getElementById('btnDismissPrivacy');
  const footerLinkPrivacy = document.getElementById('footerLinkPrivacy');
  const footerLinkPricing = document.getElementById('footerLinkPricing');
  const footerLinkAdmin = document.getElementById('footerLinkAdmin');

  // ==========================================
  // AUTHENTICATION & SESSION MANAGEMENT
  // ==========================================
  async function refreshCurrentUser() {
    if (!currentSessionToken) {
      updateAuthUI(null, null);
      return;
    }
    try {
      const res = await fetch(`/api/auth/me?session_token=${encodeURIComponent(currentSessionToken)}&device_id=${encodeURIComponent(currentDeviceId)}`);
      if (res.ok) {
        const data = await res.json();
        currentUser = data.user;
        currentEligibility = data.eligibility;
        updateAuthUI(currentUser, currentEligibility);
      } else {
        localStorage.removeItem('acadformat_session_token');
        currentSessionToken = null;
        currentUser = null;
        currentEligibility = null;
        updateAuthUI(null, null);
      }
    } catch (e) {
      console.warn('Could not refresh session:', e);
    }
  }

  function updateAuthUI(user, eligibility) {
    if (!user) {
      loggedOutControls.classList.remove('hidden');
      loggedInControls.classList.add('hidden');
      btnNavAdmin.classList.add('hidden');
      return;
    }

    loggedOutControls.classList.add('hidden');
    loggedInControls.classList.remove('hidden');

    navUserAvatar.textContent = (user.full_name ? user.full_name.charAt(0) : 'U').toUpperCase();
    navUserName.textContent = user.full_name || user.username;

    // Role display
    if (user.role === 'super_admin') {
      navUserRole.textContent = 'SUPER ADMIN';
      navUserRole.style.background = '#c69214';
      navUserRole.style.color = '#000';
    } else if (user.role === 'admin') {
      navUserRole.textContent = 'ADMIN';
      navUserRole.style.background = '#4338ca';
      navUserRole.style.color = '#fff';
    } else {
      navUserRole.textContent = 'STUDENT';
      navUserRole.style.background = 'rgba(255,255,255,0.2)';
      navUserRole.style.color = '#e2e8f0';
    }

    // Status & trial badge
    navUserStatus.className = 'badge-status';
    if (user.role === 'admin' || user.role === 'super_admin') {
      navUserStatus.textContent = 'Institutional Pass';
      navUserStatus.classList.add('badge-paid');
    } else if (eligibility && eligibility.allowed) {
      if (eligibility.reason === 'free_trial') {
        const hrs = Math.max(1, Math.floor((eligibility.trial_seconds_left || 0) / 3600));
        navUserStatus.textContent = `Trial: ${hrs}h left`;
        navUserStatus.classList.add('badge-trial');
      } else if (eligibility.reason === 'paid_subscription') {
        const days = Math.max(1, Math.floor((eligibility.paid_seconds_left || 0) / 86400));
        navUserStatus.textContent = `Active Pass: ${days}d left`;
        navUserStatus.classList.add('badge-paid');
      }
    } else {
      navUserStatus.textContent = 'Pass Expired (250 FCFA)';
      navUserStatus.classList.add('badge-expired');
      navUserStatus.style.cursor = 'pointer';
      navUserStatus.onclick = () => openPaywall('Your trial has expired. Activate 7-day export access.');
    }

    // Show Admin Console if staff
    if (user.role === 'admin' || user.role === 'super_admin') {
      btnNavAdmin.classList.remove('hidden');
    } else {
      btnNavAdmin.classList.add('hidden');
    }
  }

  // Password Visibility Eye Toggles
  document.querySelectorAll('.eye-toggle-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
      } else {
        input.type = 'password';
        btn.textContent = '👁️';
      }
    });
  });

  // Open Auth Modal
  btnOpenSignIn.addEventListener('click', () => openAuthModal('signin'));
  btnOpenSignUp.addEventListener('click', () => openAuthModal('signup'));

  function openAuthModal(mode = 'signin') {
    authModal.classList.remove('hidden');
    authAlert.classList.add('hidden');
    authAlert.textContent = '';
    if (mode === 'signup') {
      tabBtnSignUp.click();
    } else {
      tabBtnSignIn.click();
    }
  }

  btnCloseAuthModal.addEventListener('click', () => authModal.classList.add('hidden'));

  tabBtnSignIn.addEventListener('click', () => {
    tabBtnSignIn.classList.add('active');
    tabBtnSignUp.classList.remove('active');
    formSignIn.classList.remove('hidden');
    formSignUp.classList.add('hidden');
    authAlert.classList.add('hidden');
  });

  tabBtnSignUp.addEventListener('click', () => {
    tabBtnSignUp.classList.add('active');
    tabBtnSignIn.classList.remove('active');
    formSignUp.classList.remove('hidden');
    formSignIn.classList.add('hidden');
    authAlert.classList.add('hidden');
  });

  linkSwitchToSignUp.addEventListener('click', (e) => {
    e.preventDefault();
    tabBtnSignUp.click();
  });

  linkSwitchToSignIn.addEventListener('click', (e) => {
    e.preventDefault();
    tabBtnSignIn.click();
  });

  // Sign In Form Submit
  formSignIn.addEventListener('submit', async (e) => {
    e.preventDefault();
    authAlert.classList.add('hidden');
    const identifier = loginIdentifier.value.trim();
    const password = loginPassword.value;

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, password, device_id: currentDeviceId })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Sign in failed.');
      }

      currentSessionToken = data.session_token;
      localStorage.setItem('acadformat_session_token', currentSessionToken);
      currentUser = data.user;
      currentEligibility = data.eligibility;
      updateAuthUI(currentUser, currentEligibility);

      authModal.classList.add('hidden');

      if (pendingDownloadFmt) {
        const fmt = pendingDownloadFmt;
        pendingDownloadFmt = null;
        triggerFileDownload(fmt);
      }
    } catch (err) {
      authAlert.className = 'auth-alert error';
      authAlert.textContent = err.message;
      authAlert.classList.remove('hidden');
    }
  });

  // Sign Up Form Submit (No School Field, 72h Trial Activated)
  formSignUp.addEventListener('submit', async (e) => {
    e.preventDefault();
    authAlert.classList.add('hidden');

    const fullName = regFullName.value.trim();
    const username = regUsername.value.trim();
    const email = regEmail.value.trim();
    const password = regPassword.value;
    const confirmPassword = regConfirmPassword.value;

    if (password !== confirmPassword) {
      authAlert.className = 'auth-alert error';
      authAlert.textContent = 'Passwords do not match. Please verify.';
      authAlert.classList.remove('hidden');
      return;
    }

    if (!chkPrivacyConsent.checked) {
      authAlert.className = 'auth-alert error';
      authAlert.textContent = 'You must accept the Privacy Policy under Law No. 2010/012.';
      authAlert.classList.remove('hidden');
      return;
    }

    try {
      const res = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName,
          username: username,
          email: email,
          password: password,
          confirm_password: confirmPassword,
          privacy_accepted: true,
          device_id: currentDeviceId
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Registration failed.');
      }

      currentSessionToken = data.session_token;
      localStorage.setItem('acadformat_session_token', currentSessionToken);
      currentUser = data.user;
      currentEligibility = data.eligibility;
      updateAuthUI(currentUser, currentEligibility);

      authModal.classList.add('hidden');

      alert(`🎉 Welcome ${data.user.full_name}! Your 72-hour free trial is active.`);

      if (pendingDownloadFmt) {
        const fmt = pendingDownloadFmt;
        pendingDownloadFmt = null;
        triggerFileDownload(fmt);
      }
    } catch (err) {
      authAlert.className = 'auth-alert error';
      authAlert.textContent = err.message;
      authAlert.classList.remove('hidden');
    }
  });

  // Sign Out
  btnNavLogout.addEventListener('click', async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {}
    localStorage.removeItem('acadformat_session_token');
    currentSessionToken = null;
    currentUser = null;
    currentEligibility = null;
    updateAuthUI(null, null);
  });

  // ==========================================
  // CAMEROON MOBILE MONEY PAYWALL & GATEWAY
  // ==========================================
  function openPaywall(reasonMessage, reasonTitle = '3-Day Free Trial Concluded') {
    paywallModal.classList.remove('hidden');
    momoSimState.classList.add('hidden');
    btnExecuteMomoPay.disabled = false;
    btnExecuteMomoPay.textContent = '💳 Pay 250 FCFA & Unlock 7-Day Pass';

    if (reasonTitle) paywallBannerTitle.textContent = reasonTitle;
    if (reasonMessage) paywallBannerText.innerHTML = reasonMessage;
  }

  btnClosePaywall.addEventListener('click', () => paywallModal.classList.add('hidden'));

  // Operator Selection (MTN vs Orange)
  cardMtnMomo.addEventListener('click', () => {
    cardMtnMomo.classList.add('selected');
    cardOrangeMoney.classList.remove('selected');
    cardMtnMomo.querySelector('input').checked = true;
  });

  cardOrangeMoney.addEventListener('click', () => {
    cardOrangeMoney.classList.add('selected');
    cardMtnMomo.classList.remove('selected');
    cardOrangeMoney.querySelector('input').checked = true;
  });

  // Execute Mobile Money Payment
  btnExecuteMomoPay.addEventListener('click', async () => {
    const rawPhone = momoPhone.value.trim();
    if (!rawPhone || rawPhone.length < 9) {
      alert('Please enter a valid 9-digit Cameroonian phone number (6XX XXX XXX).');
      return;
    }

    const selectedOperator = document.querySelector('input[name="momoOperator"]:checked').value;
    const operatorName = selectedOperator === 'mtn_momo' ? 'MTN Mobile Money' : 'Orange Money';
    const ussdCode = selectedOperator === 'mtn_momo' ? '*126#' : '*150#';

    // Show simulated USSD push state
    momoSimState.classList.remove('hidden');
    simStateTitle.textContent = `Sending USSD Prompt to +237 ${rawPhone}...`;
    simStateDesc.innerHTML = `Please check your phone screen and enter your ${operatorName} PIN (or dial <strong>${ussdCode}</strong>) to authorize 250 FCFA.`;
    btnExecuteMomoPay.disabled = true;

    // Simulate telecom handshake
    setTimeout(async () => {
      try {
        const res = await fetch('/api/payments/momo-checkout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentSessionToken}`
          },
          body: JSON.stringify({
            operator: selectedOperator,
            phone_number: rawPhone,
            device_id: currentDeviceId,
            amount: 250
          })
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Payment authorization failed.');
        }

        simStateTitle.textContent = '✅ Payment Approved & Verified!';
        simStateDesc.textContent = `Transaction Ref: ${data.payment.transaction_ref}. 7-day export pass active!`;
        
        await refreshCurrentUser();

        setTimeout(() => {
          paywallModal.classList.add('hidden');
          if (pendingDownloadFmt) {
            const fmt = pendingDownloadFmt;
            pendingDownloadFmt = null;
            triggerFileDownload(fmt);
          }
        }, 1200);
      } catch (err) {
        simStateTitle.textContent = '❌ Payment Authorization Error';
        simStateDesc.textContent = err.message;
        btnExecuteMomoPay.disabled = false;
      }
    }, 2000);
  });

  // ==========================================
  // DOCUMENT DOWNLOAD & PAYWALL INTERCEPTOR
  // ==========================================
  btnDownloadDocx.addEventListener('click', (e) => {
    e.preventDefault();
    handleDownloadRequest('docx');
  });

  btnDownloadPdf.addEventListener('click', (e) => {
    e.preventDefault();
    handleDownloadRequest('pdf');
  });

  function handleDownloadRequest(fmt) {
    if (!currentToken) {
      alert('Please upload and restructure a document first.');
      return;
    }

    // 1. If not logged in -> Prompt Authentication
    if (!currentUser || !currentSessionToken) {
      pendingDownloadFmt = fmt;
      openAuthModal('signup');
      authAlert.className = 'auth-alert error';
      authAlert.textContent = 'Please sign in or register free to export official Senate documents.';
      authAlert.classList.remove('hidden');
      return;
    }

    // 2. Check Eligibility (72h Free Trial, Active Pass, or Device Match)
    if (!currentEligibility || !currentEligibility.allowed) {
      pendingDownloadFmt = fmt;
      if (currentEligibility && currentEligibility.reason === 'device_mismatch') {
        openPaywall(
          `Your account is locked to another device. In compliance with academic anti-sharing policies, pay <strong>250 FCFA</strong> to authorize this device for 7 days.`,
          'New Device Detected'
        );
      } else {
        openPaywall(
          `Your 72-hour free trial has ended. To download official .docx and .pdf files, activate 7 days of unlimited access for only <strong>250 FCFA</strong> via Mobile Money.`,
          'Free Trial Concluded'
        );
      }
      return;
    }

    // 3. Eligible -> Trigger download directly with auth tokens
    triggerFileDownload(fmt);
  }

  function triggerFileDownload(fmt) {
    const url = `/api/download/${currentToken}/${fmt}?session_token=${encodeURIComponent(currentSessionToken)}&device_id=${encodeURIComponent(currentDeviceId)}&v=${Date.now()}`;
    window.location.href = url;
  }

  // ==========================================
  // SEGMENTED ADMIN & SUPER ADMIN PORTAL
  // ==========================================
  btnNavAdmin.addEventListener('click', openAdminPortal);
  footerLinkAdmin.addEventListener('click', (e) => {
    e.preventDefault();
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'super_admin')) {
      openAuthModal('signin');
      authAlert.className = 'auth-alert error';
      authAlert.textContent = 'Administrative credentials required to access this portal.';
      authAlert.classList.remove('hidden');
    } else {
      openAdminPortal();
    }
  });

  function openAdminPortal() {
    adminModal.classList.remove('hidden');
    const isSuperAdmin = currentUser && currentUser.role === 'super_admin';
    adminRoleDisplay.textContent = isSuperAdmin ? 'Role: System Super Administrator' : 'Role: Academic Quality Administrator';

    // Show/hide Super Admin specific tabs
    document.querySelectorAll('.superadmin-only').forEach(el => {
      if (isSuperAdmin) el.classList.remove('hidden');
      else el.classList.add('hidden');
    });

    // Default to Users Tab
    document.querySelector('.admin-tab-btn[data-tab="adminTabUsers"]').click();
    loadAdminUsers();
  }

  btnCloseAdminModal.addEventListener('click', () => adminModal.classList.add('hidden'));

  // Admin Tab Navigation
  document.querySelectorAll('.admin-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.admin-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.admin-tab-content').forEach(c => c.classList.add('hidden'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.remove('hidden');

      if (targetId === 'adminTabUsers') loadAdminUsers();
      else if (targetId === 'adminTabDocs') loadAdminDocs();
      else if (targetId === 'adminTabFinance') loadAdminAnalytics();
    });
  });

  // Load Admin Users
  async function loadAdminUsers() {
    const query = adminUserSearchInput.value.trim();
    try {
      const res = await fetch(`/api/admin/users?search=${encodeURIComponent(query)}`, {
        headers: { 'Authorization': `Bearer ${currentSessionToken}` }
      });
      if (!res.ok) return;
      const data = await res.json();
      renderAdminUsersTable(data.users || []);
    } catch (e) {
      console.error('Error loading users:', e);
    }
  }

  adminUserSearchInput.addEventListener('input', loadAdminUsers);
  btnRefreshUsers.addEventListener('click', loadAdminUsers);

  function renderAdminUsersTable(users) {
    adminUsersTableBody.innerHTML = '';
    if (users.length === 0) {
      adminUsersTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:1rem;color:#64748b;">No registered users found.</td></tr>';
      return;
    }

    users.forEach(u => {
      const row = document.createElement('tr');
      const isTrial = u.trial_active;
      const isPaid = u.paid_active;

      let subBadge = '<span class="badge-status badge-expired">Expired</span>';
      if (isPaid) subBadge = '<span class="badge-status badge-paid">Active Pass</span>';
      else if (isTrial) subBadge = '<span class="badge-status badge-trial">Trial Active</span>';

      row.innerHTML = `
        <td><strong>#${u.id}</strong></td>
        <td>${escapeHtml(u.full_name)}</td>
        <td><code>${escapeHtml(u.username)}</code></td>
        <td>${escapeHtml(u.email)}</td>
        <td><span class="badge-role">${u.role.toUpperCase()}</span></td>
        <td><small style="color:#64748b;">${escapeHtml(u.registered_device_id || 'None')}</small></td>
        <td><small>${u.trial_expires_at.substring(0, 10)}</small></td>
        <td>${subBadge}</td>
        <td>
          <button class="btn btn-chip btn-extend-user" data-id="${u.id}" style="padding:2px 8px;font-size:0.75rem;">
            +7 Days Pass
          </button>
        </td>
      `;
      adminUsersTableBody.appendChild(row);
    });

    // Attach extension click handlers
    document.querySelectorAll('.btn-extend-user').forEach(btn => {
      btn.addEventListener('click', async () => {
        const uId = btn.getAttribute('data-id');
        try {
          const res = await fetch('/api/admin/extend-user', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${currentSessionToken}`
            },
            body: JSON.stringify({ user_id: parseInt(uId, 10), extra_days: 7 })
          });
          const d = await res.json();
          if (res.ok) {
            alert(d.message);
            loadAdminUsers();
          } else {
            alert(d.detail || 'Failed to extend user.');
          }
        } catch (e) {
          alert('Network error.');
        }
      });
    });
  }

  // Load Admin Documents
  async function loadAdminDocs() {
    try {
      const res = await fetch('/api/admin/documents', {
        headers: { 'Authorization': `Bearer ${currentSessionToken}` }
      });
      if (!res.ok) return;
      const data = await res.json();
      renderAdminDocsTable(data.documents || []);
    } catch (e) {
      console.error('Error loading documents:', e);
    }
  }

  btnRefreshDocs.addEventListener('click', loadAdminDocs);

  function renderAdminDocsTable(docs) {
    adminDocsTableBody.innerHTML = '';
    if (docs.length === 0) {
      adminDocsTableBody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:1rem;color:#64748b;">No documents audited yet.</td></tr>';
      return;
    }
    docs.forEach(d => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><code>${d.token.substring(0, 8)}...</code></td>
        <td>${escapeHtml(d.filename)}</td>
        <td>${d.doc_type}</td>
        <td>${(d.school_type || '').toUpperCase()}</td>
        <td><strong>${d.compliance_score}%</strong></td>
        <td>${escapeHtml(d.author || 'N/A')}</td>
        <td><small>${(d.created_at || '').substring(0, 10)}</small></td>
      `;
      adminDocsTableBody.appendChild(row);
    });
  }

  // Load Super Admin Financial Analytics
  async function loadAdminAnalytics() {
    try {
      const res = await fetch('/api/superadmin/analytics', {
        headers: { 'Authorization': `Bearer ${currentSessionToken}` }
      });
      if (!res.ok) return;
      const data = await res.json();
      const ana = data.analytics;

      kpiRevenue.textContent = `${(ana.total_revenue_xaf || 0).toLocaleString()} FCFA`;
      kpiTxCount.textContent = ana.total_transactions || 0;
      kpiUserCount.textContent = ana.total_users || 0;

      // Operator breakdown
      operatorBreakdownGrid.innerHTML = '';
      (ana.operator_breakdown || []).forEach(op => {
        const box = document.createElement('div');
        box.className = 'operator-kpi-box';
        const isMtn = op.operator === 'mtn_momo';
        box.innerHTML = `
          <div class="operator-badge ${isMtn ? 'mtn-badge' : 'orange-badge'}">${isMtn ? 'MTN MoMo' : 'Orange Money'}</div>
          <div style="font-size:1.25rem;font-weight:800;color:var(--uba-navy);margin-top:4px;">
            ${(op.revenue || 0).toLocaleString()} FCFA
          </div>
          <div style="font-size:0.8rem;color:#64748b;">${op.count} Completed Payments</div>
        `;
        operatorBreakdownGrid.appendChild(box);
      });

      // Payments ledger table
      adminPaymentsTableBody.innerHTML = '';
      (ana.recent_payments || []).forEach(p => {
        const r = document.createElement('tr');
        r.innerHTML = `
          <td><code>${p.transaction_ref}</code></td>
          <td>${escapeHtml(p.username)}</td>
          <td><span class="operator-badge ${p.operator === 'mtn_momo' ? 'mtn-badge' : 'orange-badge'}">${p.operator === 'mtn_momo' ? 'MTN' : 'Orange'}</span></td>
          <td>${p.phone_number}</td>
          <td><strong>${p.amount} FCFA</strong></td>
          <td><small>${p.paid_at.substring(0, 16).replace('T', ' ')}</small></td>
          <td><small>${p.expires_at.substring(0, 10)}</small></td>
        `;
        adminPaymentsTableBody.appendChild(r);
      });

      // Config form values
      if (data.config) {
        cfgTrialHours.value = data.config.trial_duration_hours || 72;
        cfgPriceXaf.value = data.config.subscription_price_xaf || 250;
        cfgValidityDays.value = data.config.subscription_duration_days || 7;
      }
    } catch (e) {
      console.error('Error loading analytics:', e);
    }
  }

  // Super Admin Config Form Submit
  formSystemConfig.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/superadmin/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentSessionToken}`
        },
        body: JSON.stringify({
          trial_duration_hours: parseInt(cfgTrialHours.value, 10),
          subscription_price_xaf: parseInt(cfgPriceXaf.value, 10),
          subscription_duration_days: parseInt(cfgValidityDays.value, 10)
        })
      });
      const data = await res.json();
      if (res.ok) alert('Platform pricing and trial configuration updated!');
      else alert(data.detail || 'Failed to update config.');
    } catch (err) {
      alert('Network error.');
    }
  });

  // Super Admin Staff Role Form Submit
  formStaffRole.addEventListener('submit', async (e) => {
    e.preventDefault();
    const tId = parseInt(targetUserIdInput.value, 10);
    const nRole = targetUserRoleSelect.value;
    try {
      const res = await fetch('/api/superadmin/manage-role', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentSessionToken}`
        },
        body: JSON.stringify({ target_user_id: tId, new_role: nRole })
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message);
        loadAdminUsers();
      } else {
        alert(data.detail || 'Failed to update role.');
      }
    } catch (err) {
      alert('Network error.');
    }
  });

  // ==========================================
  // PRIVACY POLICY MODAL
  // ==========================================
  function openPrivacyModal() {
    privacyModal.classList.remove('hidden');
  }

  linkOpenPrivacy.addEventListener('click', (e) => {
    e.preventDefault();
    openPrivacyModal();
  });

  footerLinkPrivacy.addEventListener('click', (e) => {
    e.preventDefault();
    openPrivacyModal();
  });

  footerLinkPricing.addEventListener('click', (e) => {
    e.preventDefault();
    openPaywall('AcadFormat offers a 3-day free trial, followed by 250 FCFA for 7 days of unlimited exports.');
  });

  btnClosePrivacyModal.addEventListener('click', () => privacyModal.classList.add('hidden'));
  btnDismissPrivacy.addEventListener('click', () => privacyModal.classList.add('hidden'));

  // ==========================================
  // GROUP ASSIGNMENTS ROSTER HELPERS
  // ==========================================
  function updateMemberNotice() {
    if (!membersTableBody || !groupOverflowNotice) return;
    const count = membersTableBody.children.length;
    if (count <= 5) {
      groupOverflowNotice.textContent = `✓ ${count} members: Roster table will be rendered directly on the Cover Page.`;
      groupOverflowNotice.style.color = '#137547';
    } else {
      groupOverflowNotice.textContent = `📋 ${count} members (> 5): Cover page will not have names; dedicated Page 2 member register and evaluation sheet will be generated.`;
      groupOverflowNotice.style.color = '#0b2545';
    }
  }

  function addMemberRow(name = '', matricule = '', role = '') {
    if (!membersTableBody) return;
    const rowIdx = membersTableBody.children.length + 1;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="padding:4px; text-align:center; font-weight:700;">${rowIdx}</td>
      <td style="padding:4px;"><input type="text" class="member-name-input" value="${escapeHtml(name)}" placeholder="Surname First"></td>
      <td style="padding:4px;"><input type="text" class="member-mat-input" value="${escapeHtml(matricule)}" placeholder="UBaXXYYZZZ"></td>
      <td style="padding:4px;"><input type="text" class="member-role-input" value="${escapeHtml(role)}" placeholder="e.g. Lead, Analysis"></td>
      <td style="padding:4px; text-align:center;"><button type="button" class="btn-remove-member" title="Remove">&times;</button></td>
    `;
    tr.querySelector('.btn-remove-member').addEventListener('click', () => {
      tr.remove();
      Array.from(membersTableBody.children).forEach((r, idx) => {
        r.cells[0].textContent = idx + 1;
      });
      updateMemberNotice();
    });
    membersTableBody.appendChild(tr);
    updateMemberNotice();
  }

  if (btnAddMember) {
    btnAddMember.addEventListener('click', () => addMemberRow());
  }

  // ==========================================
  // METADATA & REFORMATTING ENGINE
  // ==========================================
  btnEditMeta.addEventListener('click', openMetaModal);
  btnCloseModal.addEventListener('click', closeModal);
  btnCancelMeta.addEventListener('click', closeModal);
  btnReformat.addEventListener('click', executeReformat);

  function openMetaModal() {
    if (!currentAudit) return;
    metaModal.classList.remove('hidden');
    const m = currentAudit.metadata || {};
    metaTitle.value = m.title || '';
    metaAuthor.value = m.author || '';
    metaRegNo.value = m.reg_number || '';
    metaDept.value = m.department || '';
    metaDegree.value = m.degree || '';
    metaSupervisor.value = (m.supervisors && m.supervisors[0]) || '';
    metaRank.value = (m.supervisor_ranks && m.supervisor_ranks[0]) || 'Associate Professor';
    metaMonth.value = m.submission_month || 'AUGUST';
    metaYear.value = m.submission_year || '2026';

    const dType = docTypeSelect.value;
    if (dType === 'internship') {
      internshipMetaFields.classList.remove('hidden');
      metaHostCompany.value = m.host_company || '';
      metaFieldSupervisor.value = m.field_supervisor || '';
    } else {
      internshipMetaFields.classList.add('hidden');
    }

    if (dType === 'assignment') {
      assignmentMetaFields.classList.remove('hidden');
      metaCourseCode.value = m.course_code || 'CE401: Software Engineering';
      metaLecturer.value = m.lecturer || 'Dr. Lecturer Name';
      metaAssignmentType.value = m.is_group_assignment ? 'group' : 'personal';
      metaGroupName.value = m.group_name || 'Group 1';

      if (m.is_group_assignment) {
        groupNameWrapper.classList.remove('hidden');
        groupMembersSection.classList.remove('hidden');
        membersTableBody.innerHTML = '';
        if (m.group_members && m.group_members.length > 0) {
          m.group_members.forEach(mem => addMemberRow(mem.name, mem.matricule, mem.participation));
        } else {
          addMemberRow(m.author, m.reg_number, 'Lead Coordinator');
        }
      } else {
        groupNameWrapper.classList.add('hidden');
        groupMembersSection.classList.add('hidden');
      }
    } else {
      assignmentMetaFields.classList.add('hidden');
    }
  }

  function closeModal() {
    metaModal.classList.add('hidden');
  }

  if (metaAssignmentType) {
    metaAssignmentType.addEventListener('change', () => {
      const isGrp = metaAssignmentType.value === 'group';
      if (isGrp) {
        groupNameWrapper.classList.remove('hidden');
        groupMembersSection.classList.remove('hidden');
        if (membersTableBody.children.length === 0) {
          addMemberRow(metaAuthor.value || 'Candidate Name', metaRegNo.value || 'UBaXXYYZZZ', 'Lead Coordinator');
        }
      } else {
        groupNameWrapper.classList.add('hidden');
        groupMembersSection.classList.add('hidden');
      }
    });
  }

  btnSaveMeta.addEventListener('click', () => {
    if (!currentAudit) return;
    currentAudit.metadata = currentAudit.metadata || {};
    currentAudit.metadata.title = metaTitle.value.trim();
    currentAudit.metadata.author = metaAuthor.value.trim();
    currentAudit.metadata.reg_number = metaRegNo.value.trim();
    currentAudit.metadata.department = metaDept.value.trim();
    currentAudit.metadata.degree = metaDegree.value.trim();
    currentAudit.metadata.supervisors = [metaSupervisor.value.trim()];
    currentAudit.metadata.supervisor_ranks = [metaRank.value.trim()];
    currentAudit.metadata.submission_month = metaMonth.value.trim().toUpperCase();
    currentAudit.metadata.submission_year = metaYear.value.trim();

    if (docTypeSelect.value === 'internship') {
      currentAudit.metadata.host_company = metaHostCompany.value.trim();
      currentAudit.metadata.field_supervisor = metaFieldSupervisor.value.trim();
    }

    if (docTypeSelect.value === 'assignment') {
      currentAudit.metadata.course_code = metaCourseCode.value.trim();
      currentAudit.metadata.lecturer = metaLecturer.value.trim();
      const isGroup = metaAssignmentType.value === 'group';
      currentAudit.metadata.is_group_assignment = isGroup;
      currentAudit.metadata.group_name = metaGroupName.value.trim();
      currentAudit.metadata.show_grading_column = chkShowGrading ? chkShowGrading.checked : true;

      if (isGroup) {
        const rows = Array.from(membersTableBody.children);
        const members = rows.map(r => ({
          name: r.querySelector('.member-name-input').value.trim(),
          matricule: r.querySelector('.member-mat-input').value.trim(),
          participation: r.querySelector('.member-role-input').value.trim(),
          grade: '____ / 20'
        })).filter(m => m.name.length > 0);

        currentAudit.metadata.group_members = members.length > 0 ? members : [
          { name: currentAudit.metadata.author, matricule: currentAudit.metadata.reg_number, participation: 'Lead', grade: '____ / 20' }
        ];
      } else {
        currentAudit.metadata.group_members = [];
      }
    }
    
    closeModal();
    renderScorecard(currentAudit);
    executeReformat();
  });

  // Standard Page Navigation
  btnPrevPage.addEventListener('click', () => goToPage(currentPageIndex - 1));
  btnNextPage.addEventListener('click', () => goToPage(currentPageIndex + 1));

  pageNumberInput.addEventListener('change', () => {
    const val = parseInt(pageNumberInput.value, 10);
    if (!isNaN(val) && val >= 1 && val <= totalPages) {
      goToPage(val - 1);
    }
  });

  btnZoomIn.addEventListener('click', () => {
    currentZoom = Math.min(2.2, currentZoom + 0.15);
    applyZoom();
  });

  btnZoomOut.addEventListener('click', () => {
    currentZoom = Math.max(0.5, currentZoom - 0.15);
    applyZoom();
  });

  function applyZoom() {
    pageViewport.style.transform = `scale(${currentZoom})`;
    zoomLevelText.textContent = `${Math.round(currentZoom * 100)}%`;
  }

  // Full Screen Preview
  btnFullScreen.addEventListener('click', openFullscreen);
  btnCloseFs.addEventListener('click', closeFullscreen);
  fsBtnPrev.addEventListener('click', () => goToPage(currentPageIndex - 1));
  fsBtnNext.addEventListener('click', () => goToPage(currentPageIndex + 1));

  fsBtnZoomIn.addEventListener('click', () => {
    fsZoom = Math.min(2.5, fsZoom + 0.15);
    applyFsZoom();
  });

  fsBtnZoomOut.addEventListener('click', () => {
    fsZoom = Math.max(0.6, fsZoom - 0.15);
    applyFsZoom();
  });

  function applyFsZoom() {
    fsPageWrapper.style.transform = `scale(${fsZoom})`;
    fsZoomText.textContent = `${Math.round(fsZoom * 100)}%`;
  }

  function openFullscreen() {
    fsModal.classList.remove('hidden');
    fsZoom = 1.0;
    applyFsZoom();
    updateFsView();
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  }

  function closeFullscreen() {
    fsModal.classList.add('hidden');
    if (document.fullscreenElement && document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
  }

  function updateFsView() {
    if (!previewUrls || previewUrls.length === 0) return;
    fsPreviewImage.src = previewUrls[currentPageIndex];
    fsPageBadge.textContent = `Page ${currentPageIndex + 1} of ${totalPages}`;
    if (currentAudit && currentAudit.metadata) {
      fsDocTitle.textContent = currentAudit.metadata.title || 'Document Preview';
    }
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (!fsModal.classList.contains('hidden')) closeFullscreen();
      else if (!metaModal.classList.contains('hidden')) closeModal();
      else if (!authModal.classList.contains('hidden')) authModal.classList.add('hidden');
      else if (!paywallModal.classList.contains('hidden')) paywallModal.classList.add('hidden');
      else if (!adminModal.classList.contains('hidden')) adminModal.classList.add('hidden');
      else if (!privacyModal.classList.contains('hidden')) privacyModal.classList.add('hidden');
    } else if (e.key === 'ArrowRight' || e.key === 'PageDown') {
      if (currentPageIndex < totalPages - 1) goToPage(currentPageIndex + 1);
    } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
      if (currentPageIndex > 0) goToPage(currentPageIndex - 1);
    }
  });

  // ==========================================
  // DOCUMENT AUDITING & RESTRUCTURING PIPELINE
  // ==========================================
  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-active');
  });

  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-active'));
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-active');
    if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files[0]);
  });

  async function handleFileUpload(file) {
    showStatus(`Auditing "${file.name}" against University of Bamenda standards...`);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docTypeSelect.value);
    formData.append('school_type', schoolSelect.value);
    formData.append('header_mode', headerModeSelect.value);

    try {
      const response = await fetch('/api/audit', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Audit request failed');
      }

      const data = await response.json();
      currentToken = data.token;
      currentAudit = data.audit;

      if (data.doc_type) docTypeSelect.value = data.doc_type;
      if (data.school_type) {
        schoolSelect.value = data.school_type;
        populateDepartments(data.school_type);
        if (data.audit.metadata && data.audit.metadata.department) {
          deptSelect.value = data.audit.metadata.department;
        }
      }

      renderScorecard(data.audit, data.filename);
      hideStatus();

      executeReformat();
    } catch (err) {
      hideStatus();
      alert(`Error auditing document: ${err.message}`);
    }
  }

  // Sample Loaders
  btnLoadUserProposal.addEventListener('click', () => loadSampleDocument('user_proposal'));
  btnLoadColtechSample.addEventListener('click', () => loadSampleDocument('coltech_dissertation'));
  btnLoadInternshipSample.addEventListener('click', () => loadSampleDocument('internship_report'));

  async function loadSampleDocument(sampleType) {
    showStatus('Loading sample manuscript and auditing...');

    try {
      const response = await fetch(`/api/sample/${sampleType}`);
      if (!response.ok) throw new Error('Could not load sample document');

      const data = await response.json();
      currentToken = data.token;
      currentAudit = data.audit;

      if (data.doc_type) docTypeSelect.value = data.doc_type;
      if (data.school_type) {
        schoolSelect.value = data.school_type;
        populateDepartments(data.school_type);
        if (data.audit.metadata && data.audit.metadata.department) {
          deptSelect.value = data.audit.metadata.department;
        }
      }
      if (data.header_mode) headerModeSelect.value = data.header_mode;

      renderScorecard(data.audit, data.filename);
      hideStatus();

      executeReformat();
    } catch (err) {
      hideStatus();
      alert(`Error loading sample: ${err.message}`);
    }
  }

  function renderScorecard(audit, filename = '') {
    resultsGrid.classList.remove('hidden');

    const meta = audit.metadata || {};
    const authorStr = meta.author ? `Candidate: ${meta.author}` : 'Candidate';
    documentMetaSummary.textContent = `${meta.title ? meta.title.substring(0, 60) + '...' : filename} (${authorStr})`;

    const score = audit.compliance_score || 0;
    scoreValue.textContent = `${score}%`;
    
    let gaugeColor = '#137547';
    if (score < 60) gaugeColor = '#d90429';
    else if (score < 80) gaugeColor = '#c69214';
    
    scoreGauge.style.background = `conic-gradient(${gaugeColor} 0% ${score}%, #e2e8f0 ${score}% 100%)`;

    const stats = audit.stats || {};
    statMargin.textContent = `${stats.left_margin_cm || '4.0'} cm`;
    statPages.textContent = stats.estimated_pages || '20';
    statFont.textContent = (stats.fonts_detected && stats.fonts_detected[0]) ? stats.fonts_detected[0].substring(0, 15) : 'Times New Roman';
    statIllustrations.textContent = `${stats.tables_count || 0} / ${stats.figures_count || 0}`;

    issuesCount.textContent = audit.issues ? audit.issues.length : 0;
    issuesList.innerHTML = '';
    if (audit.issues && audit.issues.length > 0) {
      audit.issues.forEach(issue => {
        const item = document.createElement('div');
        item.className = `issue-item ${issue.severity}`;
        item.innerHTML = `
          <div class="issue-header">
            <span class="issue-cat">${issue.category}</span>
            <span class="issue-badge ${issue.severity}">${issue.severity.toUpperCase()}</span>
          </div>
          <div class="issue-msg">${escapeHtml(issue.message)}</div>
          <div class="issue-rec">💡 <strong>UBa Fix:</strong> ${escapeHtml(issue.recommendation)}</div>
        `;
        issuesList.appendChild(item);
      });
    } else {
      issuesList.innerHTML = '<div class="issue-item info"><div class="issue-msg">🎉 100% compliant with all University of Bamenda standards!</div></div>';
    }

    const allSections = [
      ...(audit.detected_sections || []).map(s => ({ name: s, passed: true })),
      ...(audit.missing_sections || []).map(s => ({ name: s, passed: false }))
    ];
    sectionsCount.textContent = allSections.length;
    sectionsList.innerHTML = '';
    allSections.forEach(s => {
      const item = document.createElement('div');
      item.className = `section-check-item ${s.passed ? 'passed' : 'missing'}`;
      item.innerHTML = `
        <span class="section-name">${escapeHtml(s.name)}</span>
        <span class="section-status ${s.passed ? 'passed' : 'missing'}">${s.passed ? '✓ Present' : '✗ Missing (Auto-Injected)'}</span>
      `;
      sectionsList.appendChild(item);
    });
  }

  async function executeReformat() {
    if (!currentToken) return;

    showStatus("Restructuring document into UBa standard .docx and compiling print-ready .pdf...");
    btnReformat.disabled = true;

    // Purge preview container so old document pages are never shown
    previewImage.src = '';
    previewUrls = [];
    currentPageIndex = 0;
    totalPages = 1;
    totalPagesSpan.textContent = '...';
    pageNumberInput.value = 1;
    thumbnailStrip.innerHTML = '<div style="color: #64748b; font-size: 0.82rem; padding: 12px; display: flex; align-items: center; gap: 8px;"><div class="spinner" style="width:16px;height:16px;border-width:2px;"></div> Restructuring manuscript...</div>';
    if (fsPreviewImage) fsPreviewImage.src = '';

    if (currentAudit && currentAudit.metadata) {
      currentAudit.metadata.department = deptSelect.value;
      currentAudit.metadata.option = deptSelect.value;
    }

    const formData = new FormData();
    formData.append('token', currentToken);
    formData.append('doc_type', docTypeSelect.value);
    formData.append('school_type', schoolSelect.value);
    formData.append('header_mode', headerModeSelect.value);
    if (currentAudit && currentAudit.metadata) {
      formData.append('metadata_json', JSON.stringify(currentAudit.metadata));
    }

    try {
      const response = await fetch('/api/reformat', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Reformatting failed');
      }

      const result = await response.json();
      hideStatus();
      btnReformat.disabled = false;

      const cacheBust = Date.now();
      const rawUrls = result.preview_urls || [];
      previewUrls = rawUrls.map(u => `${u}?v=${cacheBust}`);
      totalPages = previewUrls.length || 1;
      totalPagesSpan.textContent = totalPages;
      pageNumberInput.max = totalPages;

      renderThumbnails();
      goToPage(0);

    } catch (err) {
      hideStatus();
      btnReformat.disabled = false;
      alert(`Reformatting error: ${err.message}`);
    }
  }

  function goToPage(index) {
    if (index < 0 || index >= previewUrls.length) return;
    currentPageIndex = index;
    pageNumberInput.value = index + 1;
    previewImage.src = previewUrls[index];

    document.querySelectorAll('.thumb-item').forEach((t, i) => {
      if (i === index) {
        t.classList.add('active');
        t.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      } else {
        t.classList.remove('active');
      }
    });

    if (!fsModal.classList.contains('hidden')) {
      updateFsView();
    }
  }

  function renderThumbnails() {
    thumbnailStrip.innerHTML = '';
    previewUrls.forEach((url, i) => {
      const thumb = document.createElement('div');
      thumb.className = `thumb-item ${i === currentPageIndex ? 'active' : ''}`;
      thumb.innerHTML = `
        <img src="${url}" alt="Page ${i + 1}">
        <span class="thumb-num">${i + 1}</span>
      `;
      thumb.addEventListener('click', () => goToPage(i));
      thumbnailStrip.appendChild(thumb);
    });
  }

  // Dynamic Department Population
  async function loadAcademicRegistry() {
    try {
      const res = await fetch('/api/academic-data');
      if (res.ok) {
        academicData = await res.json();
        populateDepartments(schoolSelect.value);
      }
    } catch (e) {
      console.warn('Academic data could not be fetched:', e);
    }
  }

  function populateDepartments(schoolCode) {
    if (!academicData || !academicData.establishments) return;
    const est = academicData.establishments[schoolCode];
    if (!est) return;

    deptSelect.innerHTML = '';
    (est.departments || []).forEach(dept => {
      const opt = document.createElement('option');
      opt.value = dept;
      opt.textContent = dept;
      deptSelect.appendChild(opt);
    });
  }

  schoolSelect.addEventListener('change', () => {
    populateDepartments(schoolSelect.value);
    if (currentToken) executeReformat();
  });

  docTypeSelect.addEventListener('change', () => {
    if (currentToken) executeReformat();
  });

  headerModeSelect.addEventListener('change', () => {
    if (currentToken) executeReformat();
  });

  deptSelect.addEventListener('change', () => {
    if (currentToken) executeReformat();
  });

  function showStatus(msg) {
    statusText.textContent = msg;
    statusBar.classList.remove('hidden');
  }

  function hideStatus() {
    statusBar.classList.add('hidden');
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Initialize
  await loadAcademicRegistry();
  await refreshCurrentUser();
});
