/**
 * Settings API client.
 *
 * Handles user preferences like LLM provider selection.
 */

import client from './client';

export interface UserSettings {
  llm_provider: 'auto' | 'groq' | 'gemini' | 'ollama';
}

export interface LLMStatus {
  active_provider: string | null;
  available_providers: string[];
  models: Record<string, string>;
  user_preference: string;
}

/** Get current user settings */
export async function getSettings(): Promise<UserSettings> {
  const { data } = await client.get('/settings/');
  return data;
}

/** Update user settings */
export async function updateSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
  const { data } = await client.put('/settings/', settings);
  return data;
}

/** Get LLM provider status (which providers are available) */
export async function getLLMStatus(): Promise<LLMStatus> {
  const { data } = await client.get('/settings/llm/status');
  return data;
}
