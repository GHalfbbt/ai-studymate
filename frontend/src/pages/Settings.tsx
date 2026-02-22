/**
 * Settings page — User preferences including LLM provider selection.
 *
 * Allows users to choose their preferred AI provider:
 * - Auto (fallback mode: Groq → Gemini → Ollama)
 * - Groq (fast cloud, free tier)
 * - Gemini (Google, free tier)
 * - Ollama (local, unlimited)
 */

import { useState, useEffect } from 'react';
import {
  getSettings,
  updateSettings,
  getLLMStatus,
  type UserSettings,
  type LLMStatus,
} from '../api/settings';

type Provider = 'auto' | 'groq' | 'gemini' | 'ollama';

const PROVIDERS: {
  value: Provider;
  label: string;
  icon: string;
  description: string;
  badge?: string;
}[] = [
  {
    value: 'auto',
    label: 'Auto (Fallback)',
    icon: '🔄',
    description: 'Tries Groq first, then Gemini, then Ollama. Best reliability.',
    badge: 'Recommended',
  },
  {
    value: 'groq',
    label: 'Groq',
    icon: '⚡',
    description: 'Fast cloud inference. Free tier: ~100k tokens/day.',
  },
  {
    value: 'gemini',
    label: 'Google Gemini',
    icon: '💎',
    description: 'Google AI free tier. Generous limits.',
  },
  {
    value: 'ollama',
    label: 'Ollama (Local)',
    icon: '🏠',
    description: 'Runs on your machine. Unlimited, but requires local setup.',
  },
];

export default function Settings() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [s, status] = await Promise.all([getSettings(), getLLMStatus()]);
      setSettings(s);
      setLlmStatus(status);
    } catch {
      setError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  }

  async function handleProviderChange(provider: Provider) {
    if (!settings) return;
    setSaving(true);
    setSaved(false);
    setError('');
    try {
      const updated = await updateSettings({ llm_provider: provider });
      setSettings(updated);
      // Refresh LLM status to show new active provider
      const status = await getLLMStatus();
      setLlmStatus(status);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <span style={{ fontSize: '2rem' }}>⏳</span>
        <p style={{ opacity: 0.6, marginTop: '0.5rem' }}>Loading settings...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem', maxWidth: 700, margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>⚙️ Settings</h1>
      <p style={{ opacity: 0.6, marginBottom: '2rem' }}>Configure your AI study assistant preferences.</p>

      {error && (
        <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.15)', borderRadius: 8, marginBottom: '1rem', color: '#ef4444' }}>
          {error}
        </div>
      )}

      {saved && (
        <div style={{ padding: '0.75rem', background: 'rgba(34,197,94,0.15)', borderRadius: 8, marginBottom: '1rem', color: '#22c55e' }}>
          ✅ Settings saved successfully!
        </div>
      )}

      {/* LLM Provider Selection */}
      <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.15rem', fontWeight: 600, marginBottom: '0.25rem' }}>🤖 LLM Provider</h2>
        <p style={{ fontSize: '0.85rem', opacity: 0.6, marginBottom: '1.25rem' }}>
          Choose which AI model powers your exams, flashcards, and chat.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {PROVIDERS.map((p) => {
            const isSelected = settings?.llm_provider === p.value;
            const isAvailable = p.value === 'auto' || llmStatus?.available_providers?.includes(p.value);
            const activeModel = llmStatus?.models?.[p.value];

            return (
              <button
                key={p.value}
                onClick={() => handleProviderChange(p.value)}
                disabled={saving || (!isAvailable && p.value !== 'auto')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                  padding: '1rem 1.25rem',
                  borderRadius: 12,
                  border: isSelected
                    ? '2px solid #6366f1'
                    : '2px solid rgba(255,255,255,0.1)',
                  background: isSelected
                    ? 'rgba(99,102,241,0.15)'
                    : 'rgba(255,255,255,0.03)',
                  color: 'inherit',
                  cursor: isAvailable || p.value === 'auto' ? 'pointer' : 'not-allowed',
                  opacity: isAvailable || p.value === 'auto' ? 1 : 0.4,
                  textAlign: 'left',
                  transition: 'all 0.15s',
                  width: '100%',
                }}
              >
                {/* Radio indicator */}
                <div style={{
                  width: 22,
                  height: 22,
                  borderRadius: '50%',
                  border: isSelected ? '2px solid #6366f1' : '2px solid rgba(255,255,255,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  {isSelected && (
                    <div style={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      background: '#6366f1',
                    }} />
                  )}
                </div>

                {/* Icon */}
                <span style={{ fontSize: '1.5rem', flexShrink: 0 }}>{p.icon}</span>

                {/* Text */}
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 600 }}>{p.label}</span>
                    {p.badge && (
                      <span style={{
                        fontSize: '0.65rem',
                        padding: '0.1rem 0.4rem',
                        borderRadius: 6,
                        background: 'rgba(99,102,241,0.2)',
                        color: '#818cf8',
                        fontWeight: 700,
                      }}>
                        {p.badge}
                      </span>
                    )}
                    {!isAvailable && p.value !== 'auto' && (
                      <span style={{
                        fontSize: '0.65rem',
                        padding: '0.1rem 0.4rem',
                        borderRadius: 6,
                        background: 'rgba(239,68,68,0.15)',
                        color: '#ef4444',
                        fontWeight: 600,
                      }}>
                        Not configured
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: '0.8rem', opacity: 0.6, marginTop: '0.15rem' }}>
                    {p.description}
                  </p>
                  {activeModel && isAvailable && (
                    <p style={{ fontSize: '0.75rem', opacity: 0.4, marginTop: '0.1rem' }}>
                      Model: {activeModel}
                    </p>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* LLM Status Panel */}
      {llmStatus && (
        <div className="card" style={{ padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>📊 Provider Status</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
            <div>
              <span style={{ fontSize: '0.8rem', opacity: 0.5, display: 'block' }}>Active Provider</span>
              <span style={{ fontWeight: 600 }}>
                {llmStatus.active_provider
                  ? `${PROVIDERS.find(p => p.value === llmStatus.active_provider)?.icon || '🤖'} ${llmStatus.active_provider}`
                  : '❌ None'}
              </span>
            </div>
            <div>
              <span style={{ fontSize: '0.8rem', opacity: 0.5, display: 'block' }}>Your Preference</span>
              <span style={{ fontWeight: 600 }}>
                {PROVIDERS.find(p => p.value === llmStatus.user_preference)?.icon || '🔄'}{' '}
                {llmStatus.user_preference}
              </span>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <span style={{ fontSize: '0.8rem', opacity: 0.5, display: 'block' }}>Available Providers</span>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem', flexWrap: 'wrap' }}>
                {llmStatus.available_providers.length > 0 ? (
                  llmStatus.available_providers.map((p) => (
                    <span
                      key={p}
                      style={{
                        fontSize: '0.8rem',
                        padding: '0.2rem 0.6rem',
                        borderRadius: 8,
                        background: 'rgba(34,197,94,0.15)',
                        color: '#22c55e',
                      }}
                    >
                      ✓ {p} ({llmStatus.models[p]})
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: '0.8rem', color: '#ef4444' }}>
                    No providers available. Check your API keys in .env
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
