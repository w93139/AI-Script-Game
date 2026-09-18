import type { PackagePlay } from '../types/packagePlay';
import type { DepositionEntry } from '../types/play';

export function phaseKind(play: PackagePlay) {
  return play.full_game?.phase_kind ?? (play.settled ? 'FINALE' : play.mechanics ? 'INVESTIGATION' : 'READING');
}
export function characterName(play: PackagePlay, id: string) {
  return play.characters.find(c => c.id === id)?.name ?? id;
}
export function publicEntries(play: PackagePlay): DepositionEntry[] {
  const entries = [...(play.discussion?.entries ?? []), ...(play.role_responses?.entries ?? [])];
  const known = new Set<string>();
  return entries.sort((a, b) => a.sequence - b.sequence).filter(e => {
    if (known.has(e.id)) return false;
    known.add(e.id); return true;
  }).map(e => ({ id: e.id, seq: e.sequence, speaker: characterName(play, e.speaker),
    self: e.speaker === play.selected_character_id, text: e.text }));
}
export function actionPayload(action: 'ADVANCE_PHASE' | 'SETTLE') {
  // These commands must OMIT target, including null.
  return { action };
}

/** Reconstruct only server-recorded pending requests, using their original keys. */
export function pendingRequests(play: PackagePlay) {
  const requests: { endpoint: import('../services/play').CommandEndpoint;
    body: import('../services/play').CommandBody }[] = [];
  for (const r of play.table_decisions?.requests ?? []) if (r.status === 'PENDING') {
    requests.push({ endpoint: 'decisions', body: { schema_version: 'package-table-decision-command/1.0',
      expected_revision: r.revision, idempotency_key: r.request_id, character_id: r.character_id, action: r.action } });
  }
  for (const [endpoint, records, schema, action] of [
    ['responses', play.role_responses?.requests, 'package-dialogue-command/1.0', 'RESPOND'],
    ['private-responses', play.private_replies?.requests, 'package-private-dialogue-command/1.0', 'RESPOND_PRIVATE'],
  ] as const) for (const r of records ?? []) if (r.status === 'PENDING') {
    requests.push({ endpoint, body: { schema_version: schema, expected_revision: r.revision,
      idempotency_key: r.request_id, character_id: r.character_id, reply_to: r.reply_to, action } });
  }
  return requests;
}
