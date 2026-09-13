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
}

export function clearToken() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function hasToken(): boolean {
  return (
    typeof window !== "undefined" && !!localStorage.getItem(ACCESS_KEY)
  );
}
