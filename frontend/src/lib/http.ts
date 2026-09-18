import axios from "axios";
import { API_BASE_URL } from "./config";

export const http = axios.create({ baseURL: API_BASE_URL, timeout: 120_000 });

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
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (err.response?.status === 401) return '登录已失效，请重新登录后继续原局。';
    if (detail === 'FULL_PLAY_CALL_PEER_REPEATED') return '本轮已与这个角色单独对话，请先选择其他角色交流。也可以在公开提问区查看可问的问题。';
    if (err.response?.status === 409) return '游戏进度或可用操作已变化，请刷新进度后核对。';
    return typeof detail === 'string' ? detail : '请求未完成，请检查连接并核对进度。';
  }
  return err instanceof Error ? err.message : "UNKNOWN";
}
