import { currentToken } from '@/services/auth';

export function watchPackagePlayAuth(onChange: () => void) {
  const token = currentToken();
  let observedToken = token;
  let valid = true;
  const check = () => {
    const current = currentToken();
    // A recording binding never revives, even if the account changes back.
    if (observedToken !== current) { observedToken = current; valid = false; onChange(); }
    return valid;
  };
  const events = ['storage', 'auth-token-changed', 'focus'];
  if (typeof window !== 'undefined') events.forEach(name => window.addEventListener(name, check));
  return { isCurrent: check, dispose: () => {
    if (typeof window !== 'undefined') events.forEach(name => window.removeEventListener(name, check));
  } };
}
