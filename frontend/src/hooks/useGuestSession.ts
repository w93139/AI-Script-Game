import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { ensureGuestSession, guestAccessKnownUnavailable } from '@/lib/guestAccess';

/**
 * 未登录时尝试以访客身份进入。
 *
 * 后端开启 ALLOW_ANONYMOUS_ACCESS 时（开发期免登录），这里会静默建立访客会话；
 * 后端关闭时什么也不会发生，调用方按原有的未登录逻辑处理即可。
 *
 * 路由守卫和游戏首页都需要这段逻辑，抽出来避免三处各写一遍而逐渐走样。
 *
 * @returns settled —— 是否已经有结论。false 表示还在探测中，此时不应该显示
 *   "请登录"，否则访客模式开着也会先闪一下登录提示。
 */
export function useGuestSession(): {
  isAuthenticated: boolean;
  isLoading: boolean;
  settled: boolean;
} {
  const { isAuthenticated, isLoading, anonymousLogin } = useAuthStore();
  // 已知访客模式不可用时无需再等待，直接按未登录处理。
  const [settled, setSettled] = useState(() => guestAccessKnownUnavailable());

  useEffect(() => {
    if (isLoading || isAuthenticated) {
      return;
    }

    let cancelled = false;

    void (async () => {
      await ensureGuestSession(anonymousLogin);
      if (!cancelled) {
        setSettled(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isLoading, anonymousLogin]);

  return { isAuthenticated, isLoading, settled };
}

export default useGuestSession;
