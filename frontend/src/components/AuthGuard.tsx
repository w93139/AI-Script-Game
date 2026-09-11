import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '@/stores/authStore';
import { Loader2 } from 'lucide-react';
import { authReturnPath } from '@/lib/authReturnPath';
import { ensureGuestSession, guestAccessKnownUnavailable } from '@/lib/guestAccess';

interface AuthGuardProps {
  children: React.ReactNode;
  redirectTo?: string;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children, redirectTo = '/auth/login' }) => {
  const router = useRouter();
  const { isAuthenticated, isLoading, anonymousLogin } = useAuthStore();
  // 访客模式开着时不该先闪一下登录页，所以在探测出结果之前一律显示加载态。
  const [guestChecked, setGuestChecked] = useState(() => guestAccessKnownUnavailable());

  useEffect(() => {
    if (!router.isReady || isLoading || isAuthenticated) {
      return;
    }

    let cancelled = false;

    void (async () => {
      // 后端开启访客模式时自动以访客身份进入，开发期不必真的登录；
      // 没开启时按原有行为回到登录页，并记住来路以便登录后返回。
      const signedIn = await ensureGuestSession(anonymousLogin);
      if (cancelled) {
        return;
      }
      setGuestChecked(true);
      if (!signedIn) {
        router.replace({
          pathname: redirectTo,
          query: { returnUrl: authReturnPath(router.asPath) },
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isLoading, router, redirectTo, anonymousLogin]);

  if (isLoading || (!isAuthenticated && !guestChecked)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ink">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-brass" />
          <p className="text-mist">正在验证身份...</p>
        </div>
      </div>
    );
  }

  // 未认证且访客模式不可用时不渲染内容（正在跳转登录页）
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
};

export default AuthGuard;
