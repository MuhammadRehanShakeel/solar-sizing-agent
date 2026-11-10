/**
 * BackupPlanner.jsx - Tick what must keep running during load-shedding; see the battery and inverter you need
 * and how long each battery size lasts. No AI: the backend adds up watts (appliances.py).
 */
import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Alert, Box, Button, Container, Grid, IconButton, Slider, Stack, Typography } from '@mui/material';
import AddIcon from '@mui/icons-material/AddRounded';
import RemoveIcon from '@mui/icons-material/RemoveRounded';
import api from '../services/api';
import { useLang } from '../services/i18n';
import { colors, DISPLAY } from '../theme';

const START = { ceiling_fan: 3, led_light: 5, fridge: 1, router: 1 };

export default function BackupPlanner() {
  const { t, dir, ur } = useLang();
  const [catalogue, setCatalogue] = useState([]);
  const [counts, setCounts] = useState(START);
  const [hours, setHours] = useState(4);
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => { api.get('/appliances').then((r) => setCatalogue(r.data)).catch((e) => setError(e.message)); }, []);
  useEffect(() => {
    const items = Object.entries(counts).filter(([, n]) => n > 0).map(([name, quantity]) => ({ name, quantity }));
    if (!items.length) { setPlan(null); return undefined; }
    const timer = setTimeout(() => {
      api.post('/backup-plan', { appliances: items, hours_needed: hours }).then((r) => { setPlan(r.data); setError(''); })
        .catch((e) => setError(e.message));
    }, 250);
    return () => clearTimeout(timer);
  }, [counts, hours]);

  const change = (key, delta) => setCounts((c) => ({ ...c, [key]: Math.max(0, Math.min(50, (c[key] || 0) + delta)) }));
  const best = plan?.hours_per_battery.find((h) => h.battery_kwh === plan.recommended_battery_kwh);
  const longest = Math.max(...(plan?.hours_per_battery.map((h) => h.hours || 0) || [1]), hours);

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
      <Box {...dir}>
        <Typography variant="h2" sx={{ fontSize: { xs: 32, md: 44 } }}>{t('backup.title')}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, fontSize: 17 }}>{t('backup.sub')}</Typography>
      </Box>
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      <Grid container spacing={3} sx={{ mt: 1 }}>
        <Grid item xs={12} md={7}>
          <Box sx={{ bgcolor: '#fff', borderRadius: 4, border: `1px solid ${colors.line}`, px: 2 }}>
            {catalogue.map((a, i) => {
              const n = counts[a.key] || 0;
              return (
                <Stack key={a.key} direction="row" alignItems="center" spacing={1.5}
                  sx={{ py: 1.1, borderTop: i ? `1px solid ${colors.line}` : 'none', opacity: n ? 1 : 0.75 }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography sx={{ fontWeight: n ? 700 : 400 }} {...(ur ? { lang: 'ur' } : {})}>
                      {ur ? a.label_ur : a.label}
                    </Typography>
                    <Typography fontSize={13} color="text.secondary">{a.watts} W</Typography>
                  </Box>
                  <IconButton size="small" onClick={() => change(a.key, -1)} disabled={!n} aria-label={`Fewer ${a.label}`}
                    sx={{ border: `1px solid ${colors.line}` }}><RemoveIcon fontSize="small" /></IconButton>
                  <Typography sx={{ width: 28, textAlign: 'center', fontFamily: DISPLAY, fontWeight: 700, fontSize: 18 }}
                    aria-live="polite">{n}</Typography>
                  <IconButton size="small" onClick={() => change(a.key, 1)} aria-label={`More ${a.label}`}
                    sx={{ border: `1px solid ${colors.line}` }}><AddIcon fontSize="small" /></IconButton>
                </Stack>
              );
            })}
          </Box>
        </Grid>
        <Grid item xs={12} md={5}>
          <Box sx={{ position: { md: 'sticky' }, top: 88 }}>
            <Box sx={{ p: 2.5, bgcolor: '#fff', borderRadius: 4, border: `1px solid ${colors.line}` }}>
              <Typography fontSize={14} color="text.secondary" {...dir}>{t('backup.hours')}: <b>{hours} h</b></Typography>
              <Slider value={hours} min={1} max={12} step={0.5} onChange={(e, v) => setHours(v)} aria-label={t('backup.hours')}
                sx={{ color: colors.dusk }} />
              {plan ? (
                <>
                  <Grid container spacing={2} sx={{ mt: 0.5 }}>
                    <Grid item xs={6}>
                      <Typography fontSize={13.5} color="text.secondary">Battery</Typography>
                      <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 30 }}>{plan.recommended_battery_kwh} kWh</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography fontSize={13.5} color="text.secondary">Inverter</Typography>
                      <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 30 }}>{plan.recommended_inverter_kw} kW</Typography>
                    </Grid>
                  </Grid>
                  <Typography fontSize={14} color="text.secondary" sx={{ mt: 1 }}>
                    Running together: {plan.running_watts.toLocaleString()} W. Energy for {hours} h: {plan.battery_needed_kwh} kWh.
                    {best?.hours ? ` A ${best.battery_kwh} kWh battery lasts about ${best.hours} h with these.` : ''}
                  </Typography>
                  <Typography sx={{ fontWeight: 700, mt: 2.5, mb: 1 }}>How long each battery lasts</Typography>
                  <Stack spacing={1}>
                    {plan.hours_per_battery.map((h) => (
                      <Stack key={h.battery_kwh} direction="row" spacing={1.5} alignItems="center">
                        <Typography sx={{ width: 60, fontSize: 14, fontWeight: h.battery_kwh === plan.recommended_battery_kwh ? 700 : 400 }}>
                          {h.battery_kwh} kWh
                        </Typography>
                        <Box sx={{ flex: 1, height: 14, bgcolor: colors.bg, borderRadius: 2, position: 'relative', overflow: 'hidden' }}>
                          <Box sx={{ height: '100%', width: `${Math.min(100, (h.hours / longest) * 100)}%`, borderRadius: 2,
                            bgcolor: h.hours >= hours ? colors.green : colors.dusk }} />
                          <Box sx={{ position: 'absolute', top: 0, bottom: 0, left: `${(hours / longest) * 100}%`, width: 2,
                            bgcolor: colors.ink }} />
                        </Box>
                        <Typography sx={{ width: 52, fontSize: 14, textAlign: 'right' }}>{h.hours} h</Typography>
                      </Stack>
                    ))}
                  </Stack>
                  <Typography fontSize={12.5} color="text.secondary" sx={{ mt: 1 }}>
                    The dark line is your longest cut. Green bars last through it.
                  </Typography>
                  {plan.warnings.map((w) => <Alert key={w} severity="warning" sx={{ mt: 1.5 }}>{w}</Alert>)}
                  <Button fullWidth variant="contained" sx={{ mt: 2.5 }} component={RouterLink}
                    to={`/calculator?backup=${plan.running_watts}`}>Use this in the calculator</Button>
                </>
              ) : (
                <Typography color="text.secondary" sx={{ mt: 2 }}>Add at least one appliance.</Typography>
              )}
            </Box>
          </Box>
        </Grid>
      </Grid>
    </Container>
  );
}
