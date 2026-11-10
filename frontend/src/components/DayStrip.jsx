/**
 * DayStrip.jsx - One day (midnight to midnight) as a strip: the sun's arc over the hours the panels work,
 * and the load-shedding window in dusk-violet. Used on the home page, the calculator and the quotation,
 * so people SEE why an on-grid system is off during a daytime cut and why night cuts need a battery.
 */
import { Box } from '@mui/material';
import { colors } from '../theme';

const W = 720;
const H = 126;
const TOP = 58;           // where the hour track starts
const TRACK = 34;
const x = (h) => (h / 24) * W;

function cutRects(start, end) {
  if (start == null || end == null) return [];
  const s = ((start % 24) + 24) % 24;
  const e = ((end % 24) + 24) % 24 || 24;
  return e > s ? [[s, e]] : [[s, 24], [0, e]];                // a cut that passes midnight is drawn in two parts
}

export default function DayStrip({ start, end, sunFrom = 8, sunTo = 17, label, height = H }) {
  const cuts = cutRects(start, end);
  // the sun's path: a half-ellipse from sunrise (6) to sunset (18.5)
  const rise = x(6);
  const set = x(18.5);
  const arc = `M ${rise} ${TOP - 2} A ${(set - rise) / 2} ${TOP - 12} 0 0 1 ${set} ${TOP - 2}`;
  const noonX = x(12.25);
  return (
    <Box component="svg" viewBox={`0 0 ${W} ${height}`} role="img"
      aria-label={label || 'A day from midnight to midnight showing sun hours and load-shedding'}
      sx={{ width: '100%', maxWidth: 760, height: 'auto', display: 'block', overflow: 'visible' }}>
      <defs>
        <pattern id="cut-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="8" height="8" fill={colors.dusk} />
          <rect width="3" height="8" fill="#5d50a0" />
        </pattern>
        <linearGradient id="sun-band" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor={colors.sun} stopOpacity="0.35" />
          <stop offset="0.5" stopColor={colors.sun} stopOpacity="1" />
          <stop offset="1" stopColor={colors.sun} stopOpacity="0.35" />
        </linearGradient>
      </defs>

      <path d={arc} fill="none" stroke={colors.sun} strokeWidth="2" strokeDasharray="2 6" strokeLinecap="round" />
      <circle cx={noonX} cy={12} r="9" fill={colors.sun} />

      {/* night / day track */}
      <rect x="0" y={TOP} width={W} height={TRACK} rx="8" fill="#dbe4e0" />
      <rect x={x(sunFrom)} y={TOP} width={x(sunTo) - x(sunFrom)} height={TRACK} fill="url(#sun-band)" />
      {cuts.map(([s, e]) => (
        <rect key={s} x={x(s)} y={TOP - 6} width={Math.max(3, x(e) - x(s))} height={TRACK + 12} rx="4"
          fill="url(#cut-hatch)" />
      ))}
      {Array.from({ length: 25 }, (_, h) => (
        <line key={h} x1={x(h)} x2={x(h)} y1={TOP + TRACK} y2={TOP + TRACK + (h % 6 === 0 ? 9 : 4)}
          stroke={colors.grid} strokeWidth="1" />
      ))}
      {[[0, '12 am'], [6, '6 am'], [12, '12 pm'], [18, '6 pm'], [24, '12 am']].map(([h, t]) => (
        <text key={h} x={Math.min(W - 2, Math.max(2, x(h)))} y={TOP + TRACK + 27} fontSize="19"
          textAnchor={h === 0 ? 'start' : h === 24 ? 'end' : 'middle'} fill={colors.muted}
          fontFamily="Source Sans 3, sans-serif">{t}</text>
      ))}
    </Box>
  );
}

/** What each system does during a cut: used for the verdict lines next to the strip. */
export function cutVerdict(start, end, sunFrom = 8, sunTo = 17) {
  if (start == null || end == null) return null;
  let sun = 0;
  let dark = 0;
  const length = ((end - start) % 24 + 24) % 24 || 24;
  for (let i = 0; i < length * 4; i += 1) {
    const h = (start + i / 4) % 24;
    if (h >= sunFrom && h < sunTo) sun += 0.25; else dark += 0.25;
  }
  return { sun, dark, hybrid: sun && dark ? 'both' : sun ? 'sun' : 'battery' };
}
