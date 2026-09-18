'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import type { PackagePlay } from '@/types/packagePlay';
import { Materials, inputClass } from './GamePanels';

export function ArchiveDrawer({ play, scope, onClose }: { play: PackagePlay; scope: string; onClose: () => void }) {
  const [tab, setTab] = useState('characters');
  const noteKey = `play-note:${scope}:${play.play_id}:${play.selected_character_id}`;
  const [note, setNote] = useState(() => localStorage.getItem(noteKey) ?? '');
  const [noteError, setNoteError] = useState('');
  const tabs = [['characters', '角色资料'], ['evidence', '线索'], ['memories', '回忆'], ['notes', '手记']];
  return <aside aria-label="本局档案" className="fixed inset-0 z-30 flex flex-col bg-void p-4 md:static md:z-auto md:w-80 md:shrink-0 md:border-l md:border-graphite">
    <div className="mb-3 flex items-center justify-between"><h2 className="text-paper">本局档案</h2>
      <button autoFocus onClick={onClose} aria-label="关闭档案" className="min-h-11 min-w-11"><X size={20} /></button></div>
    <div className="mb-4 flex flex-wrap gap-1">{tabs.map(([id, title]) => <button key={id} aria-pressed={tab === id}
      className={`min-h-11 rounded px-2 text-sm ${tab === id ? 'bg-obsidian text-acid-lime' : 'text-mist'}`} onClick={() => setTab(id)}>{title}</button>)}</div>
    <div className="min-h-0 flex-1 space-y-4 overflow-y-auto">
      {tab === 'characters' && <>
        {play.characters.map(c => <p key={c.id} className="text-sm">{c.name}{c.id === play.selected_character_id ? '（你）' : ''}</p>)}
        <Materials title="公共背景" items={play.public_knowledge} collection="knowledge" />
        <Materials title="本人资料" items={play.private_knowledge} collection="knowledge" />
      </>}
      {tab === 'evidence' && <><Materials title="公开线索" items={play.public_evidence} collection="evidence" /><Materials title="本人线索" items={play.private_evidence} collection="evidence" /></>}
      {tab === 'memories' && <Materials title="已获得的回忆" items={play.memories?.entries ?? []} collection="memory" />}
      {tab === 'notes' && <label className="block space-y-3"><span className="text-sm text-fog">只保存在当前浏览器，按账号、对局和角色分开。</span>
        <textarea aria-label="我的手记" className={`${inputClass} min-h-64`} value={note} maxLength={10000} onChange={e => {
          setNote(e.target.value);
          try { localStorage.setItem(noteKey, e.target.value); setNoteError(''); }
          catch { setNoteError('当前浏览器无法保存手记，请先复制保存。'); }
        }} />{noteError && <span role="alert">{noteError}</span>}</label>}
    </div>
  </aside>;
}
