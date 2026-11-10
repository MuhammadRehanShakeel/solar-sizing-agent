/**
 * MessageText.jsx - Shows the agent's answer with simple formatting:
 * **bold**, "- " bullet lines, numbered lines and clickable links. No HTML is ever injected.
 */
import { Box, Link } from '@mui/material';
import { isUrdu } from '../utils/format';

function inline(text, keyBase) {
  const parts = text.split(/(\*\*[^*]+\*\*|https?:\/\/[^\s)]+)/g).filter(Boolean);
  return parts.map((part, i) => {
    const key = `${keyBase}-${i}`;
    if (part.startsWith('**') && part.endsWith('**')) return <b key={key}>{part.slice(2, -2)}</b>;
    if (/^https?:\/\//.test(part)) {
      const local = part.includes('/quote/');
      const href = local ? part.slice(part.indexOf('/quote/')) : part;
      return <Link key={key} href={href} target={local ? undefined : '_blank'} rel="noreferrer">
        {local ? 'Open your quotation' : part}</Link>;
    }
    return part;
  });
}

export default function MessageText({ text }) {
  const lines = (text || '').replace(/\r/g, '').split('\n');
  return (
    <Box dir={isUrdu(text) ? 'rtl' : 'ltr'} sx={{ fontSize: 15, lineHeight: 1.55, '& p': { m: 0 } }}>
      {lines.map((line, i) => {
        const bullet = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/);
        if (bullet) {
          return <Box key={i} sx={{ display: 'flex', gap: 1, pl: 0.5 }}><span>•</span><span>{inline(bullet[1], i)}</span></Box>;
        }
        if (/^#{1,4}\s/.test(line)) return <Box key={i} sx={{ fontWeight: 700, mt: 0.5 }}>{inline(line.replace(/^#+\s/, ''), i)}</Box>;
        return line.trim() ? <p key={i}>{inline(line, i)}</p> : <Box key={i} sx={{ height: 6 }} />;
      })}
    </Box>
  );
}
