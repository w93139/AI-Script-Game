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
  version_id: number;
  title: string;
  content_version: string;
  player_count: number;
  characters: ReleaseCharacter[];
  runtime_ready: boolean;
  status: string;
}

export type { PackagePlay as PlayView, PlayMaterial as Material,
  CreatePackagePlayRequest as CreatePlayBody, PackagePlayActionRequest as ActionBody,
  PackagePlayAskRequest as AskBody, PackagePlaySpeakRequest as SpeakBody } from './packagePlay';

export interface CreateSessionBody {
  release_id: number;
  character_id: string;
  idempotency_key: string;
}
export interface OpeningSession {
  session_id: string; release_id: number; version_id: number; selected_character_id: string;
  status: string; script: { title: string; content_version: string; player_count: number };
  characters: ReleaseCharacter[]; introduction: { text: string }; initial_phase: { id: string; title: string };
  public_knowledge: import('./packagePlay').PlayMaterial[];
  private_knowledge: import('./packagePlay').PlayMaterial[];
  public_evidence: import('./packagePlay').PlayMaterial[];
  private_evidence: import('./packagePlay').PlayMaterial[];
  reading_supplements?: { id: string; text: string }[];
  visuals?: import('../services/playAssets').AuthorizedVisual[];
}

export interface LibraryItem {
  play_id: string;
  opening_session_id: string;
  title: string;
  character_name: string;
  phase_label: string;
  settled: boolean;
  revision: number;
  updated_at: string;
}

export interface LibraryResult {
  items: LibraryItem[];
  has_more: boolean;
}
