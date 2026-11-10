/**
 * OutagePicker.jsx - "When does your light go?" in the way people actually describe it:
 * none / every day / some days a week, and from what time to what time (or just how many hours).
 * The DayStrip below shows it straight away.
 */
import { Box, Checkbox, FormControlLabel, MenuItem, Slider, Stack, TextField, ToggleButton, ToggleButtonGroup,
  Typography } from '@mui/material';
import DayStrip from './DayStrip';
import { useLang } from '../services/i18n';

export const OUTAGE_DEFAULT = { mode: 'none', days: 2, start: 9, end: 14, unknown: false, hours: 2 };

const HOURS = Array.from({ length: 48 }, (_, i) => i / 2);
export function clock(h) {
  const hour = Math.floor(h) % 24;
  const suffix = hour < 12 ? 'am' : 'pm';
  return `${hour % 12 || 12}${h % 1 ? ':30' : ''} ${suffix}`;
}

/** The picker's value -> the fields the backend understands. */
export function outageToApi(o) {
  if (!o || o.mode === 'none') return { outage_hours: 0 };
  const days = o.mode === 'daily' ? null : o.days;
  if (o.unknown) return { outage_hours: o.hours, outage_days_per_week: days };
  return { outage_start_hour: o.start, outage_end_hour: o.end, outage_days_per_week: days };
}

export default function OutagePicker({ value, onChange }) {
  const { t } = useLang();
  const set = (patch) => onChange({ ...value, ...patch });
  return (
    <Stack spacing={1.75}>
      <ToggleButtonGroup exclusive size="small" value={value.mode} onChange={(e, v) => v && set({ mode: v })}
        sx={{ flexWrap: 'wrap', '& .MuiToggleButton-root': { textTransform: 'none', px: 1.75 } }}>
        <ToggleButton value="none">{t('out.none')}</ToggleButton>
        <ToggleButton value="daily">{t('out.daily')}</ToggleButton>
        <ToggleButton value="some">{t('out.some')}</ToggleButton>
      </ToggleButtonGroup>
      {value.mode !== 'none' && (
        <>
          {value.mode === 'some' && (
            <Box sx={{ px: 1 }}>
              <Typography fontSize={14} color="text.secondary">{t('out.days')}: <b>{value.days}</b></Typography>
              <Slider value={value.days} min={1} max={6} step={1} marks onChange={(e, v) => set({ days: v })}
                aria-label={t('out.days')} />
            </Box>
          )}
          {value.unknown ? (
            <Box sx={{ px: 1 }}>
              <Typography fontSize={14} color="text.secondary">{t('out.hours')}: <b>{value.hours}</b></Typography>
              <Slider value={value.hours} min={0.5} max={16} step={0.5} onChange={(e, v) => set({ hours: v })}
                aria-label={t('out.hours')} />
            </Box>
          ) : (
            <Stack direction="row" spacing={1} alignItems="center">
              <TextField select size="small" label={t('out.time')} value={value.start} sx={{ flex: 1 }}
                onChange={(e) => set({ start: Number(e.target.value) })}>
                {HOURS.map((h) => <MenuItem key={h} value={h}>{clock(h)}</MenuItem>)}
              </TextField>
              <Typography color="text.secondary">to</Typography>
              <TextField select size="small" value={value.end} sx={{ flex: 1 }} inputProps={{ 'aria-label': 'Until' }}
                onChange={(e) => set({ end: Number(e.target.value) })}>
                {HOURS.map((h) => <MenuItem key={h} value={h}>{clock(h)}</MenuItem>)}
              </TextField>
            </Stack>
          )}
          <FormControlLabel control={<Checkbox size="small" checked={value.unknown}
            onChange={(e) => set({ unknown: e.target.checked })} />} label={t('out.unknown')} />
          {!value.unknown && <DayStrip start={value.start} end={value.end} />}
        </>
      )}
    </Stack>
  );
}
