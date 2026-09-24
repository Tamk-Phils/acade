import React, { useState } from 'react';
import { processMoMoPayment } from '../services/api';
import { Eligibility } from '../types';

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
  eligibility: Eligibility | null;
  onPaymentSuccess: () => void;
}

export const PaywallModal: React.FC<PaywallModalProps> = ({
  isOpen,
  onClose,
  eligibility,
  onPaymentSuccess
}) => {
  const [operator, setOperator] = useState<'mtn_momo' | 'orange_money'>('mtn_momo');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [processing, setProcessing] = useState(false);
  const [ussdStep, setUssdStep] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const isDeviceMismatch = eligibility?.reason === 'device_mismatch';

  const handlePay = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanNum = phoneNumber.replace(/\s+/g, '');
    if (cleanNum.length < 9) {
      setError('Please provide a valid 9-digit Cameroonian mobile money phone number (e.g. 677... or 699...).');
      return;
    }

    setProcessing(true);
    setUssdStep(true);

    try {
      // Simulate real-time mobile push verification
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await processMoMoPayment({
        operator,
        phone_number: cleanNum,
        amount: 250
      });
      setUssdStep(false);
      onPaymentSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Payment transaction failed or timed out.');
      setUssdStep(false);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">
            {isDeviceMismatch ? 'Device Verification & Export Pass' : 'Academic Export Pass (250 FCFA)'}
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: '#64748B' }}
          >
            ✕
          </button>
        </div>

        <div className="modal-body">
          {/* Reason Alert */}
          <div style={{ padding: '0.75rem 1rem', background: '#FFFBEB', border: '1px solid #FCD34D', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', fontSize: '0.825rem', color: '#92400E' }}>
            {isDeviceMismatch ? (
              <div>
                <strong>New Hardware Device Detected:</strong> Under our anti-sharing policy, your account is bound to your primary device. Unlock official manuscript export on this device with a standard 1-week pass.
              </div>
            ) : (
              <div>
                <strong>72-Hour Free Trial Concluded:</strong> Your free trial has elapsed. Continue enjoying unlimited DOCX & PDF exports conforming to Senate standards.
              </div>
            )}
          </div>

          {/* Pricing Highlight */}
          <div className="momo-pricing-banner">
            <div className="momo-price">250 FCFA</div>
            <div className="momo-duration">7 Days Full Unlimited Document Export Access</div>
          </div>

          {error && (
            <div style={{ padding: '0.65rem 0.85rem', background: '#FEF2F2', border: '1px solid #FCA5A5', color: '#DC2626', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', marginBottom: '1rem' }}>
              {error}
            </div>
          )}

          {ussdStep ? (
            <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem', animation: 'spin 1.5s linear infinite' }}>
                ⏳
              </div>
              <h4 style={{ color: 'var(--color-primary)', fontWeight: 700 }}>
                USSD Prompt Sent to {phoneNumber}
              </h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                Please enter your PIN on your mobile device to authorize payment of 250 FCFA to AcadFormat.
              </p>
            </div>
          ) : (
            <form onSubmit={handlePay}>
              {/* Operator Tabs */}
              <div className="operator-tabs">
                <div
                  className={`operator-tab mtn ${operator === 'mtn_momo' ? 'active' : ''}`}
                  onClick={() => setOperator('mtn_momo')}
                >
                  MTN Mobile Money
                </div>
                <div
                  className={`operator-tab orange ${operator === 'orange_money' ? 'active' : ''}`}
                  onClick={() => setOperator('orange_money')}
                >
                  Orange Money
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">
                  {operator === 'mtn_momo' ? 'MTN Phone Number' : 'Orange Phone Number'}
                </label>
                <input
                  type="tel"
                  className="form-control"
                  placeholder="e.g. 677 12 34 56"
                  required
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                />
              </div>

              <div style={{ fontSize: '0.725rem', color: 'var(--color-text-muted)', marginBottom: '1.25rem' }}>
                🔒 Secure Instant USSD Gateway. Instant receipt generated upon authorization.
              </div>

              <button
                type="submit"
                className="btn-submit-format"
                disabled={processing}
                style={{ background: operator === 'mtn_momo' ? '#D97706' : '#EA580C', borderColor: 'transparent' }}
              >
                {processing ? 'Connecting Gateway...' : `Authorize 250 FCFA with ${operator === 'mtn_momo' ? 'MTN MoMo' : 'Orange Money'}`}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

