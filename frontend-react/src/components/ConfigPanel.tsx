import React from 'react';
import { AcademicData, DocumentMetadata, GroupMember } from '../types';

interface ConfigPanelProps {
  academicData: AcademicData | null;
  institution: 'uba' | 'catuc';
  schoolType: string;
  onSchoolTypeChange: (st: string) => void;
  docType: string;
  onDocTypeChange: (dt: string) => void;
  headerMode: string;
  onHeaderModeChange: (hm: string) => void;
  metadata: DocumentMetadata;
  onMetadataChange: (meta: DocumentMetadata) => void;
  onReformat: () => void;
  reformatting: boolean;
  canReformat: boolean;
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  academicData,
  institution,
  schoolType,
  onSchoolTypeChange,
  docType,
  onDocTypeChange,
  headerMode,
  onHeaderModeChange,
  metadata,
  onMetadataChange,
  onReformat,
  reformatting,
  canReformat
}) => {
  // Filter establishments based on selected institution
  const establishments = React.useMemo(() => {
    if (!academicData?.establishments) return {};
    const filtered: Record<string, any> = {};
    for (const [key, est] of Object.entries(academicData.establishments)) {
      if (est.university === institution) {
        filtered[key] = est;
      }
    }
    return filtered;
  }, [academicData, institution]);

  const currentEst = academicData?.establishments[schoolType];
  const departments = currentEst?.departments || [];
  const departmentOptions = React.useMemo(() => {
    if (!currentEst?.department_options || !metadata.department) return [];
    return currentEst.department_options[metadata.department] || [];
  }, [currentEst, metadata.department]);

  const handleFieldChange = (field: keyof DocumentMetadata, value: any) => {
    onMetadataChange({
      ...metadata,
      [field]: value
    });
  };

  const handleSupervisorChange = (index: number, val: string) => {
    const updated = [...(metadata.supervisors || [''])];
    updated[index] = val;
    handleFieldChange('supervisors', updated);
  };

  const handleRankChange = (index: number, val: string) => {
    const updated = [...(metadata.supervisor_ranks || [''])];
    updated[index] = val;
    handleFieldChange('supervisor_ranks', updated);
  };

  const addSupervisor = () => {
    handleFieldChange('supervisors', [...(metadata.supervisors || []), '']);
    handleFieldChange('supervisor_ranks', [...(metadata.supervisor_ranks || []), 'Associate Professor']);
  };

  const removeSupervisor = (index: number) => {
    if ((metadata.supervisors || []).length <= 1) return;
    const updatedSups = (metadata.supervisors || []).filter((_, i) => i !== index);
    const updatedRanks = (metadata.supervisor_ranks || []).filter((_, i) => i !== index);
    onMetadataChange({
      ...metadata,
      supervisors: updatedSups,
      supervisor_ranks: updatedRanks
    });
  };

  const handleMemberChange = (index: number, field: keyof GroupMember, val: string) => {
    const members = [...(metadata.group_members || [])];
    if (!members[index]) return;
    members[index] = { ...members[index], [field]: val };
    handleFieldChange('group_members', members);
  };

  const addGroupMember = () => {
    const members = [...(metadata.group_members || [])];
    members.push({ name: '', matricule: '', participation: '', grade: '' });
    handleFieldChange('group_members', members);
  };

  const removeGroupMember = (index: number) => {
    const members = (metadata.group_members || []).filter((_, i) => i !== index);
    handleFieldChange('group_members', members);
  };

  const isAssignment = docType === 'assignment';

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 20h9"></path>
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
          </svg>
          2. Academic Document Structure
        </span>
      </div>

      <div className="card-body">
        {/* Document Classification Row */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Establishment / Faculty</label>
            <select
              className="form-control"
              value={schoolType}
              onChange={(e) => onSchoolTypeChange(e.target.value)}
            >
              {Object.entries(establishments).map(([key, est]) => (
                <option key={key} value={key}>
                  {est.code} — {est.name_en}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Document Type</label>
            <select
              className="form-control"
              value={docType}
              onChange={(e) => onDocTypeChange(e.target.value)}
            >
              {academicData?.doc_types &&
                Object.entries(academicData.doc_types).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
            </select>
          </div>
        </div>

        {/* Department & Option Row */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Department</label>
            <select
              className="form-control"
              value={metadata.department}
              onChange={(e) => {
                const newDept = e.target.value;
                const opts = currentEst?.department_options?.[newDept] || [];
                onMetadataChange({
                  ...metadata,
                  department: newDept,
                  option: opts.length > 0 && !opts.includes(metadata.option) ? opts[0] : metadata.option
                });
              }}
            >
              {departments.map((dept: string) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Option / Specialization</label>
            {departmentOptions.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <select
                  className="form-control"
                  value={departmentOptions.includes(metadata.option) ? metadata.option : (metadata.option ? '__custom__' : '')}
                  onChange={(e) => {
                    if (e.target.value === '__custom__') {
                      handleFieldChange('option', '');
                    } else {
                      handleFieldChange('option', e.target.value);
                    }
                  }}
                >
                  <option value="">-- General / None --</option>
                  {departmentOptions.map((opt: string) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                  <option value="__custom__">Custom / Other Specialization...</option>
                </select>
                {(!departmentOptions.includes(metadata.option) || metadata.option === '') && (
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Type specialization (e.g. Information Technology and Cybersecurity)"
                    value={metadata.option || ''}
                    onChange={(e) => handleFieldChange('option', e.target.value)}
                  />
                )}
              </div>
            ) : (
              <input
                type="text"
                className="form-control"
                placeholder="Option (e.g. Information Technology)"
                value={metadata.option || ''}
                onChange={(e) => handleFieldChange('option', e.target.value)}
              />
            )}
          </div>
        </div>

        {/* Degree Code / Program */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Degree Code / Program</label>
            <select
              className="form-control"
              value={metadata.degree_code}
              onChange={(e) => handleFieldChange('degree_code', e.target.value)}
            >
              <option value="BTech">BTech (Bachelor of Technology)</option>
              <option value="HND">HND (Higher National Diploma)</option>
              <option value="BSc">BSc (Bachelor of Science)</option>
              <option value="MTech">MTech (Master of Technology)</option>
              <option value="MSc">MSc (Master of Science)</option>
              <option value="PhD">PhD (Doctor of Philosophy)</option>
              <option value="BA">BA (Bachelor of Arts)</option>
              <option value="MA">MA (Master of Arts)</option>
            </select>
          </div>
        </div>

        {/* Document Title */}
        <div className="form-group">
          <label className="form-label">Document Title</label>
          <textarea
            className="form-control"
            rows={2}
            value={metadata.title}
            onChange={(e) => handleFieldChange('title', e.target.value)}
          />
        </div>

        {/* Author & Matricule (If Not Group Assignment) */}
        {!metadata.is_group_assignment && (
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Author Full Name</label>
              <input
                type="text"
                className="form-control"
                value={metadata.author}
                onChange={(e) => handleFieldChange('author', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Registration / Matricule Number</label>
              <input
                type="text"
                className="form-control"
                value={metadata.reg_number}
                onChange={(e) => handleFieldChange('reg_number', e.target.value)}
              />
            </div>
          </div>
        )}

        {/* Group Assignment Toggle (For Assignments) */}
        {isAssignment && (
          <div style={{ marginBottom: '1rem', padding: '0.85rem', background: '#F8FAFC', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={metadata.is_group_assignment || false}
                  onChange={(e) => handleFieldChange('is_group_assignment', e.target.checked)}
                />
                Group Assignment Mode
              </label>
              {metadata.is_group_assignment && (
                <button
                  type="button"
                  className="btn-tool"
                  onClick={addGroupMember}
                  style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                >
                  + Add Member
                </button>
              )}
            </div>

            {metadata.is_group_assignment && (
              <div>
                <div className="form-row" style={{ marginBottom: '0.5rem' }}>
                  <div className="form-group">
                    <label className="form-label">Group Name / Number</label>
                    <input
                      type="text"
                      className="form-control"
                      value={metadata.group_name || ''}
                      onChange={(e) => handleFieldChange('group_name', e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Evaluation Column</label>
                    <input
                      type="text"
                      className="form-control"
                      value={metadata.grading_column_title || 'Score / 20'}
                      onChange={(e) => handleFieldChange('grading_column_title', e.target.value)}
                    />
                  </div>
                </div>

                {/* Member Roster List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '180px', overflowY: 'auto' }}>
                  {(metadata.group_members || []).map((m, idx) => (
                    <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr auto', gap: '0.4rem', alignItems: 'center' }}>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Member Name"
                        value={m.name}
                        onChange={(e) => handleMemberChange(idx, 'name', e.target.value)}
                      />
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Matricule"
                        value={m.matricule}
                        onChange={(e) => handleMemberChange(idx, 'matricule', e.target.value)}
                      />
                      <button
                        type="button"
                        onClick={() => removeGroupMember(idx)}
                        style={{ background: 'none', border: 'none', color: '#DC2626', cursor: 'pointer', padding: '4px' }}
                        title="Remove member"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Supervision & Defense Committee Section */}
        {!isAssignment && (
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <label className="form-label" style={{ marginBottom: 0 }}>Supervisors & Academic Ranks</label>
              <button
                type="button"
                className="btn-tool"
                onClick={addSupervisor}
                style={{ fontSize: '0.725rem', padding: '0.15rem 0.45rem' }}
              >
                + Add Co-Supervisor
              </button>
            </div>

            {(metadata.supervisors || ['']).map((sup, idx) => (
              <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr auto', gap: '0.4rem', marginBottom: '0.4rem', alignItems: 'center' }}>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Supervisor Full Name"
                  value={sup}
                  onChange={(e) => handleSupervisorChange(idx, e.target.value)}
                />
                <select
                  className="form-control"
                  value={(metadata.supervisor_ranks || [])[idx] || 'Associate Professor'}
                  onChange={(e) => handleRankChange(idx, e.target.value)}
                >
                  <option value="Professor">Professor (Pr.)</option>
                  <option value="Associate Professor">Associate Professor</option>
                  <option value="Senior Lecturer">Senior Lecturer (Dr.)</option>
                  <option value="Lecturer">Lecturer (Dr. / Mr.)</option>
                  <option value="Assistant Lecturer">Assistant Lecturer</option>
                  <option value="Field Supervisor">Field / Industrial Supervisor</option>
                </select>
                {(metadata.supervisors || []).length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeSupervisor(idx)}
                    style={{ background: 'none', border: 'none', color: '#DC2626', cursor: 'pointer', padding: '4px' }}
                    title="Remove supervisor"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Month & Year */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Submission Month</label>
            <select
              className="form-control"
              value={metadata.submission_month}
              onChange={(e) => handleFieldChange('submission_month', e.target.value)}
            >
              {['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER'].map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Submission Year</label>
            <input
              type="text"
              className="form-control"
              value={metadata.submission_year}
              onChange={(e) => handleFieldChange('submission_year', e.target.value)}
            />
          </div>
        </div>

        {/* Action Button: Format Document */}
        <button
          type="button"
          className="btn-submit-format"
          disabled={!canReformat || reformatting}
          onClick={onReformat}
        >
          {reformatting ? (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ animation: 'spin 1s linear infinite' }}>
                <line x1="12" y1="2" x2="12" y2="6"></line>
                <line x1="12" y1="18" x2="12" y2="22"></line>
                <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                <line x1="2" y1="12" x2="6" y2="12"></line>
                <line x1="18" y1="12" x2="22" y2="12"></line>
                <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
              </svg>
              Enforcing Official Senate Standard...
            </>
          ) : (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              Standardize & Generate Previews
            </>
          )}
        </button>
      </div>
    </div>
  );
};

