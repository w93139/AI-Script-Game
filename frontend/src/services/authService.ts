// 用户认证API服务
import {
  UserLogin as LoginData,
  PasswordChange,
  Token,
  UserResponse as User,
  UserRegister,
  UserUpdate
} from '@/client';
import { PhoneLogin, SmsCodeResponse } from '@/types/auth';
import { config } from '@/stores/configStore';
import { authReturnPath } from '@/lib/authReturnPath';

class AuthService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = config.api.baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    allowRefresh: boolean = true,
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const defaultHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      // 401状态码拦截器
      if (response.status === 401) {
        // 访问令牌有效期是小时级，过期属于正常情况。先用续期凭条静默换一张新的
        // 再重试本次请求；只有换发也失败，才说明登录真的结束了。
        if (allowRefresh && this.getRefreshToken()) {
          const renewed = await this.renewSession();
          if (renewed) {
            return this.request<T>(endpoint, options, false);
          }
        }

        const returnPath = typeof window !== 'undefined'
          && !/^\/auth(?:\/|$)/i.test(window.location.pathname)
          ? authReturnPath(window.location.pathname + window.location.search + window.location.hash)
          : null;
        this.removeToken();
        // Preserve the current game when an existing login expires.
        if (returnPath !== null) {
          // 强制跳转登录页：登录已过期，替换当前历史记录而不是新增一条，
          // 这样用户按后退不会回到已失效的页面。
          window.location.replace('/auth/login?returnUrl=' + encodeURIComponent(returnPath));
        }
      }

      const errorData = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  /**
   * 用续期凭条换一张新的访问令牌。
   *
   * 多个请求同时收到 401 时只会真正换发一次：后到的请求等待同一个换发结果，
   * 否则并发刷新会互相作废对方刚拿到的凭条（服务端的凭条是一次性的）。
   */
  private async renewSession(): Promise<boolean> {
    if (this.renewal) {
      return this.renewal;
    }

    this.renewal = (async (): Promise<boolean> => {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        return false;
      }
      try {
        const response = await fetch(`${this.baseUrl}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) {
          return false;
        }
        this.setSession(await response.json());
        return true;
      } catch {
        return false;
      } finally {
        this.renewal = null;
      }
    })();

    return this.renewal;
  }

  private renewal: Promise<boolean> | null = null;

  // Token 管理
  getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('access_token');
    }
    return null;
  }

  getRefreshToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('refresh_token');
    }
    return null;
  }

  setToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
      window.dispatchEvent(new Event('auth-token-changed'));
    }
  }

  /** 保存一次登录或换发返回的整组令牌。 */
  setSession(session: { access_token: string; refresh_token?: string | null }): void {
    if (typeof window === 'undefined') {
      return;
    }
    localStorage.setItem('access_token', session.access_token);
    if (session.refresh_token) {
      localStorage.setItem('refresh_token', session.refresh_token);
    }
    window.dispatchEvent(new Event('auth-token-changed'));
  }

  removeToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.dispatchEvent(new Event('auth-token-changed'));
    }
  }

  /**
   * 用户注册
   * @param registerData 注册数据
   * @returns 注册响应
   */
  async register(registerData: UserRegister): Promise<User> {
    try {
      return await this.request<User>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(registerData),
      });
    } catch (error) {
      console.error('注册失败:', error);
      throw error;
    }
  }

  /**
   * 用户登录
   * @param loginData 登录数据
   * @returns 登录响应
   */
  async login(loginData: LoginData): Promise<Token> {
    try {
      return await this.request<Token>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginData),
      });
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  }

  async sendSmsCode(phone: string): Promise<SmsCodeResponse> {
    return this.request<SmsCodeResponse>('/api/auth/sms-code', {
      method: 'POST',
      body: JSON.stringify({ phone }),
    });
  }

  async phoneLogin(data: PhoneLogin): Promise<Token> {
    return this.request<Token>('/api/auth/phone-login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * 匿名登录（需后端启用 ALLOW_ANONYMOUS_ACCESS）
   * @returns 登录响应
   */
  async anonymousLogin(): Promise<Token> {
    try {
      return await this.request<Token>('/api/auth/anonymous-login', {
        method: 'POST',
      });
    } catch (error) {
      console.error('匿名登录失败:', error);
      throw error;
    }
  }

  // 用户登出
  async logout(): Promise<void> {
    try {
      await this.request('/api/auth/logout', {
        method: 'POST',
      });
    } finally {
      // 无论请求是否成功，都清除本地token
      this.removeToken();
    }
  }

  // 获取当前用户信息
  async getCurrentUser(): Promise<User> {
    return this.request<User>('/api/auth/me');
  }

  // 更新用户资料
  async updateProfile(userData: UserUpdate): Promise<User> {
    return this.request<User>('/api/auth/me', {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
  }

  // 修改密码
  async changePassword(passwordData: PasswordChange): Promise<{ message: string }> {
    return this.request<{ message: string }>('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(passwordData),
    });
  }

  // 检查是否已登录
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  // 验证token是否有效
  async validateToken(): Promise<boolean> {
    try {
      await this.getCurrentUser();
      return true;
    } catch {
      this.removeToken();
      return false;
    }
  }
}

export const authService = new AuthService();
export default authService;
