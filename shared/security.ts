/**
 * Settings keys that hold credentials. They must never be persisted
 * (localStorage, server file, export) nor sent to the API.
 * This build has no broker connection: no credential is ever needed.
 */
export const SECRET_SETTING_KEYS = ["mt5Password", "telegramToken"] as const;

export type SecretSettingKey = (typeof SECRET_SETTING_KEYS)[number];

export function stripSecrets<T extends object>(
  settings: T,
): Omit<T, SecretSettingKey> {
  const copy: Record<string, unknown> = { ...(settings as Record<string, unknown>) };
  for (const key of SECRET_SETTING_KEYS) delete copy[key];
  return copy as Omit<T, SecretSettingKey>;
}
