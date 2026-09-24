import React, { useState } from 'react';
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
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Register Fields
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await loginUser(identifier, password);
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

    if (password !== confirmPassword) {
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
        full_name: fullName,
        username,
        email,
        password,
        confirm_password: confirmPassword,
        privacy_accepted: privacyAccepted
      });
      onAuthSuccess(resp.user, resp.eligibility);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              type="button"
              className={`admin-tab ${mode === 'signin' ? 'active' : ''}`}
              onClick={() => { setMode('signin'); setError(null); }}
              style={{ fontSize: '1rem', paddingBottom: '0.25rem' }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`admin-tab ${mode === 'register' ? 'active' : ''}`}
              onClick={() => { setMode('register'); setError(null); }}
              style={{ fontSize: '1rem', paddingBottom: '0.25rem' }}
            >
              Create Account (3-Day Free Trial)
            </button>
          </div>
          <button
            type="button"
            onClick={onClose}
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
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="form-control"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: '#64748B' }}
                  >
                    {showPassword ? 'Hide' : 'Show'}
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
            </form>
          ) : (
            <form onSubmit={handleSignup}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Username</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <input
                    type="email"
                    className="form-control"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className="form-control"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: '#64748B' }}
                    >
                      {showPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Confirm Password</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      className="form-control"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: '#64748B' }}
                    >
                      {showConfirmPassword ? 'Hide' : 'Show'}
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
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

