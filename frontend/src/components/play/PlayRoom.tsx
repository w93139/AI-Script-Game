'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { usePlaySessionStore } from '@/stores/playSessionStore';
import { currentToken } from '@/services/auth';
import { phaseKind, publicEntries, characterName, actionPayload, pendingRequests } from '@/lib/playView';
import { NarrativeStream } from './NarrativeStream';
import { ArchiveDrawer } from './ArchiveDrawer';
import { Materials, Investigation, Finale, Exchange, Ending, buttonClass, primaryClass, inputClass } from './GamePanels';
import { MaterialAssetContext } from './AuthorizedImage';
import { PlayText } from './PlayText';
import type { AssetOwner } from '@/services/playAssets';

export function PlayRoom() {
  const state = usePlaySessionStore();
  const { mode, play, opening, releases, error, busy, unresolved, scope, bootstrap, refresh, send, invalidate } = state;
  const search = useSearchParams();
  const playId = search.get('play_id'); const openingId = search.get('opening_session_id');
  const [releaseId, setReleaseId] = useState('');
  const [characterId, setCharacterId] = useState('');
  const [archive, setArchive] = useState(false);
  const archiveButton = useRef<HTMLButtonElement>(null);
  const [review, setReview] = useState('');
  useEffect(() => { void bootstrap({ playId: playId ?? undefined, openingSessionId: openingId ?? undefined }); }, [bootstrap, playId, openingId]);
  useEffect(() => {
    // bootstrap above may already have cleared a previous route's snapshot.
    // Never let that stale render redirect a new game back to the previous one.
    if (usePlaySessionStore.getState() !== state) return;
    if (mode === 'live' && play && playId !== play.play_id) {
      window.history.replaceState(null, '', `/play?play_id=${encodeURIComponent(play.play_id)}`);
    } else if (mode === 'opening' && opening && openingId !== opening.session_id) {
      window.history.replaceState(null, '', `/play?opening_session_id=${encodeURIComponent(opening.session_id)}`);
    }
  }, [state, mode, play, opening, playId, openingId]);
  useEffect(() => {
    if (mode === 'connecting') return;
    const token = currentToken();
    const check = () => { if (currentToken() !== token) invalidate(); };
    const events = ['storage', 'auth-token-changed', 'focus'];
    events.forEach(name => window.addEventListener(name, check));
    return () => { events.forEach(name => window.removeEventListener(name, check)); };
  }, [mode, invalidate]);
  useEffect(() => {
    if (!archive) return;
    const close = (e: KeyboardEvent) => { if (e.key === 'Escape') { setArchive(false); archiveButton.current?.focus(); } };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [archive]);
  const locked = busy || !!unresolved || !!play?.pending_ai;
  const chosenRelease = releases.find(r => String(r.id) === releaseId);
  const kind = play ? phaseKind(play) : null;
  const phase = play?.round_workspace?.phases.find(p => p.phase_id === review);
  const entries = play ? publicEntries(play) : [];
  const reviewedEntries = phase ? entries.filter(e => phase.statement_ids.includes(e.id)) : [];
  const assetOwner: AssetOwner | null = play ? { kind: 'play', id: play.play_id, scope }
    : opening ? { kind: 'opening', id: opening.session_id, scope } : null;
  const assets = assetOwner ? { ...assetOwner, visuals: play ? play.visuals ?? [] : opening?.visuals ?? [] } : null;
  return <MaterialAssetContext.Provider value={assets}><div className="flex min-h-screen flex-col">
    <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-graphite bg-void px-4 py-3">
      <Link href="/" className="min-h-11 py-3 text-sm text-mist">← 返回首页</Link>
      <div className="min-w-0 flex-1 text-center"><h1 className="break-words text-base text-paper">{play?.script.title ?? opening?.script.title ?? '开始新游戏'}</h1>
        {play && <p className="mt-1 text-xs text-fog">{characterName(play, play.selected_character_id)} · {play.settled ? '已结束' : play.current_phase.title}</p>}</div>
      {play && <><button className={buttonClass} disabled={busy} onClick={() => void refresh()}>刷新进度</button>
        <button ref={archiveButton} className={buttonClass} aria-expanded={archive} onClick={() => setArchive(!archive)}>档案</button>
        {!play.settled && kind !== 'FINALE' && <a className={primaryClass} href="#phase-progress"
          onClick={e => { e.preventDefault(); setReview(''); requestAnimationFrame(() => document.getElementById('phase-progress')?.scrollIntoView({ block: 'start' })); }}>下一阶段 ↓</a>}</>}
    </header>
    {error && <div role="alert" className="mx-auto my-3 w-full max-w-4xl rounded border border-coral-red px-4 py-3 text-sm">{error}</div>}
    {unresolved && <div role="status" className="mx-auto my-3 max-w-4xl space-y-2 border border-smoke p-4 text-sm">
      <p>上次提交尚未确认。先核对原请求，核对期间不能发起新操作。</p>
      <button className={buttonClass} disabled={busy} onClick={() => void state.checkRequest()}>核对原请求</button>
    </div>}
    <div className="flex min-w-0 flex-1">
      <main className="min-w-0 flex-1 px-4 py-6 md:px-8"><div className="mx-auto max-w-3xl space-y-7">
        {mode === 'connecting' && <p role="status">正在读取游戏…</p>}
        {mode === 'error' && <><p>暂时无法打开游戏，已保留原有进度。</p><button className={buttonClass} onClick={() => void bootstrap({ playId: playId ?? undefined, openingSessionId: openingId ?? undefined })}>重新读取</button></>}
        {mode === 'selecting' && <section className="space-y-5"><h2 className="text-xl text-paper">选择故事与角色</h2>
          {!releases.length ? <p className="text-fog">当前没有已发布的可玩剧本。请先完成内容准备，再回来开始游戏。</p> : <>
            <label className="block space-y-2"><span>故事</span><select className={inputClass} disabled={busy} value={releaseId} onChange={e => { setReleaseId(e.target.value); setCharacterId(''); }}>
              <option value="">请选择故事</option>{releases.map(r => <option key={r.id} value={r.id}>{r.title}</option>)}</select></label>
            {chosenRelease && <fieldset disabled={busy} className="space-y-2"><legend>你扮演的角色</legend><div className="flex flex-wrap gap-2">
              {chosenRelease.characters.map(c => <label key={c.id} className="flex min-h-11 cursor-pointer items-center gap-2 rounded border border-smoke px-4 py-3"><input type="radio" name="character" checked={characterId === c.id} onChange={() => setCharacterId(c.id)} />{c.name}</label>)}
            </div></fieldset>}
            <button className={primaryClass} disabled={busy || !chosenRelease || !characterId} onClick={() => void state.preview(Number(releaseId), characterId)}>阅读开场</button>
          </>}
        </section>}
        {mode === 'opening' && opening && <>
          <p className="text-acid-lime">你将扮演：{opening.characters.find(c => c.id === opening.selected_character_id)?.name}</p>
          <PlayText text={opening.introduction.text} />
          <Materials title="公共背景" items={opening.public_knowledge} collection="knowledge" />
          <Materials title="本人资料" items={opening.private_knowledge} collection="knowledge" />
          <Materials title="开场线索" items={[...opening.public_evidence, ...opening.private_evidence]} collection="evidence" />
          {!!opening.reading_supplements?.length && <Materials title="阅读补充" items={opening.reading_supplements} collection="knowledge" />}
          <button className={primaryClass} disabled={busy} onClick={() => void state.begin()}>开始游戏</button>
        </>}
        {mode === 'live' && play && <>
          {play.pending_ai && <p role="status" className="text-sm text-fog">仍有角色请求待完成，请稍后刷新进度核对。</p>}
          {!unresolved && pendingRequests(play).map(r => <button key={r.body.idempotency_key} className={buttonClass} disabled={busy}
            onClick={() => void send(r.endpoint, {}, r.body)}>核对已保存的角色请求</button>)}
          {play.finale_motivation && !play.finale_motivation.complete && <button className={buttonClass} disabled={busy || !!unresolved}
            onClick={() => void send('finale-motivations', {})}>核对终局看法进度</button>}
          {play.single_player?.stage && !play.settled && <section className="rounded border border-graphite p-4"><h2 className="text-paper">本轮核心目标</h2><p className="mt-2 text-sm">{play.single_player.stage.goal}</p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-fog">{play.single_player.stage.instructions.map((s, i) => <li key={i}>{s}</li>)}</ul></section>}
          {!!play.round_workspace?.phases.length && <label className="block space-y-2"><span className="text-sm">回看本局记录</span><select className={inputClass} value={review} onChange={e => setReview(e.target.value)}>
            <option value="">当前进度</option>{play.round_workspace.phases.filter(p => p.phase_id !== play.current_phase.id).map(p => <option key={p.phase_id} value={p.phase_id}>{p.title}</option>)}</select></label>}
          {phase ? <section className="space-y-4"><h2>{phase.title} · 只读回看</h2>
            <Materials title="当时已获资料" items={phase.materials.flatMap(ref => {
              const pool = ref.collection === 'memory' ? play.memories?.entries ?? [] : ref.collection === 'evidence' ? [...play.public_evidence, ...play.private_evidence] : [...play.public_knowledge, ...play.private_knowledge];
              const material = pool.find(m => m.id === ref.id); return material ? [{ ...material, assetCollection: ref.collection }] : [];
            })} />
            <NarrativeStream entries={reviewedEntries} />
            <button className={buttonClass} onClick={() => setReview('')}>回到当前进度</button>
          </section> : play.settled ? <Ending play={play} /> : <>
            {kind === 'READING' && <>
              <Materials title="公共阅读资料" items={play.public_knowledge} collection="knowledge" /><Materials title="本人阅读资料" items={play.private_knowledge} collection="knowledge" />
              {!!play.reading_supplements?.length && <Materials title="阅读补充" items={play.reading_supplements} collection="knowledge" />}
              <div id="phase-progress" className="scroll-mt-40"><button className={primaryClass} disabled={locked || !play.can_advance} onClick={() => void send('actions', actionPayload('ADVANCE_PHASE'))}>阅读完成，继续</button></div>
            </>}
            {kind === 'INVESTIGATION' && <><Investigation key={play.current_phase.id} play={play} locked={locked} />
              <Exchange key={`${scope}:${play.play_id}:${play.current_phase.id}:${play.full_game?.call?.id ?? "public"}`} noteKey={`draft:${scope}:${play.play_id}:${play.current_phase.id}`} ownerScope={scope} play={play} locked={locked} />
            </>}
            {kind === 'FINALE' && <Finale key={play.play_id} play={play} locked={locked} />}
            {!!entries.length && <section className="space-y-4"><h2 className="text-lg text-paper">公开交流记录</h2><NarrativeStream entries={entries} /></section>}
            {!!play.dialogue.length && <Materials title="历史材料问答" items={play.dialogue.map((d, i) => ({ id: `dialogue-${i}`, title: d.character_name, text: d.text }))} />}
          </>}
        </>}
      </div></main>
      {archive && play && <ArchiveDrawer key={`${scope}:${play.play_id}:${play.selected_character_id}`} play={play} scope={scope} onClose={() => { setArchive(false); archiveButton.current?.focus(); }} />}
    </div>
  </div></MaterialAssetContext.Provider>;
}
