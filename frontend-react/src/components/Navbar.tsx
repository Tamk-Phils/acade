import React from 'react';
import { User, Eligibility } from '../types';

interface NavbarProps {
  institution: 'uba' | 'catuc';
  onSelectInstitution: (inst: 'uba' | 'catuc') => void;
  onOpenChat: () => void;
  onOpenAuth: () => void;
  onOpenAdmin: () => void;
  user: User | null;
  eligibility: Eligibility | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  institution,
  onSelectInstitution,
  onOpenChat,
  onOpenAuth,
  onOpenAdmin,
  user,
  eligibility,
  onLogout
}) => {
  return (
    <header className="navbar">
      <div className="navbar-container">
        {/* Brand & Platform Emblem */}
        <div className="brand-wrapper">
          <img
            src="/assets/acadformat_logo.png"
            alt="AcadFormat Emblem"
            className="brand-logo"
          />
          <div className="brand-titles">
            <span className="brand-name">
              AcadFormat
              <span className="brand-tag">v2.3 Standard</span>
            </span>
            <span className="brand-subtitle">
              Academic Document Standardization & Compliance Platform
            </span>
          </div>
        </div>

        {/* Institution Switcher (UBa vs CATUC Bamenda) */}
        <div className="institution-switcher">
          <button
            type="button"
            className={`institution-btn ${institution === 'uba' ? 'active' : ''}`}
            onClick={() => onSelectInstitution('uba')}
          >
            UBa Bambili
          </button>
          <button
            type="button"
            className={`institution-btn ${institution === 'catuc' ? 'active' : ''}`}
            onClick={() => onSelectInstitution('catuc')}
          >
            CATUC Bamenda
          </button>
        </div>

        {/* Navigation Actions */}
        <div className="nav-actions">
          {/* AI Formatting Assistant Trigger */}
          <button
            type="button"
            className="btn-nav-chat"
            onClick={onOpenChat}
            title="Open formatting assistant"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            Ask AI Assistant
          </button>

          {/* Admin Portal Button */}
          {user && (user.role === 'admin' || user.role === 'super_admin') && (
            <button
              type="button"
              className="btn-tool"
              onClick={onOpenAdmin}
              style={{ background: '#1E293B', color: '#FCD34D', borderColor: '#C5A059' }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
              Admin Console
            </button>
          )}

          {/* Auth State Button */}
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                type="button"
                className="auth-status-btn"
                title={`Logged in as ${user.full_name} (${user.email})`}
              >
                <span>{user.full_name.split(' ')[0]}</span>
                <span className={`role-badge ${user.role}`}>
                  {user.role === 'super_admin' ? 'Super Admin' : user.role === 'admin' ? 'Admin' : 'Student'}
                </span>
              </button>
              <button
                type="button"
                className="btn-tool"
                onClick={onLogout}
                title="Sign out of account"
                style={{ padding: '0.45rem 0.65rem' }}
              >
                Sign Out
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="auth-status-btn"
              onClick={onOpenAuth}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              Sign In / Register
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

