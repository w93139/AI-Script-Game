import { currentToken } from '@/services/auth';
import { readPlayImage, type AssetOwner } from '@/services/playAssets';
import { playImageRotation } from '@/lib/playImageOrientation';

export type ImageState = { url: string; loading: boolean; invalid: boolean; error: string; rotation: number };
export const EMPTY_IMAGE: ImageState = { url: '', loading: false, invalid: false, error: '', rotation: 0 };

/** Own the request and blob lifetime. No image bytes or URLs are persisted. */
export function createPlayImageResource(owner: AssetOwner, visualId: string, notify: (state: ImageState) => void) {
  const token = currentToken();
  let disposed = false;
  let generation = 0;
  let controller: AbortController | undefined;
  let state = { ...EMPTY_IMAGE };
  const publish = (changes: Partial<ImageState>) => { state = { ...state, ...changes }; if (!disposed) notify(state); };
  const clear = () => {
    generation++;
    controller?.abort(); controller = undefined;
    if (state.url) URL.revokeObjectURL(state.url);
    state = { ...state, url: '', loading: false };
  };
  const isCurrent = () => {
    if (disposed || state.invalid) return false;
    if (!token || currentToken() !== token) {
      clear();
      publish({ invalid: true, error: '登录身份已变化，请重新打开游戏。' });
      return false;
    }
    return true;
  };
  const checkIdentity = () => { isCurrent(); };
  window.addEventListener('storage', checkIdentity);
  window.addEventListener('focus', checkIdentity);
  return {
    isCurrent,
    async load() {
      if (!isCurrent() || controller || state.url) return;
      const attempt = generation;
      const request = new AbortController(); controller = request;
      publish({ loading: true, error: '' });
      try {
        const blob = await readPlayImage(owner, visualId, request.signal);
        if (!isCurrent() || request.signal.aborted || attempt !== generation) return;
        const rotation = await playImageRotation(blob);
        if (!isCurrent() || request.signal.aborted || attempt !== generation) return;
        publish({ url: URL.createObjectURL(blob), rotation, loading: false });
      } catch (error) {
        if (isCurrent() && !request.signal.aborted && attempt === generation) {
          publish({ error: error instanceof Error ? error.message : '图片暂时读取失败，请重试。' });
        }
      } finally {
        if (!disposed && attempt === generation) { controller = undefined; publish({ loading: false }); }
      }
    },
    rotate() { if (isCurrent()) publish({ rotation: (state.rotation + 90) % 360 }); },
    dispose() {
      disposed = true;
      window.removeEventListener('storage', checkIdentity);
      window.removeEventListener('focus', checkIdentity);
      clear();
    },
  };
}
