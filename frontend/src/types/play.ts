/** 证词条目：一条叙事流消息（真人或 AI） */
export interface DepositionEntry {
  id: string;
  seq: number;
  speaker: string;
  self?: boolean;
  text: string;
}
