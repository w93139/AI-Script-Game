import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { Loader2 } from 'lucide-react';
import { authReturnPath } from '@/lib/authReturnPath';
import { useGuestSession } from '@/hooks/useGuestSession';

interface AuthGuardProps {
  children: React.ReactNode;
  redirectTo?: string;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children, redirectTo = '/auth/login' }) => {
  const router = useRouter();
  // 未登录时先尝试访客模式（后端开启时开发期无需登录），有结论后再决定去留。
  const { isAuthenticated, isLoading, settled } = useGuestSession();

  useEffect(() => {
    if (!router.isReady || isLoading || isAuthenticated || !settled) {
      return;
    }
    // 访客模式不可用，回到登录页并记住来路，登录后能回到原来的位置。
    router.replace({
      pathname: redirectTo,
      query: { returnUrl: authReturnPath(router.asPath) },
    });
  }, [isAuthenticated, isLoading, settled, router, redirectTo]);

  // 探测期间保持加载态，避免访客模式开着也先闪一下登录页。
  if (isLoading || (!isAuthenticated && !settled)) {
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
