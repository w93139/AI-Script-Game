'use client';

import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { AssetOwner, AuthorizedVisual } from '@/services/playAssets';
import { createPlayImageResource, EMPTY_IMAGE } from '@/lib/playImageResource';

export const MaterialAssetContext = createContext<(AssetOwner & { visuals: AuthorizedVisual[] }) | null>(null);

/** A material can render only the matching collection/id in the authorized view. */
export function MaterialImages({ collection, materialId }: { collection?: AuthorizedVisual['collection']; materialId: string }) {
  const assets = useContext(MaterialAssetContext);
  if (!assets || !collection) return null;
  return assets.visuals.filter(v => v.collection === collection && v.material_id === materialId).map(visual =>
    <AuthorizedImage key={`${assets.scope}:${assets.kind}:${assets.id}:${visual.id}`} owner={assets} visual={visual} />);
}

export function AuthorizedImage({ owner, visual }: { owner: AssetOwner; visual: AuthorizedVisual }) {
  return <ImageCard key={`${owner.scope}:${owner.kind}:${owner.id}:${visual.id}`} owner={owner} visual={visual} />;
}

function ImageCard({ owner, visual }: { owner: AssetOwner; visual: AuthorizedVisual }) {
  const [image, setImage] = useState(EMPTY_IMAGE);
  const [zoom, setZoom] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const resource = useRef<ReturnType<typeof createPlayImageResource> | null>(null);
  const { kind, id, scope } = owner;
  useEffect(() => {
    const current = createPlayImageResource({ kind, id, scope }, visual.id, setImage);
    resource.current = current;
    let observer: IntersectionObserver | undefined;
    if (root.current && typeof IntersectionObserver !== 'undefined') {
      observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) { observer?.disconnect(); void current.load(); }
      }, { rootMargin: '120px' });
      observer.observe(root.current);
    }
    return () => { observer?.disconnect(); current.dispose(); resource.current = null; };
  }, [kind, id, scope, visual.id]);
  const picture = () => (
    // The browser displays an authenticated local blob; never send it to an image proxy.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={image.url} alt={visual.label} draggable={false} className="absolute inset-0 h-full w-full object-contain" style={{ transform: `rotate(${image.rotation}deg)` }} />
  );
  return <div ref={root} className="mt-4 min-w-0 rounded-lg border border-graphite p-3">
    <p className="text-sm text-mist">{visual.label}</p>
    {!image.url && <button type="button" disabled={image.loading || image.invalid} onClick={() => void resource.current?.load()}
      className="mt-2 min-h-11 rounded border border-smoke px-3 py-2 text-sm text-acid-lime disabled:opacity-50">
      {image.loading ? '正在读取图片…' : image.error ? '重试图片' : '查看图片'}</button>}
    {image.url && <>
      <button ref={trigger} type="button" aria-label={`放大${visual.label}`} className="relative mx-auto mt-3 block aspect-square w-full max-w-[60dvh] overflow-hidden rounded bg-obsidian focus-visible:outline focus-visible:outline-2 focus-visible:outline-acid-lime"
        onClick={() => { if (resource.current?.isCurrent()) dialog.current?.showModal(); }}>{picture()}</button>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-fog"><button type="button" className="min-h-11 rounded border border-smoke px-3 py-2 text-acid-lime" onClick={() => resource.current?.rotate()}>旋转图片</button><span>点击图片放大阅读</span></div>
      <dialog ref={dialog} aria-label={visual.label} className="fixed inset-0 m-auto h-[calc(100dvh-1.5rem)] max-h-none w-[calc(100vw-1.5rem)] max-w-none rounded-xl border border-smoke bg-carbon p-3 text-paper backdrop:bg-black/80 sm:p-5"
        onClose={() => { setZoom(false); trigger.current?.focus(); }}>
        <div className="flex h-full min-h-0 flex-col gap-3">
          <div className="flex flex-wrap items-center gap-3"><h3 className="min-w-0 flex-1 break-words text-base font-semibold">{visual.label}</h3>
            <button type="button" className="min-h-11 rounded border border-smoke px-3 text-sm" onClick={() => { if (resource.current?.isCurrent()) setZoom(value => !value); }}>{zoom ? '适应窗口' : '放大细节'}</button>
            <button type="button" className="min-h-11 rounded border border-smoke px-3 text-sm" onClick={() => resource.current?.rotate()}>旋转图片</button>
            <button type="button" autoFocus aria-label="关闭图片" className="min-h-11 rounded px-3 text-sm text-acid-lime" onClick={() => dialog.current?.close()}>关闭</button>
          </div>
          <p className="text-xs text-fog">放大后可滑动查看细节。</p>
          <div className="min-h-0 flex-1 overflow-auto overscroll-contain rounded bg-obsidian">
            <div className="relative mx-auto aspect-square" style={{ width: zoom ? '200%' : '100%', maxWidth: zoom ? undefined : '72dvh' }}>{picture()}</div>
          </div>
        </div>
      </dialog>
    </>}
    {image.error && <p role="alert" className="mt-2 text-sm text-fog">{image.error}</p>}
  </div>;
}
