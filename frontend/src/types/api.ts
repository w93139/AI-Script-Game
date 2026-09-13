/** 后端融合接口契约类型（与 docs/contracts/package-play.md 对齐）。 */

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string | null;
  user: { id: number; username: string; nickname?: string | null };
}

export interface ReleaseCharacter {
  id: string;
  name: string;
}

export interface Release {
  id: number;
  version_id: string;
  title: string;
  content_version: string;
  player_count: number;
  characters: ReleaseCharacter[];
  runtime_ready: boolean;
  status: string;
}

export interface Material {
  id: string;
  text?: string;
  disclosure?: string;
  kind?: string;
}

export interface OpeningSession {
  session_id: string;
  release_id: number;
  version_id: string;
  selected_character_id: string;
  status: string;
  script: { title: string; content_version: string; player_count: number };
  characters: ReleaseCharacter[];
  introduction: { text: string };
  initial_phase: { id: string; title: string };
  public_knowledge: Material[];
  private_knowledge: Material[];
  public_evidence: Material[];
  private_evidence: Material[];
  [key: string]: unknown;
}

export interface DiscussionEntry {
  id: string;
  sequence: number;
  phase_id: string;
  kind: string;
  speaker: string;
  text: string;
}

export interface AvailableAction {
  id: string;
  label: string;
  cost: number;
}

export interface DialogueEntry {
  speaker: string;
  text: string;
  self?: boolean;
}

export interface PlayView {
  play_id: string;
  status: "TEXT_PLAY" | "SETTLED";
  settled: boolean;
  revision?: number;
  selected_character?: { id: string; name: string } | null;
  phase?: { id: string; title: string } | null;
  public_knowledge?: Material[];
  private_knowledge?: Material[];
  public_evidence?: Material[];
  private_evidence?: Material[];
  settlement?: { text: string; truths: { id: string; text: string }[] } | null;
  dialogue?: DialogueEntry[];
  discussion?: { entries: DiscussionEntry[] };
  model?: { available: boolean; reason?: string } | null;
  pending_ai?: unknown;
  last_ai_status?: string | null;
  mechanics?: {
    initial_points: number;
    remaining_points: number;
    spent_points: number;
    can_finish_phase: boolean;
    available_actions: AvailableAction[];
  };
  memories?: { id: string; title: string; text?: string }[];
  [key: string]: unknown;
}

export interface CreateSessionBody {
  release_id: number;
  character_id: string;
  idempotency_key: string;
}

export interface CreatePlayBody {
  opening_session_id: string;
  idempotency_key: string;
}

export type PlayActionName =
  | "ADVANCE_PHASE"
  | "SHARE_MATERIAL"
  | "SETTLE"
  | "PERFORM_ACTION";

export interface ActionBody {
  expected_revision: number;
  idempotency_key: string;
  action: PlayActionName;
  target?: { collection?: string; id?: string; action_id?: string } | null;
}

export interface AskBody {
  expected_revision: number;
  idempotency_key: string;
  character_id: string;
  question: string;
}

export interface SpeakBody {
  schema_version: string;
  action: "SPEAK";
  expected_revision: number;
  idempotency_key: string;
  text: string;
}
