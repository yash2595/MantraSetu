/**
 * Centralized Form Security Utility
 *
 * Provides a single, guaranteed sanitization function to strip sensitive keys
 * (passwords, confirm passwords, binaries, ID numbers) before persisting
 * form data to browser localStorage/sessionStorage.
 */

const SENSITIVE_KEYS = new Set([
  'password',
  'confirm_password',
  'confirmPassword',
  'panditPassword',
  'panditConfirmPassword',
  'confirm',
  'pass',
  'aadhaar',
  'aadhaarFile',
  'certFile',
  'documents'
]);

export function getPersistableData<T extends Record<string, any>>(data: T): Partial<T> {
  if (!data || typeof data !== 'object') return {};

  const sanitized: Record<string, any> = {};
  for (const [key, value] of Object.entries(data)) {
    const keyLower = key.toLowerCase();
    if (!SENSITIVE_KEYS.has(key) && !keyLower.includes('password') && !keyLower.includes('confirm')) {
      sanitized[key] = value;
    }
  }
  return sanitized as Partial<T>;
}
