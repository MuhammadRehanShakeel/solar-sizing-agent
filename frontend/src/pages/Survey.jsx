/**
 * Survey.jsx - Book a free site survey. Only the area/sector is asked, never a full address.
 * Opened from a quotation (?quote=<token>) the booking is linked to that quote for the installer.
 */
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Alert, Box, Button, Checkbox, Container, FormControlLabel, Grid, Stack, TextField, ToggleButton,
  ToggleButtonGroup, Typography } from '@mui/material';
import api, { storage } from '../services/api';
import { useLang } from '../services/i18n';
import { colors, DISPLAY } from '../theme';

const SLOTS = [['morning', 'Morning', '10 am - 1 pm'], ['afternoon', 'Afternoon', '1 pm - 4 pm'], ['evening', 'Evening', '4 pm - 7 pm']];

function nextDays(n = 14) {
  const days = [];
  const d = new Date();
  while (days.length < n) {
    d.setDate(d.getDate() + 1);
    if (d.getDay() !== 0) days.push(new Date(d));                        // no Sundays
  }
  return days;
}
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

export default function Survey() {
  const { t, dir } = useLang();
  const [params] = useSearchParams();
  const days = nextDays();
  const [form, setForm] = useState({ name: '', phone: '', area: '', date: iso(days[1]), slot: 'morning', consent: false, website: '' });
  const [done, setDone] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const { data } = await api.post('/surveys', {
        name: form.name, phone: form.phone, area: form.area, preferred_date: form.date, time_slot: form.slot,
        consent: form.consent, website: form.website, quote_token: params.get('quote') || null,
        session_id: storage.get('ss_session', localStorage) || null,
      });
      setDone(data);
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  };

  return (
    <Container maxWidth="md" sx={{ py: { xs: 3, md: 5 } }}>
      <Box {...dir}>
        <Typography variant="h2" sx={{ fontSize: { xs: 32, md: 44 } }}>{t('survey.title')}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, fontSize: 17, maxWidth: 600 }}>{t('survey.sub')}</Typography>
      </Box>
      {done ? (
        <Box sx={{ mt: 3, p: 3, borderRadius: 4, bgcolor: colors.greenSoft }}>
          <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 24 }}>Survey requested</Typography>
          <Typography sx={{ mt: 1 }}>{done.message}</Typography>
          <Typography fontSize={14} color="text.secondary" sx={{ mt: 1 }}>Booking number {done.booking_id}.</Typography>
        </Box>
      ) : (
        <Box component="form" onSubmit={submit} sx={{ mt: 3, p: { xs: 2, md: 3 }, bgcolor: '#fff', borderRadius: 4,
          border: `1px solid ${colors.line}` }}>
          {params.get('quote') && (
            <Alert severity="success" icon={false} sx={{ mb: 2 }}>Your quotation will be attached, so the engineer comes prepared.</Alert>
          )}
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}><TextField fullWidth required label="Your name" value={form.name} onChange={set('name')}
              autoComplete="name" /></Grid>
            <Grid item xs={12} sm={6}><TextField fullWidth required label="Mobile number" placeholder="0300 1234567"
              value={form.phone} onChange={set('phone')} inputProps={{ inputMode: 'tel' }} autoComplete="tel" /></Grid>
            <Grid item xs={12}><TextField fullWidth required label="Area or sector" placeholder="G-11 Islamabad, Bahria Town Phase 7…"
              value={form.area} onChange={set('area')} helperText="Only the area. The engineer asks for the exact address on the phone." /></Grid>
          </Grid>
          <Typography sx={{ fontWeight: 700, mt: 3, mb: 1 }}>Day</Typography>
          <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 1 }} role="radiogroup" aria-label="Day">
            {days.map((d) => {
              const value = iso(d);
              const active = value === form.date;
              return (
                <Box key={value} component="button" type="button" role="radio" aria-checked={active}
                  onClick={() => setForm({ ...form, date: value })}
                  sx={{ flexShrink: 0, width: 64, py: 1, borderRadius: 2, cursor: 'pointer', font: 'inherit',
                    border: `1px solid ${active ? colors.ink : colors.line}`, bgcolor: active ? colors.ink : '#fff',
                    color: active ? '#fff' : colors.ink }}>
                  <Typography fontSize={12.5} sx={{ opacity: 0.8 }}>{d.toLocaleDateString('en-GB', { weekday: 'short' })}</Typography>
                  <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 20 }}>{d.getDate()}</Typography>
                  <Typography fontSize={12}>{d.toLocaleDateString('en-GB', { month: 'short' })}</Typography>
                </Box>
              );
            })}
          </Box>
          <Typography sx={{ fontWeight: 700, mt: 2, mb: 1 }}>Time</Typography>
          <ToggleButtonGroup exclusive value={form.slot} onChange={(e, v) => v && setForm({ ...form, slot: v })}
            sx={{ flexWrap: 'wrap', '& .MuiToggleButton-root': { textTransform: 'none', display: 'block', px: 2 } }}>
            {SLOTS.map(([v, label, time]) => (
              <ToggleButton key={v} value={v}>
                <Typography sx={{ fontWeight: 700, fontSize: 15 }}>{label}</Typography>
                <Typography fontSize={12.5}>{time}</Typography>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
          <input type="text" name="website" value={form.website} onChange={set('website')} tabIndex={-1} autoComplete="off"
            style={{ position: 'absolute', left: -9999, width: 1, height: 1 }} aria-hidden="true" />
          <FormControlLabel sx={{ mt: 2, display: 'flex' }} control={<Checkbox checked={form.consent}
            onChange={(e) => setForm({ ...form, consent: e.target.checked })} />}
            label="The installer may call me on this number about the survey." />
          {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
          <Stack direction="row" justifyContent="flex-end" sx={{ mt: 2 }}>
            <Button type="submit" variant="contained" size="large" disabled={busy || !form.consent}>Request the survey</Button>
          </Stack>
        </Box>
      )}
    </Container>
  );
}
