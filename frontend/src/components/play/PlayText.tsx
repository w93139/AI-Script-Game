import { Fragment } from 'react';

const listStart = /^(?:[-*+]\s|\d+[.)]\s|\d+、)/;
const blockStart = /^(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|\d+、|>|```|\||\*\*[^*]+\*\*$|__[^_]+__$)/;
const cjk = /[\u3400-\u9fff]/;
const readingHeading = /^(?:你的(?:表现|目的|回忆(?:（共\d+条）)?)|你已经知道的其他人|附[：:]名词解释|第[一二三四五六七八九十\d]+(?:阶段|幕)|结局[一二三四五六七八九十\d]+)$/;

/** Presentation only: never change stored materials, model inputs or triggers. */
export function normalizePlayText(text: string): string {
  const lines = text.replace(/\r\n?/g, '\n')
    .replace(/^\s*(?:#{1,6}\s*)?\d+-R\s*[|｜]\s*([^\n]+)\n(?=\s*编辑修订版\s*v?\d)/gmi, '## $1\n')
    .replace(/^\s*编辑修订版\s*v?\d+(?:\.\d+)*(?:\s*[|｜]\s*(?:新增线索|补充线索|非原\d+号(?:线索)?卡?))*\s*$/gmi, '')
    .replace(/^(\s*)编辑修订版\s*v?\d+(?:\.\d+)*[。．]\s*/gmi, '$1').split('\n');
  const out: string[] = [];
  let blanks = 0;
  let fenced = false;
  for (const raw of lines) {
    if (raw.trim().startsWith('```')) { fenced = !fenced; out.push(raw.trim()); blanks = 0; continue; }
    if (fenced) { out.push(raw); continue; }
    // Internal ending-selection metadata occupies its own marked line. Keep
    // the adjacent title/story intact, including ordinary narrative mentions.
    if (/^\s*〔编辑修订条件〕/.test(raw)) { blanks++; continue; }
    const line = raw.trim().replace(/([\u3400-\u9fff，。！？；：、“”《》]) +(?=[\u3400-\u9fff，。！？；：、“”《》])/g, '$1');
    if (!line) { blanks++; continue; }
    const last = out.at(-1) || '';
    const listContinuation = listStart.test(last) && blanks === 0;
    const prose = last && (!blockStart.test(last) || listContinuation) && !blockStart.test(line) && !readingHeading.test(last) && !readingHeading.test(line);
    const join = prose && cjk.test(last) && cjk.test(line)
      && !/[。！？!?：:；;][”’」』）)]?$/.test(last)
      && (blanks === 0 || /[\u3400-\u9fff，、]$/.test(last));
    const left = Array.from(last).at(-1) || '';
    const right = Array.from(line)[0] || '';
    const wordBoundary = /[\p{L}\p{N}]/u.test(left) && /[\p{L}\p{N}]/u.test(right) && !cjk.test(left) && !cjk.test(right);
    if (join) out[out.length - 1] = last + (wordBoundary ? ' ' : '') + line;
    else { if (out.length && blanks) out.push(''); out.push(line); }
    blanks = 0;
  }
  return out.join('\n');
}

function inline(text: string) {
  // Deliberately render HTML, image URLs and links as text. Images are loaded
  // only from the server-authorized visual collection, never from Markdown.
  return text.split(/(\*\*[^*\n]+\*\*|__[^_\n]+__|`[^`\n]+`|\*[^*\n]+\*)/g).map((part, i) => {
    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) return <strong key={i} className="font-bold text-paper">{part.slice(2, -2)}</strong>;
    if (part.startsWith('`') && part.endsWith('`')) return <code key={i} className="rounded bg-obsidian px-1">{part.slice(1, -1)}</code>;
    if (part.startsWith('*') && part.endsWith('*')) return <em key={i}>{part.slice(1, -1)}</em>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}

/** Small safe Markdown renderer matching the reading formats used by this app. */
export function PlayText({ text }: { text: string }) {
  const lines = normalizePlayText(text).split('\n');
  const content = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line) continue;
    if (line.startsWith('```')) {
      const start = i; const code: string[] = [];
      while (++i < lines.length && !lines[i].startsWith('```')) code.push(lines[i]);
      content.push(<pre key={start} className="my-3 overflow-x-auto rounded bg-obsidian p-3 text-sm"><code>{code.join('\n')}</code></pre>);
      continue;
    }
    if (readingHeading.test(line)) { content.push(<h3 key={i} className="mb-3 mt-6 text-xl font-bold leading-relaxed">{line}</h3>); continue; }
    const heading = line.match(/^(#{1,6})\s+(.+?)(?:\s+#+)?$/);
    if (heading) {
      const Heading = heading[1].length <= 2 ? 'h3' : 'h4';
      content.push(<Heading key={i} className={`mb-3 mt-6 font-bold leading-relaxed ${heading[1].length === 1 ? 'text-2xl' : heading[1].length === 2 ? 'text-xl' : 'text-lg'}`}>{inline(heading[2])}</Heading>);
      continue;
    }
    if (/^[-*_]{3,}$/.test(line)) { content.push(<hr key={i} className="my-5 border-graphite" />); continue; }
    const list = line.match(/^(?:[-*+]\s+|\d+[.)]\s+|\d+、\s*)(.*)$/);
    if (list) { content.push(<p key={i} className="mb-2 pl-5 -indent-4"><span className="mr-2 text-acid-lime">{line.match(/^\d+[.)、]/)?.[0] || '•'}</span>{inline(list[1])}</p>); continue; }
    if (/^>\s?/.test(line)) { content.push(<blockquote key={i} className="my-3 border-l-2 border-acid-lime/60 pl-4 text-mist">{inline(line.replace(/^>\s?/, ''))}</blockquote>); continue; }
    content.push(<p key={i} className="mb-4 last:mb-0">{inline(line)}</p>);
  }
  return <div className="min-w-0 break-words text-[15px] leading-8 [overflow-wrap:anywhere]">{content}</div>;
}
