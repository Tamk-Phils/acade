import React, { useState, useEffect } from 'react';
import { loginUser, signupUser } from '../services/api';
import { User, Eligibility } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthSuccess: (user: User, eligibility: Eligibility) => void;
  onOpenPrivacy: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onAuthSuccess,
  onOpenPrivacy
}) => {
  const [mode, setMode] = useState<'signin' | 'register'>('signin');

  // Sign In Fields (isolated)
  const [loginIdentifier, setLoginIdentifier] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);

  // Register Fields (isolated)
  const [regFullName, setRegFullName] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showRegConfirmPassword, setShowRegConfirmPassword] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // When modal opens, clear transient error and prefill last username if available
  useEffect(() => {
    if (isOpen) {
      setError(null);
      setLoginPassword('');
      setRegPassword('');
      setRegConfirmPassword('');
      const lastUser = localStorage.getItem('acadformat_last_user');
      if (lastUser && !loginIdentifier) {
        setLoginIdentifier(lastUser);
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanId = loginIdentifier.trim();
    if (!cleanId || !loginPassword) {
      setError('Please enter your username or email, and password.');
      return;
    }

    setLoading(true);
    try {
      const resp = await loginUser(cleanId, loginPassword);
      try {
        localStorage.setItem('acadformat_last_user', cleanId);
      } catch (_) {}
      setLoginPassword('');
      onAuthSuccess(resp.user, resp.eligibility);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanFullName = regFullName.trim();
    const cleanUsername = regUsername.trim();
    const cleanEmail = regEmail.trim().toLowerCase();

    if (!cleanFullName || cleanFullName.length < 3) {
      setError('Full name must be at least 3 characters.');
      return;
    }
    if (!cleanUsername || cleanUsername.length < 3) {
      setError('Username must be at least 3 characters.');
      return;
    }
    if (!cleanEmail || !cleanEmail.includes('@')) {
      setError('A valid institutional or personal email is required.');
      return;
    }
    if (!regPassword || regPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (!privacyAccepted) {
      setError('You must accept the Privacy Policy under Law No. 2010/012.');
      return;
    }

    setLoading(true);
    try {
      const resp = await signupUser({
        full_name: cleanFullName,
        username: cleanUsername,
        email: cleanEmail,
        password: regPassword,
        confirm_password: regConfirmPassword,
        privacy_accepted: privacyAccepted
      });

      try {
        localStorage.setItem('acadformat_last_user', cleanUsername);
      } catch (_) {}
      setLoginIdentifier(cleanUsername);
      setRegPassword('');
      setRegConfirmPassword('');
      onAuthSuccess(resp.user, resp.eligibility);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (newMode: 'signin' | 'register') => {
    setMode(newMode);
    setError(null);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              type="button"
              className={`admin-tab ${mode === 'signin' ? 'active' : ''}`}
              onClick={() => switchMode('signin')}
              style={{ fontSize: '1rem', paddingBottom: '0.25rem' }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`admin-tab ${mode === 'register' ? 'active' : ''}`}
              onClick={() => switchMode('register')}
              style={{ fontSize: '1rem', paddingBottom: '0.25rem' }}
            >
              Create Account (3-Day Free Trial)
            </button>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close authentication modal"
            style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: '#64748B' }}
          >
            ✕
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div style={{ padding: '0.65rem 0.85rem', background: '#FEF2F2', border: '1px solid #FCA5A5', color: '#DC2626', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', marginBottom: '1rem' }}>
              {error}
            </div>
          )}

          {mode === 'signin' ? (
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label className="form-label">Username or Email</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. your_username or name@email.com"
                  required
                  autoComplete="username"
                  value={loginIdentifier}
                  onChange={(e) => setLoginIdentifier(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showLoginPassword ? 'text' : 'password'}
                    className="form-control"
                    placeholder="Enter account password"
                    required
                    autoComplete="current-password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowLoginPassword(!showLoginPassword)}
                    style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: '#64748B' }}
                  >
                    {showLoginPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
                🔒 Device Locking: Your account will be authenticated for this device.
              </div>

              <button
                type="submit"
                className="btn-submit-format"
                disabled={loading}
              >
                {loading ? 'Authenticating...' : 'Sign In'}
              </button>

              <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('register')}
                  style={{ background: 'none', border: 'none', color: 'var(--color-accent)', cursor: 'pointer', fontWeight: 600, padding: 0 }}
                >
                  Create one (3-Day Free Trial)
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleSignup}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Njitapon Ahmed Said Assan"
                  required
                  autoComplete="name"
                  value={regFullName}
                  onChange={(e) => setRegFullName(e.target.value)}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Username</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. ahmedsaid"
                    required
                    autoComplete="username"
                    value={regUsername}
                    onChange={(e) => setRegUsername(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <input
                    type="email"
                    className="form-control"
                    placeholder="e.g. student@univ-bamenda.cm"
                    required
                    autoComplete="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showRegPassword ? 'text' : 'password'}
                      className="form-control"
                      placeholder="At least 6 characters"
                      required
                      autoComplete="new-password"
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowRegPassword(!showRegPassword)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: '#64748B' }}
                    >
                      {showRegPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Confirm Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showRegConfirmPassword ? 'text' : 'password'}
                      className="form-control"
                      placeholder="Repeat password"
                      required
                      autoComplete="new-password"
                      value={regConfirmPassword}
                      onChange={(e) => setRegConfirmPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowRegConfirmPassword(!showRegConfirmPassword)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: '#64748B' }}
                    >
                      {showRegConfirmPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Law No. 2010/012 Compliance Checkbox */}
              <div style={{ margin: '1rem 0' }}>
                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.775rem', color: 'var(--color-text-main)', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    required
                    checked={privacyAccepted}
                    onChange={(e) => setPrivacyAccepted(e.target.checked)}
                    style={{ marginTop: '3px' }}
                  />
                  <span>
                    I accept the{' '}
                    <strong
                      onClick={(e) => { e.preventDefault(); onOpenPrivacy(); }}
                      style={{ color: 'var(--color-accent)', textDecoration: 'underline' }}
                    >
                      AcadFormat Privacy & Data Protection Policy
                    </strong>{' '}
                    under Cameroonian Law No. 2010/012 on Cybersecurity and Cybercrime.
                  </span>
                </label>
              </div>

              <button
                type="submit"
                className="btn-submit-format"
                disabled={loading}
              >
                {loading ? 'Registering...' : 'Register & Start 72-Hour Free Trial'}
              </button>

              <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                Already registered?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signin')}
                  style={{ background: 'none', border: 'none', color: 'var(--color-accent)', cursor: 'pointer', fontWeight: 600, padding: 0 }}
                >
                  Sign In to your account
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
