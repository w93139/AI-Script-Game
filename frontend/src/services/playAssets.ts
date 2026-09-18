import { currentToken, sessionScope } from '@/services/auth';
import { API_BASE_URL } from '@/lib/config';

export type AssetOwner = { kind: 'opening' | 'play'; id: string; scope: string };
export type AuthorizedVisual = { id: string; collection: 'knowledge' | 'evidence' | 'memory'; material_id: string; label: string };

/** Fetch a frozen, authorized asset directly; never use a public image proxy. */
export async function readPlayImage(owner: AssetOwner, visualId: string, signal?: AbortSignal): Promise<Blob> {
  const token = currentToken();
  const assertCurrent = () => {
    if (!token || token !== currentToken()) throw new Error('登录身份已变化，请重新打开游戏。');
    if (signal?.aborted) throw new Error('图片读取已取消。');
  };
  assertCurrent();
  const scope = await sessionScope();
  assertCurrent();
  if (scope !== owner.scope) throw new Error('登录身份已变化，请重新打开游戏。');
  const collection = owner.kind === 'opening' ? 'package-sessions' : 'package-plays';
  const url = `${API_BASE_URL.replace(/\/$/, '')}/api/fusion/${collection}/${encodeURIComponent(owner.id)}/images/${encodeURIComponent(visualId)}`;
  const response = await fetch(url, { method: 'GET', signal, cache: 'no-store', credentials: 'omit', redirect: 'error',
    headers: { Authorization: `Bearer ${token}` } });
  assertCurrent();
  if (!response.ok) throw new Error(response.status === 401 ? '登录已失效，请重新登录后查看图片。'
    : response.status === 403 || response.status === 404 ? '当前资料的图片不可读取，请刷新进度。' : '图片暂时读取失败，请重试。');
  const media = response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase();
  if (!media || !['image/png', 'image/jpeg'].includes(media)) throw new Error('未收到有效图片，请刷新后重试。');
  const blob = await response.blob();
  assertCurrent();
  if (!blob.size) throw new Error('未收到完整图片，请重试。');
  return blob;
}
