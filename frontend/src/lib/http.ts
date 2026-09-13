import axios from "axios";
import { API_BASE_URL } from "./config";

export const http = axios.create({ baseURL: API_BASE_URL });

http.interceptors.request.use((config) => {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/** 提取后端统一的错误码（HTTPException.detail），失败时回退为消息。 */
export function errorCode(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    return detail ?? err.message;
  }
  return err instanceof Error ? err.message : "UNKNOWN";
}
