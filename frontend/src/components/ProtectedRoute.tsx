import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { Loader2 } from 'lucide-react';
import { authReturnPath } from '@/lib/authReturnPath';
import { useGuestSession } from '@/hooks/useGuestSession';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  redirectTo?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAuth = true,
  redirectTo = '/auth/login'
}) => {
  const router = useRouter();
  // 未登录时先尝试访客模式（后端开启时开发期无需登录），有结论后再决定去留。
  const { isAuthenticated, isLoading, settled } = useGuestSession();

  // 还不能下结论的几种情况：认证状态未加载、路由未就绪、访客探测未出结果。
  // 直接推导而不用额外的 state，避免在 effect 里同步 setState 触发连锁渲染。
  const resolving =
    isLoading || !router.isReady || (requireAuth && !isAuthenticated && !settled);

  useEffect(() => {
    if (resolving) {
      return;
    }

    if (requireAuth && !isAuthenticated) {
      // 访客模式不可用，回到登录页并记住来路。
      router.replace({ pathname: redirectTo, query: { returnUrl: authReturnPath(router.asPath) } });
      return;
    }

    // 登录后回到原入口，缺省进入剧本中心。
    if (!requireAuth && isAuthenticated &&
        (router.pathname.startsWith('/auth/') || router.pathname === '/auth')) {
      router.replace(authReturnPath(router.query.returnUrl));
    }
  }, [resolving, isAuthenticated, requireAuth, router, redirectTo]);

  // 显示加载状态
  if (resolving) {
    return (
      <div className="min-h-screen bg-ink flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-brass mx-auto mb-4" />
          <p className="text-mist">正在验证身份...</p>
        </div>
      </div>
    );
  }

  // 如果需要认证但用户未登录，不渲染内容（等待重定向）
  if (requireAuth && !isAuthenticated) {
    return null;
  }

  // 如果用户已登录但访问认证页面，不渲染内容（等待重定向）
  if (!requireAuth && isAuthenticated &&
      (router.pathname.startsWith('/auth/') || router.pathname === '/auth')) {
    return null;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
