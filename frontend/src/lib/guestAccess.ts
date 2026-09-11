// 访客模式：后端开启 ALLOW_ANONYMOUS_ACCESS 时，受保护页面自动以访客身份进入，
// 开发期不需要真的登录。后端关闭该开关时（生产环境的启动自检会强制关闭），
// 这里会原样回到登录页，行为与以前完全一致。
//
// 是否开启由后端说了算，前端不另设开关：尝试一次访客登录，成功即进入，
// 被拒绝就记下来，本次浏览器会话内不再重复尝试，避免每开一个页面都多一次请求。

export const GUEST_PROBE_KEY = 'guest-access-unavailable';

let inFlight: Promise<boolean> | null = null;

function probeStore(): Storage | null {
  // 无痕模式或禁用存储时 sessionStorage 可能直接抛错，不能让它拖垮页面。
  try {
    return typeof window !== 'undefined' ? window.sessionStorage : null;
  } catch {
    return null;
  }
}

export function guestAccessKnownUnavailable(): boolean {
  try {
    return probeStore()?.getItem(GUEST_PROBE_KEY) === '1';
  } catch {
    return false;
  }
}

export function markGuestAccessUnavailable(): void {
  try {
    probeStore()?.setItem(GUEST_PROBE_KEY, '1');
  } catch {
    // 记不住就只是下次再多问一次，不影响正确性。
  }
}

/** 登录成功或显式登出后调用，让访客探测在下次需要时重新进行。 */
export function clearGuestAccessProbe(): void {
  try {
    probeStore()?.removeItem(GUEST_PROBE_KEY);
  } catch {
    // 同上，清不掉不影响正确性。
  }
  inFlight = null;
}

/**
 * 尝试以访客身份建立会话。
 *
 * @returns 是否已经登录成功。返回 false 表示后端没开访客模式，调用方应回到登录页。
 */
export async function ensureGuestSession(
  signInAsGuest: () => Promise<void>,
): Promise<boolean> {
  if (guestAccessKnownUnavailable()) {
    return false;
  }

  // 同一时刻只探测一次：多个受保护组件同时挂载时不应各发一次请求。
  if (!inFlight) {
    inFlight = (async () => {
      try {
        await signInAsGuest();
        return true;
      } catch {
        markGuestAccessUnavailable();
        return false;
      } finally {
        inFlight = null;
      }
    })();
  }

  return inFlight;
}
