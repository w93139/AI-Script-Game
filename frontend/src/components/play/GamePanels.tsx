'use client';

import { useState } from 'react';
import type { PackagePlay, FullSubmission, TopicTurn } from '@/types/packagePlay';
import { usePlaySessionStore } from '@/stores/playSessionStore';
import { characterName, actionPayload } from '@/lib/playView';
import { PlayText } from './PlayText';
import { MaterialImages } from './AuthorizedImage';
import PlayVoiceInput from './PlayVoiceInput';
import type { AuthorizedVisual } from '@/services/playAssets';

export const buttonClass = 'min-h-11 rounded-md border border-smoke px-4 py-2 text-sm text-mist hover:border-mist disabled:cursor-not-allowed disabled:opacity-40';
export const primaryClass = `${buttonClass} bg-acid-lime text-void border-acid-lime`;
export const inputClass = 'min-h-11 w-full rounded-md border border-smoke bg-obsidian p-3 text-sm text-mist';
const guidedSchema = 'package-guided-command/1.0';
const tableSchema = 'package-full-play-command/1.0';

export function Materials({ title, items, collection }: { title: string; collection?: AuthorizedVisual['collection'];
  items: { id: string; title?: string; text?: string; assetCollection?: AuthorizedVisual['collection'] }[] }) {
  return <section className="space-y-3"><h2 className="text-lg text-paper">{title}</h2>
    {!items.length && <p className="text-sm text-fog">暂无已获得的资料。</p>}
    {items.map((m, i) => <details key={`${m.id}-${i}`} open className="rounded-lg border border-graphite bg-carbon p-4">
      <summary className="cursor-pointer text-sm text-paper">{m.title ?? `${title} ${i + 1}`}</summary>
      <div className="mt-3"><PlayText text={m.text ?? ''} /></div>
      <MaterialImages collection={m.assetCollection ?? collection} materialId={m.id} />
    </details>)}
  </section>;
}

export function Investigation({ play, locked }: { play: PackagePlay; locked: boolean }) {
  const send = usePlaySessionStore(s => s.send);
  const [selected, setSelected] = useState<string[]>([]);
  const options = play.mechanics?.available_actions ?? [];
  const chosen = selected.filter(id => options.some(o => o.id === id));
  const cost = options.filter(o => chosen.includes(o.id)).reduce((sum, o) => sum + o.cost, 0);
  const guided = play.guided_play;
  const ballot = play.full_game?.ballot;
  const call = play.full_game?.call;
  const phoneBusy = play.full_game?.phone_busy;
  const [confirmFinish, setConfirmFinish] = useState(false);
  return <section className="space-y-4 rounded-lg border border-graphite bg-carbon p-4">
    <h2 className="text-lg text-paper">本轮调查</h2>
    <p className="text-sm text-fog">剩余 {play.mechanics?.remaining_points ?? 0} 点；已选地点需 {cost} 点。</p>
    {phoneBusy && <div role="status" className="space-y-2 rounded border border-smoke p-3 text-sm">
      <p>{call ? `正在与${call.character_ids.filter(id => id !== play.selected_character_id).map(id => characterName(play, id)).join('、')}单独对话。结束对话后，才能调查地点或进入下一阶段。` : '其他角色正在通话，通话结束后才能调查或推进；请刷新进度。'}</p>
      {call && <button className={buttonClass} disabled={locked}
        onClick={() => void send('table', { schema_version: tableSchema, action: 'STOP_CALL' })}>结束对话，恢复调查</button>}
    </div>}
    {locked && <p role="status" className="text-sm text-fog">正在处理或核对上次操作，完成后可继续调查。</p>}
    {guided ? <>
      <fieldset disabled={locked || !guided.can_investigate_round} className="grid gap-2 sm:grid-cols-2">
        {options.map(o => <label key={o.id} className="flex min-h-11 cursor-pointer items-center gap-3 rounded border border-graphite p-3 text-sm has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50">
          <input type="checkbox" checked={chosen.includes(o.id)} onChange={e => setSelected(e.target.checked ? [...chosen, o.id] : chosen.filter(id => id !== o.id))} />
          {o.label}（{o.cost} 点）</label>)}
      </fieldset>
      <button className={primaryClass} disabled={locked || !guided.can_investigate_round || cost > (play.mechanics?.remaining_points ?? 0)}
        onClick={() => void send('guided', { schema_version: guidedSchema, action: 'INVESTIGATE_ROUND', payload: { action_ids: chosen } })}>
        {chosen.length ? '调查所选地点，其余交给其他角色' : '由其他角色安排本轮调查'}</button>
      {!!guided.required_speech_pending && <p role="status" className="text-sm text-fog">还有 {guided.required_speech_pending} 条必要说明待展示。</p>}
      {guided.can_present_required && <button className={buttonClass} disabled={locked}
        onClick={() => void send('guided', { schema_version: guidedSchema, action: 'PRESENT_REQUIRED' })}>展示必要说明</button>}
      <div id="phase-progress" className="scroll-mt-40 space-y-2 rounded border border-smoke p-3">
        <h3 className="text-paper">进入下一阶段</h3>
        <p className="text-sm text-fog">{phoneBusy ? '请先结束单独对话，再继续下一阶段。' : locked ? '请先完成或核对上次操作。' : guided.required_speech_pending ? '请先展示上方的必要说明。' : guided.can_finish_investigation ? '调查和交流完成后，可以结束本轮。也可以保留疑问，提前进入下一阶段。' : '当前暂不能推进，请刷新进度核对。'}</p>
        <button className={primaryClass} disabled={locked || !guided.can_finish_investigation}
          onClick={() => {
            if ((play.mechanics?.remaining_points ?? 0) > 0) setConfirmFinish(true);
            else void send('guided', { schema_version: guidedSchema, action: 'FINISH_INVESTIGATION' });
          }}>结束本轮调查，继续下一阶段</button>
        {confirmFinish && <div className="space-y-2 text-sm">
          <p>本轮还有 {play.mechanics?.remaining_points ?? 0} 点未使用。继续后将结束本轮调查。</p>
          <button className={buttonClass} onClick={() => setConfirmFinish(false)}>继续调查</button>{' '}
          <button className={primaryClass} disabled={locked || !guided.can_finish_investigation}
            onClick={() => void send('guided', { schema_version: guidedSchema, action: 'FINISH_INVESTIGATION' })}>确认结束本轮，进入下一阶段</button>
        </div>}
      </div>
    </> : play.full_game ? <>
      <p className="text-sm text-fog">本局采用共同表决选址，各席提交后按规则安排调查。</p>
      <button className={buttonClass} disabled={locked || !play.full_game.can_open_ballot}
        onClick={() => void send('table', { schema_version: tableSchema, action: 'OPEN_BALLOT' })}>开始选址表决</button>
      {ballot && <div className="space-y-2"><p className="text-sm">已提交 {ballot.sealed_count}/{ballot.required_count}</p>
        {ballot.status === 'WAITING' && !ballot.ballot && <div className="flex flex-wrap gap-2">
          {ballot.choices.map(o => <button className={buttonClass} disabled={locked} key={o.id}
            onClick={() => void send('table', { schema_version: tableSchema, action: 'CAST_BALLOT', payload: { kind: 'CHOOSE', choice_id: o.id } })}>{o.label}</button>)}
          <button className={buttonClass} disabled={locked} onClick={() => void send('table', { schema_version: tableSchema, action: 'CAST_BALLOT', payload: { kind: 'SKIP', choice_id: null } })}>提议结束调查</button>
        </div>}
        {ballot.status === 'TIE' && ballot.decider === play.selected_character_id && ballot.tied_choice_ids.map(id => <button key={id} className={buttonClass} disabled={locked}
          onClick={() => void send('table', { schema_version: tableSchema, action: 'BREAK_TIE', payload: { choice_id: id } })}>裁决：{ballot.choices.find(c => c.id === id)?.label ?? id}</button>)}
        <DecisionButtons play={play} locked={locked} />
      </div>}
      <button id="phase-progress" className={`${buttonClass} scroll-mt-40`} disabled={locked || !play.can_advance || !play.mechanics?.can_finish_phase}
        onClick={() => void send('actions', actionPayload('ADVANCE_PHASE'))}>继续下一阶段</button>
    </> : <>
      <div className="flex flex-wrap gap-2">{options.map(o => <button key={o.id} className={buttonClass} disabled={locked}
        onClick={() => void send('actions', { action: 'PERFORM_ACTION', target: { action_id: o.id } })}>{o.label}（{o.cost} 点）</button>)}</div>
      <button id="phase-progress" className={`${buttonClass} scroll-mt-40`} disabled={locked || !play.mechanics?.can_finish_phase}
        onClick={() => void send('actions', actionPayload(play.can_advance ? 'ADVANCE_PHASE' : 'SETTLE'))}>{play.can_advance ? '继续下一阶段' : '结束游戏'}</button>
    </>}
  </section>;
}

export function DecisionButtons({ play, locked }: { play: PackagePlay; locked: boolean }) {
  const send = usePlaySessionStore(s => s.send);
  const decisions = play.table_decisions;
  return <div className="flex flex-wrap gap-2">{decisions?.options.map(o => <button key={`${o.character_id}-${o.action}`} className={buttonClass}
    disabled={locked || !decisions.available} onClick={() => void send('decisions', {
      schema_version: 'package-table-decision-command/1.0', action: o.action, character_id: o.character_id,
    })}>请{characterName(play, o.character_id)}{o.action === 'SEAL_FINALE' ? '提交答卷' : o.action === 'BREAK_TIE' ? '裁决' : '表决'}</button>)}
    {decisions && !decisions.available && !!decisions.options.length && <p className="w-full text-sm text-fog">其他角色暂不能提交，请检查 AI 服务后刷新进度。当前答卷会保留。</p>}
  </div>;
}

export function Finale({ play, locked }: { play: PackagePlay; locked: boolean }) {
  const send = usePlaySessionStore(s => s.send);
  const finale = play.full_game?.finale;
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [accusation, setAccusation] = useState('');
  const [trust, setTrust] = useState('');
  const [reflection, setReflection] = useState('');
  const [confirm, setConfirm] = useState(false);
  if (!finale) return <p className="text-sm text-fog">本局暂未返回可提交的答卷，请刷新进度核对。</p>;
  const submit = () => {
    const payload: FullSubmission = { schema_version: 'structured-finale-submission/1.0',
      answers: finale.questions.map(q => ({ question_id: q.id, option_ids: answers[q.id] ?? [] })),
      vote: { accusation_id: accusation || null, trust_character_id: trust || null }, reflection };
    void send('table', { schema_version: tableSchema, action: 'SEAL_FINALE', payload });
  };
  return <section className="space-y-5">
    <h2 className="text-xl text-paper">终局答卷</h2>
    <p className="text-sm text-fog">各题可留空表示不确定。提交后无法修改，所有角色封卷后才会揭晓。</p>
    {play.finale_speeches?.map(e => <p key={e.character_id} className="rounded border border-graphite p-3 text-sm">{characterName(play, e.character_id)}的封卷前看法：{e.text || '本次未留下看法'}</p>)}
    {!finale.sealed ? <fieldset disabled={locked || !!play.finale_motivation && !play.finale_motivation.complete} className="space-y-5">
      {finale.questions.map(q => <fieldset key={q.id} className="space-y-2 rounded border border-graphite p-4"><legend>{q.prompt}（最多 {q.max_choices} 项）</legend>
        {q.options.map(o => {
          const list = answers[q.id] ?? []; const checked = list.includes(o.id);
          return <label key={o.id} className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={checked}
            disabled={!checked && list.length >= q.max_choices}
            onChange={e => setAnswers({ ...answers, [q.id]: e.target.checked ? [...list, o.id] : list.filter(id => id !== o.id) })} />{o.label}</label>;
        })}
      </fieldset>)}
      <label className="block space-y-2"><span>指认</span><select className={inputClass} value={accusation} onChange={e => setAccusation(e.target.value)}>
        <option value="">弃权／不确定</option>{finale.votes.accusation_options.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}</select></label>
      <label className="block space-y-2"><span>信任的人</span><select className={inputClass} value={trust} onChange={e => setTrust(e.target.value)}>
        <option value="">不选择</option>{finale.votes.trust_character_ids.map(id => <option key={id} value={id}>{characterName(play, id)}</option>)}</select></label>
      <label className="block space-y-2"><span>你的推理（可选）</span><textarea maxLength={1000} className={inputClass} value={reflection} onChange={e => setReflection(e.target.value)} /></label>
      <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={confirm} onChange={e => setConfirm(e.target.checked)} />我已检查答卷，确认封卷后不再修改</label>
      <button className={primaryClass} disabled={!confirm} onClick={submit}>提交我的答卷</button>
    </fieldset> : <p role="status" className="text-acid-lime">你的答卷已保存并封卷。</p>}
    <p>封卷进度：{finale.votes.sealed_count}/{finale.votes.required_count}</p>
    <DecisionButtons play={play} locked={locked || !!play.finale_motivation && !play.finale_motivation.complete} />
    <button className={primaryClass} disabled={locked || !finale.all_sealed} onClick={() => void send('actions', actionPayload('SETTLE'))}>查看结局与得分</button>
  </section>;
}

function TopicResult({ turn, play, locked }: { turn: TopicTurn; play: PackagePlay; locked: boolean }) {
  const send = usePlaySessionStore(s => s.send);
  const recoveryLocked = usePlaySessionStore(s => s.busy || !!s.unresolved);
  const publicAnswer = turn.channel === 'PUBLIC' && turn.status === 'OK'
    ? play.role_responses?.entries.find(e => e.reply_to === turn.reply_to && e.speaker === turn.character_id && e.phase_id === turn.phase_id)?.text : null;
  const answer = turn.answer ?? publicAnswer;
  return <div className="space-y-2 rounded border border-graphite p-3 text-sm" data-topic-turn={turn.id}>
    <h4 className="text-paper">{characterName(play, turn.character_id)} · {turn.channel === 'PRIVATE' ? '单独对话' : '公开回答'}</h4>
    <p>你的问题：{turn.question}</p>{answer && <p className="whitespace-pre-wrap">{answer}</p>}
    <p className="text-fog">{({ READY: '问题已保存，等待回应', PENDING: '正在等待结果，请核对原回应，不用重新提问。', OK: '已回应', FAILED: turn.receipt_status === 'INVALID' ? '这次生成的回答未通过核验，未作为角色发言保存。' : '这次未取得有效回答，你的问题已保存。', FALLBACK: '已采用资料简答，可以继续调查或选择其他问题。' })[turn.status]}</p>
    {turn.status === 'READY' && !turn.reply_request && !turn.can_fallback && <p className="text-fog">这条问题已不在当前可回应的对话中，请查看已保存记录或选择当前问题。</p>}
    {turn.status === 'READY' && turn.reply_request && !turn.can_fallback && <button className={buttonClass} disabled={locked}
      onClick={() => void send(turn.channel === 'PRIVATE' ? 'private-responses' : 'responses', {}, turn.reply_request ?? undefined)}>请角色回应</button>}
    {turn.status === 'PENDING' && turn.reply_request && <button className={buttonClass} disabled={recoveryLocked}
      onClick={() => void send(turn.channel === 'PRIVATE' ? 'private-responses' : 'responses', {}, turn.reply_request ?? undefined)}>核对原回应</button>}
    {turn.can_fallback && <p className="text-fog">可使用当前剧情资料中已核对的简短回答。点击后会保存到这次对话，不会再次请求 AI。</p>}
    {turn.can_fallback && <button className={primaryClass} disabled={locked} onClick={() => void send('topic', {
      schema_version: 'package-topic-command/1.0', action: 'USE_FALLBACK', payload: { turn_id: turn.id },
    })}>使用资料简答，继续游戏</button>}
    {turn.status === 'FAILED' && !turn.can_fallback && <p className="text-fog">当前不能使用资料简答。可以继续调查或选择其他问题；如正在单独对话，可先结束对话再查看。</p>}
  </div>;
}

export function Exchange({ play, locked, noteKey, ownerScope }: { play: PackagePlay; locked: boolean; noteKey: string; ownerScope: string }) {
  const send = usePlaySessionStore(s => s.send);
  const askTopic = usePlaySessionStore(s => s.askTopic);
  const busy = usePlaySessionStore(s => s.busy);
  const error = usePlaySessionStore(s => s.error);
  const [draft, setDraft] = useState(() => sessionStorage.getItem(`${noteKey}:public`) ?? '');
  const [privateDraft, setPrivateDraft] = useState(() => sessionStorage.getItem(`${noteKey}:private:${play.full_game?.call?.id ?? "none"}`) ?? '');
  const [peer, setPeer] = useState('');
  const [selection, setSelection] = useState('');
  const call = play.full_game?.call;
  const single = play.single_player;
  const busyPhone = play.full_game?.phone_busy;
  const peers = play.characters.filter(c => c.id !== play.selected_character_id);
  const save = (value: string, priv: boolean) => {
    (priv ? setPrivateDraft : setDraft)(value);
    sessionStorage.setItem(priv ? `${noteKey}:private:${play.full_game?.call?.id ?? 'none'}` : `${noteKey}:public`, value);
  };
  const submit = async (priv: boolean) => {
    const text = (priv ? privateDraft : draft).trim(); if (!text) return;
    const ok = await send(priv ? 'table' : 'discussion', priv
      ? { schema_version: tableSchema, action: 'PRIVATE_SPEAK', payload: { text } }
      : { schema_version: 'package-discussion-command/1.0', action: 'SPEAK', text });
    if (ok) save('', priv);
  };
  const questionOptions = single?.topics.flatMap(topic => topic.responders.flatMap(r => r.intents.filter(i => i.available).flatMap(i => r.channels.filter(channel =>
    channel === 'PUBLIC' ? !busyPhone : !!call?.character_ids.includes(r.character_id)).map(channel => ({ key: `${topic.id}:${r.character_id}:${i.id}:${channel}`,
      topic_id: topic.id, character_id: r.character_id, intent_id: i.id, channel, question: i.question, label: `${topic.title} · ${characterName(play, r.character_id)} · ${i.label} · ${channel === 'PRIVATE' ? '私聊' : '公开'}` }))))) ?? [];
  const selected = questionOptions.find(o => o.key === selection);
  const peerHasQuestions = !single || single.topics.some(t => t.responders.some(r =>
    r.character_id === peer && r.channels.includes('PRIVATE') && r.intents.some(i => i.available)));
  const latestHuman = [...(play.discussion?.entries ?? [])].reverse().find(e => e.phase_id === play.current_phase.id && e.speaker === play.selected_character_id);
  return <section className="space-y-4 rounded-lg border border-graphite bg-carbon p-4">
    <h2 className="text-lg text-paper">交流</h2>
    {busy && <p role="status" className="text-sm text-fog">正在提交操作或等待角色回应，请稍候…</p>}
    {error && <p role="alert" className="text-sm text-coral-red">{error}</p>}
    <fieldset disabled={locked} className="space-y-3">
      {single && <div className="space-y-3 rounded border border-smoke p-3">
        <h3 className="text-paper">{call ? `向${call.character_ids.filter(id => id !== play.selected_character_id).map(id => characterName(play, id)).join('、')}提问` : '向角色提问'}</h3>
        <p className="text-sm text-fog">选择当前问题，确认后会直接请求角色回应。新的线索可能解锁更多问题。</p>
        {questionOptions.length ? <>
          <label className="block space-y-2"><span className="text-sm">当前可问的问题</span><select className={inputClass} value={selected?.key ?? ''} onChange={e => setSelection(e.target.value)}>
            <option value="">请选择问题</option>{questionOptions.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}</select></label>
          {selected && <p className="text-sm">将发送：{selected.question}</p>}
          <button className={primaryClass} disabled={!selected || !single.available} onClick={() => {
            if (!selected) return;
            const { topic_id, character_id, intent_id, channel } = selected;
            void askTopic({ topic_id, character_id, intent_id, channel });
          }}>发送问题并等待回应</button>
        </> : <p role="status" className="text-sm text-fog">{call ? '对方当前没有可问的问题。请先结束单独对话，继续调查或与其他角色交流。' : busyPhone ? '通话进行中，暂不能公开提问。' : '当前没有可问的问题。可以先调查获取线索，或查看下方已有问题的回应。'}</p>}
      </div>}
    </fieldset>
    {!!single?.turns.some(t => t.phase_id === play.current_phase.id) && <section className="space-y-3" aria-label="本轮问题与回答">
      <h3 className="text-paper">本轮问题与回答</h3>
      {single.turns.filter(t => t.phase_id === play.current_phase.id).reverse().map(t => <TopicResult key={t.id} turn={t} play={play} locked={locked} />)}
    </section>}
    <fieldset disabled={locked} className="space-y-3">
      <label className="block space-y-2"><span className="text-sm">{single ? '陈述我的发现（公开）' : '公开发言'}</span><textarea className={inputClass} maxLength={1000} value={draft} onChange={e => save(e.target.value, false)} placeholder="写下你的发现或判断…" /></label>
      <PlayVoiceInput ownerId={ownerScope} playId={play.play_id} phaseId={play.current_phase.id} revision={play.revision}
        channel="PUBLIC" disabled={locked || !!busyPhone} value={draft} onChange={value => save(value, false)} />
      {single && <p className="text-sm text-fog">这里记录你的说法，不会自动请求 AI 回答。想获得回答，请使用上方的提问区。</p>}
      <button className={buttonClass} disabled={!!busyPhone || !draft.trim()} onClick={() => void submit(false)}>{single ? '记录公开发言' : '发送公开发言'}</button>
      {!single && play.role_responses && latestHuman && <div className="flex flex-wrap gap-2">{play.role_responses.character_ids.map(id => <button key={id} className={buttonClass}
        disabled={!play.role_responses?.available || !!busyPhone} onClick={() => void send('responses', { schema_version: 'package-dialogue-command/1.0', action: 'RESPOND', character_id: id, reply_to: latestHuman.id })}>请{characterName(play, id)}回应</button>)}</div>}
      {play.full_game && <div className="space-y-3 border-t border-graphite pt-4">
        {call ? <>
          <h3>单独对话 · {call.character_ids.filter(id => id !== play.selected_character_id).map(id => characterName(play, id)).join('、')}</h3>
          {play.full_game.private_discussion.filter(e => e.call_id === call.id).map(e => <p key={e.id} className="whitespace-pre-wrap text-sm">{characterName(play, e.speaker)}：{e.text}</p>)}
          <label className="block space-y-2"><span className="text-sm">{single ? '向对方陈述我的发现' : '私聊内容'}</span><textarea className={inputClass} maxLength={1000} value={privateDraft} onChange={e => save(e.target.value, true)} /></label>
          <PlayVoiceInput ownerId={ownerScope} playId={play.play_id} phaseId={play.current_phase.id} revision={play.revision}
            channel="PRIVATE" callId={call.id} disabled={locked} value={privateDraft} onChange={value => save(value, true)} />
          {single && <p className="text-sm text-fog">这里仅保存你对对方说的话；需要回应时，请在上方选择可问的问题。</p>}
          <button className={buttonClass} disabled={!privateDraft.trim()} onClick={() => void submit(true)}>{single ? '记录单独发言' : '发送私聊'}</button>
          {!single && play.private_replies?.available && play.private_replies.options.slice(-1).map(o => <button key={o.reply_to} className={buttonClass} onClick={() => void send('private-responses', {
            schema_version: 'package-private-dialogue-command/1.0', action: 'RESPOND_PRIVATE', ...o,
          })}>请对方回应</button>)}
          <button className={buttonClass} onClick={() => void send('table', { schema_version: tableSchema, action: 'STOP_CALL' })}>结束单独对话</button>
        </> : <>
          <label className="block space-y-2"><span className="text-sm">单独对话对象</span><select className={inputClass} value={peer} onChange={e => { setPeer(e.target.value); setSelection(''); }}>
            <option value="">请选择角色</option>{peers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
          <button className={buttonClass} disabled={!peer || !!busyPhone || !!play.full_game.ballot} onClick={() => void send('table', { schema_version: tableSchema, action: 'START_CALL', payload: { peer_character_id: peer } })}>开始单独对话</button>
          {peer && !peerHasQuestions && <p className="text-sm text-fog">这个角色当前没有可问的问题。建议先调查，或选择其他角色；仍可单独陈述你的发现。</p>}
          {busyPhone && <p className="text-sm text-fog">线路正忙，请稍后刷新进度。</p>}
        </>}
      </div>}
    </fieldset>
    <details><summary className="min-h-11 cursor-pointer py-2 text-sm text-fog">查看已保存的私聊记录</summary>
      {play.full_game?.private_discussion.map(e => <p key={e.id} className="whitespace-pre-wrap py-2 text-sm">{characterName(play, e.speaker)}：{e.text}</p>)}
    </details>
  </section>;
}

export function Ending({ play }: { play: PackagePlay }) {
  const result = play.full_game?.result;
  const own = result?.totals.find(t => t.character_id === play.selected_character_id);
  const ownEndings = result?.endings.filter(e => e.character_ids.includes(play.selected_character_id));
  return <section className="space-y-4">
    <h2 className="text-xl text-acid-lime">本局已结束</h2>
    {own && <p>你的得分：{own.total_points ?? `已判 ${own.known_points}`} / {own.max_points}{own.total_points === null ? '（含未判项目）' : ''}</p>}
    {ownEndings?.flatMap(e => e.texts).map((text, i) => <PlayText key={i} text={text} />)}
    {result?.goals.filter(g => g.character_id === play.selected_character_id).map(g => <p key={g.id}>{g.title}：{g.points ?? '未判'} / {g.max_points}</p>)}
    <Materials title="真相复盘" items={[...(play.settlement?.text ? [{ id: 'settlement', text: play.settlement.text }] : []), ...(play.settlement?.truths ?? [])]} />
    {result?.vote_disclosure && <section><h3>正式投票公示</h3>{result.vote_disclosure.map(v => <p key={v.character_id} className="py-2 text-sm">{characterName(play, v.character_id)} → {v.voted_for_label}；封卷前看法：{v.motivation || '未留下看法'}</p>)}</section>}
    <details><summary className="min-h-11 cursor-pointer py-2">其他角色的结局与得分</summary>
      {result?.totals.filter(t => t.character_id !== play.selected_character_id).map(t => <p key={t.character_id}>{characterName(play, t.character_id)}：{t.total_points ?? `已判 ${t.known_points}`} / {t.max_points}</p>)}
      {result?.endings.filter(e => !e.character_ids.includes(play.selected_character_id)).flatMap(e => e.texts).map((text, i) => <div key={i} className="py-3"><PlayText text={text} /></div>)}
    </details>
    {!!play.post_game_qa?.questions.length && <Materials title="结局答疑" items={play.post_game_qa.questions} />}
  </section>;
}
