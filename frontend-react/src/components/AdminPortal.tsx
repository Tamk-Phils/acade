import React, { useState, useEffect } from 'react';
import { User } from '../types';
import {
  fetchAdminUsers,
  extendUserPass,
  fetchAdminDocuments,
  fetchSuperAdminAnalytics,
  updateSystemConfig,
  updateUserRole
} from '../services/api';

interface AdminPortalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: User;
}

export const AdminPortal: React.FC<AdminPortalProps> = ({
  isOpen,
  onClose,
  currentUser
}) => {
  const [activeTab, setActiveTab] = useState<'users' | 'documents' | 'analytics' | 'config'>('users');
  const [users, setUsers] = useState<User[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [systemConfig, setSystemConfig] = useState<any>({
    trial_duration_hours: 72,
    subscription_price_xaf: 250,
    subscription_duration_days: 7
  });

  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const isSuperAdmin = currentUser.role === 'super_admin';

  useEffect(() => {
    if (isOpen) {
      loadTabData();
    }
  }, [isOpen, activeTab]);

  const loadTabData = async () => {
    setLoading(true);
    setActionMsg(null);
    try {
      if (activeTab === 'users') {
        const res = await fetchAdminUsers(search);
        setUsers(res.users);
      } else if (activeTab === 'documents') {
        const res = await fetchAdminDocuments();
        setDocuments(res.documents);
      } else if (activeTab === 'analytics' || activeTab === 'config') {
        if (isSuperAdmin) {
          const res = await fetchSuperAdminAnalytics();
          setAnalytics(res.analytics);
          if (res.config) setSystemConfig(res.config);
        }
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleExtend = async (userId: number) => {
    try {
      await extendUserPass(userId, 7);
      setActionMsg(`Granted 7 additional days to user #${userId}`);
      loadTabData();
    } catch (err: any) {
      alert(err.message || 'Failed to extend pass');
    }
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await updateUserRole(userId, newRole);
      setActionMsg(`Updated user #${userId} role to ${newRole}`);
      loadTabData();
    } catch (err: any) {
      alert(err.message || 'Failed to change role');
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateSystemConfig(systemConfig);
      setActionMsg('Platform configuration updated successfully!');
    } catch (err: any) {
      alert(err.message || 'Failed to update config');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <span className="modal-title">
              {isSuperAdmin ? 'AcadFormat Super Administrator Console' : 'AcadFormat Administration Portal'}
            </span>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              Logged in as {currentUser.full_name} ({currentUser.role.toUpperCase()})
            </div>
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
          {actionMsg && (
            <div style={{ padding: '0.55rem 0.75rem', background: '#ECFDF5', color: '#059669', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', marginBottom: '1rem', border: '1px solid #A7F3D0' }}>
              ✓ {actionMsg}
            </div>
          )}

          {/* Tab Navigation */}
          <div className="admin-tabs">
            <button
              type="button"
              className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveTab('users')}
            >
              User Registry & Device Locks
            </button>
            <button
              type="button"
              className={`admin-tab ${activeTab === 'documents' ? 'active' : ''}`}
              onClick={() => setActiveTab('documents')}
            >
              Document Audit Logs
            </button>

            {isSuperAdmin && (
              <>
                <button
                  type="button"
                  className={`admin-tab ${activeTab === 'analytics' ? 'active' : ''}`}
                  onClick={() => setActiveTab('analytics')}
                >
                  Financial & MoMo Analytics
                </button>
                <button
                  type="button"
                  className={`admin-tab ${activeTab === 'config' ? 'active' : ''}`}
                  onClick={() => setActiveTab('config')}
                >
                  System Configuration
                </button>
              </>
            )}
          </div>

          {/* TAB 1: USERS */}
          {activeTab === 'users' && (
            <div>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Search by name, username, or email..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') loadTabData(); }}
                />
                <button
                  type="button"
                  className="btn-tool"
                  onClick={loadTabData}
                >
                  Search
                </button>
              </div>

              {loading ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: '#64748B' }}>Loading user registry...</div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Role</th>
                        <th>Device ID</th>
                        <th>Free Trial</th>
                        <th>Subscription</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => {
                        const trialActive = new Date(u.trial_expires_at) > new Date();
                        const subActive = u.subscription_expires_at && new Date(u.subscription_expires_at) > new Date();

                        return (
                          <tr key={u.id}>
                            <td>
                              <div style={{ fontWeight: 600 }}>{u.full_name}</div>
                              <div style={{ fontSize: '0.7rem', color: '#64748B' }}>@{u.username} • {u.email}</div>
                            </td>
                            <td>
                              {isSuperAdmin ? (
                                <select
                                  value={u.role}
                                  onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                  style={{ fontSize: '0.75rem', padding: '2px 4px' }}
                                >
                                  <option value="user">Student</option>
                                  <option value="admin">Admin</option>
                                  <option value="super_admin">Super Admin</option>
                                </select>
                              ) : (
                                <span className={`role-badge ${u.role}`}>{u.role}</span>
                              )}
                            </td>
                            <td style={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                              {u.device_id ? `${u.device_id.substring(0, 14)}...` : 'Unbound'}
                            </td>
                            <td>
                              <span style={{ color: trialActive ? '#059669' : '#DC2626', fontWeight: 600, fontSize: '0.75rem' }}>
                                {trialActive ? 'Active (72h)' : 'Expired'}
                              </span>
                            </td>
                            <td>
                              <span style={{ color: subActive ? '#059669' : '#64748B', fontWeight: 600, fontSize: '0.75rem' }}>
                                {subActive ? 'Active Pass' : 'None'}
                              </span>
                            </td>
                            <td>
                              <button
                                type="button"
                                className="btn-tool"
                                onClick={() => handleExtend(u.id)}
                                style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                                title="Grant 7 additional days of unlimited export"
                              >
                                +7 Days
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: DOCUMENTS */}
          {activeTab === 'documents' && (
            <div>
              {loading ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: '#64748B' }}>Loading audit logs...</div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Filename</th>
                        <th>Document Type</th>
                        <th>Faculty / School</th>
                        <th>Compliance Score</th>
                        <th>Issues Identified</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>{doc.filename}</td>
                          <td>{doc.doc_type}</td>
                          <td>{(doc.school_type || 'coltech').toUpperCase()}</td>
                          <td>
                            <strong style={{ color: doc.compliance_score >= 85 ? '#059669' : '#D97706' }}>
                              {doc.compliance_score}%
                            </strong>
                          </td>
                          <td>{doc.issues_count ?? 0} issues</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: SUPER ADMIN ANALYTICS */}
          {activeTab === 'analytics' && isSuperAdmin && (
            <div>
              {analytics ? (
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                    <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Total Revenue</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-primary)' }}>
                        {analytics.total_revenue_xaf || 0} FCFA
                      </div>
                    </div>
                    <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>MTN MoMo Revenue</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#D97706' }}>
                        {analytics.mtn_revenue_xaf || 0} FCFA
                      </div>
                    </div>
                    <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Orange Money Revenue</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#EA580C' }}>
                        {analytics.orange_revenue_xaf || 0} FCFA
                      </div>
                    </div>
                    <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Completed Transactions</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--color-success)' }}>
                        {analytics.completed_payments_count || 0}
                      </div>
                    </div>
                  </div>

                  <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: 'var(--color-primary)' }}>
                    Recent Payment Ledger
                  </h4>
                  <div style={{ overflowX: 'auto' }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Operator</th>
                          <th>Phone</th>
                          <th>Amount</th>
                          <th>Device ID</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(analytics.recent_payments || []).map((p: any, idx: number) => (
                          <tr key={idx}>
                            <td>{new Date(p.created_at).toLocaleDateString()}</td>
                            <td style={{ fontWeight: 600 }}>{p.operator.toUpperCase()}</td>
                            <td>{p.phone_number}</td>
                            <td><strong>{p.amount} FCFA</strong></td>
                            <td style={{ fontSize: '0.7rem', fontFamily: 'monospace' }}>{p.device_id}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div>Loading analytics...</div>
              )}
            </div>
          )}

          {/* TAB 4: SYSTEM CONFIG */}
          {activeTab === 'config' && isSuperAdmin && (
            <form onSubmit={handleSaveConfig} style={{ maxWidth: '480px' }}>
              <div className="form-group">
                <label className="form-label">Free Trial Duration (Hours)</label>
                <input
                  type="number"
                  className="form-control"
                  value={systemConfig.trial_duration_hours}
                  onChange={(e) => setSystemConfig({ ...systemConfig, trial_duration_hours: parseInt(e.target.value) || 72 })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Export Pass Price (FCFA)</label>
                <input
                  type="number"
                  className="form-control"
                  value={systemConfig.subscription_price_xaf}
                  onChange={(e) => setSystemConfig({ ...systemConfig, subscription_price_xaf: parseInt(e.target.value) || 250 })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Pass Validity Duration (Days)</label>
                <input
                  type="number"
                  className="form-control"
                  value={systemConfig.subscription_duration_days}
                  onChange={(e) => setSystemConfig({ ...systemConfig, subscription_duration_days: parseInt(e.target.value) || 7 })}
                />
              </div>

              <button type="submit" className="btn-submit-format">
                Save Platform Configuration
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

