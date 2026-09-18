import { http } from "@/lib/http";
import type { Token } from "@/types/api";

const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export async function anonymousLogin(): Promise<Token> {
  const { data } = await http.post<Token>("/api/auth/anonymous-login");
  return data;
}

export function saveToken(token: Token) {
  localStorage.setItem(ACCESS_KEY, token.access_token);
  if (token.refresh_token) {
    localStorage.setItem(REFRESH_KEY, token.refresh_token);
  }
  window.dispatchEvent(new Event('auth-token-changed'));
}

export function clearToken() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  window.dispatchEvent(new Event('auth-token-changed'));
}

export function hasToken(): boolean {
  return (
    typeof window !== "undefined" && !!localStorage.getItem(ACCESS_KEY)
  );
}

let loginInFlight: Promise<void> | null = null;

/** Reuse the current identity across home, play, records and StrictMode effects. */
export function ensureSession(): Promise<void> {
  if (hasToken()) return Promise.resolve();
  if (!loginInFlight) {
    loginInFlight = anonymousLogin().then(saveToken).finally(() => { loginInFlight = null; });
  }
  return loginInFlight;
}

export function currentToken(): string | null {
  return typeof window === 'undefined' ? null : localStorage.getItem(ACCESS_KEY);
}

export async function sessionScope(): Promise<string> {
  const token = currentToken();
  if (!token) throw new Error('请先登录。');
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token));
  return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
}
