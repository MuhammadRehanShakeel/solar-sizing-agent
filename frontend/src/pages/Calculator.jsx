/**
 * Calculator.jsx - The calculator as a form (no AI). Same maths as the advisor (backend sizing.py),
 * so it works even when the free AI quota is used up.
 * The backup load can come from the Backup planner (?backup=watts).
 */
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Alert, Box, Button, CircularProgress, Collapse, Container, Grid, MenuItem, Radio, RadioGroup, FormControlLabel,
  Stack, TextField, ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';
import MyLocationIcon from '@mui/icons-material/MyLocationRounded';
import api from '../services/api';
import OutagePicker, { OUTAGE_DEFAULT, outageToApi } from '../components/OutagePicker';
import QuoteView from '../components/QuoteView';
import { useLang } from '../services/i18n';
import { colors, DISPLAY } from '../theme';

const BACKUP = [
  { w: 800, label: 'Fans and lights (about 0.8 kW)' },
  { w: 1500, label: 'Fans, lights, fridge, TV (about 1.5 kW)' },
  { w: 2500, label: 'Plus a water motor or one inverter AC (about 2.5 kW)' },
  { w: 4000, label: 'Most of the house (about 4 kW)' },
];

function Step({ n, title, children }) {
  return (
    <Box component="section" sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '44px 1fr' }, gap: { xs: 0, sm: 1.5 },
      py: 2.5, '& + &': { borderTop: `1px solid ${colors.line}` } }}>
      <Typography aria-hidden sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 22, color: colors.grid,
        display: { xs: 'none', sm: 'block' } }}>{n}</Typography>
      <Box>
        <Typography component="h2" sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 19, mb: 1.5 }}>{title}</Typography>
        {children}
      </Box>
    </Box>
  );
}

export default function Calculator() {
  const { t, dir } = useLang();
  const [params] = useSearchParams();
  const [cities, setCities] = useState([]);
  const [form, setForm] = useState({ units: '', city: 'islamabad', backup: Number(params.get('backup')) || 1500,
    roof: '', budget: '', grid: 'auto', package: 'standard' });
  const [outage, setOutage] = useState(OUTAGE_DEFAULT);
  const [location, setLocation] = useState(null);
  const [quote, setQuote] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  useEffect(() => { api.get('/cities').then((r) => setCities(r.data)).catch(() => {}); }, []);

  const locate = () => {
    if (!navigator.geolocation) { setError('This browser cannot share a location.'); return; }
    navigator.geolocation.getCurrentPosition(
      (p) => setLocation({ lat: Math.round(p.coords.latitude * 100) / 100, lon: Math.round(p.coords.longitude * 100) / 100 }),
      () => setError('Location not shared. The city average will be used.'), { timeout: 10000 });
  };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    const units = form.units.split(/[\s,]+/).map(Number).filter((n) => n > 0);
    if (!units.length) { setError('Type your monthly units from the bill, e.g. 450 - or up to 12 months separated by commas.'); return; }
    setBusy(true);
    try {
      const { data } = await api.post('/calculate', {
        monthly_units: units.slice(0, 12), city: form.city, ...outageToApi(outage),
        backup_load_w: form.backup, roof_area_sqft: form.roof ? Number(form.roof) : null,
        budget_rs: form.budget ? Number(form.budget) : null,
        has_grid: form.grid !== 'none', grid_choice: form.grid === 'none' ? 'off_grid' : form.grid,
        package: form.package, ...(location || {}),
      });
      setQuote(data);
      setTimeout(() => document.getElementById('result')?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  };

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
      <Box {...dir}>
        <Typography variant="h2" sx={{ fontSize: { xs: 32, md: 44 } }}>{t('calc.title')}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, fontSize: 17 }}>{t('calc.sub')}</Typography>
      </Box>
      <Box component="form" onSubmit={submit} sx={{ mt: 3, px: { xs: 2, md: 3 }, pb: 2.5, bgcolor: '#fff', borderRadius: 4,
        border: `1px solid ${colors.line}` }}>
        <Step n="1" title="Your electricity use">
          <Grid container spacing={2}>
            <Grid item xs={12} md={7}>
              <TextField fullWidth label={t('calc.units')} value={form.units} onChange={set('units')}
                placeholder="450   or   300, 280, 350, 450, 600, 800, 850, 820, 650, 450, 320, 300"
                helperText="One number, or up to 12 months from the bill's history (most accurate)." />
            </Grid>
            <Grid item xs={8} md={3}>
              <TextField select fullWidth label={t('calc.city')} value={form.city} onChange={set('city')}>
                {cities.map((c) => <MenuItem key={c.key} value={c.key}>{c.name}</MenuItem>)}
                <MenuItem value="other">Other town</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={4} md={2}>
              <Button fullWidth variant={location ? 'contained' : 'outlined'} color={location ? 'success' : 'primary'}
                startIcon={<MyLocationIcon />} onClick={locate} sx={{ height: 56, borderRadius: 2 }}>
                {location ? 'Used' : 'Exact'}
              </Button>
            </Grid>
          </Grid>
          {location && (
            <Typography fontSize={13} color="text.secondary" sx={{ mt: 1 }}>
              NASA sunlight for {location.lat}, {location.lon} will be used (rounded, not stored with your name).
            </Typography>
          )}
        </Step>

        <Step n="2" title={t('strip.title')}>
          <OutagePicker value={outage} onChange={setOutage} />
          <Collapse in={outage.mode !== 'none'}>
            <TextField select fullWidth sx={{ mt: 2 }} label="What must keep running during load-shedding?" value={form.backup}
              onChange={set('backup')} helperText="Not sure? Use the Backup planner to tick your appliances.">
              {BACKUP.map((b) => <MenuItem key={b.w} value={b.w}>{b.label}</MenuItem>)}
              {!BACKUP.some((b) => b.w === form.backup) && <MenuItem value={form.backup}>From the backup planner ({form.backup} W)</MenuItem>}
            </TextField>
          </Collapse>
        </Step>

        <Step n="3" title={t('grid.title')}>
          <RadioGroup value={form.grid} onChange={set('grid')}>
            {[['auto', 'grid.auto'], ['net_billing', 'grid.net'], ['no_export', 'grid.noexp'], ['off_grid', 'grid.off'],
              ['none', 'grid.none']].map(([v, key]) => (
              <FormControlLabel key={v} value={v} control={<Radio size="small" />} label={t(key)} {...dir} />
            ))}
          </RadioGroup>
        </Step>

        <Step n="4" title="Optional">
          <Grid container spacing={2}>
            <Grid item xs={6} md={4}>
              <TextField fullWidth label="Free roof space (sq ft)" value={form.roof} onChange={set('roof')}
                inputProps={{ inputMode: 'numeric' }} />
            </Grid>
            <Grid item xs={6} md={4}>
              <TextField fullWidth label="Budget (Rs)" value={form.budget} onChange={set('budget')} inputProps={{ inputMode: 'numeric' }} />
            </Grid>
            <Grid item xs={12} md={4}>
              <ToggleButtonGroup fullWidth exclusive value={form.package} onChange={(e, v) => v && setForm({ ...form, package: v })}
                sx={{ height: 56, '& .MuiToggleButton-root': { textTransform: 'none' } }} aria-label="Package">
                <ToggleButton value="economy">Economy</ToggleButton>
                <ToggleButton value="standard">Standard</ToggleButton>
                <ToggleButton value="premium">Premium</ToggleButton>
              </ToggleButtonGroup>
            </Grid>
          </Grid>
        </Step>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <Stack direction="row" justifyContent="flex-end">
          <Button type="submit" variant="contained" size="large" disabled={busy}
            startIcon={busy ? <CircularProgress size={18} color="inherit" /> : null}>{t('calc.go')}</Button>
        </Stack>
      </Box>
      <Box id="result" sx={{ mt: 4 }}>{quote && <QuoteView quote={quote} />}</Box>
    </Container>
  );
}
