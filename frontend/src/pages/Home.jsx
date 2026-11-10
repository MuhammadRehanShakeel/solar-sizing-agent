/**
 * Home.jsx - The landing page. The interactive "day strip" is the centre: people set when their
 * light goes and immediately see which kind of system keeps the house running.
 */
import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Accordion, AccordionDetails, AccordionSummary, Box, Button, Container, Grid, MenuItem, Stack, TextField,
  Typography } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMoreRounded';
import ChatIcon from '@mui/icons-material/ForumOutlined';
import CalcIcon from '@mui/icons-material/CalculateOutlined';
import BatteryIcon from '@mui/icons-material/BatteryChargingFullRounded';
import DayStrip, { cutVerdict } from '../components/DayStrip';
import { clock } from '../components/OutagePicker';
import { useLang } from '../services/i18n';
import { colors, DISPLAY } from '../theme';

const HOURS = Array.from({ length: 48 }, (_, i) => i / 2);

const FAQ = [
  ['Is net metering finished?',
    'For new solar users, yes. Since 9 February 2026 new connections get net billing: units you send to WAPDA are credited at about Rs 11, while units you take still cost the normal tariff (Rs 22-47 a unit). So the best system is one that uses its own power during the day - which is what our calculator sizes for. Users approved before that date keep their old terms.'],
  ['On-grid or hybrid - which one do I need?',
    'On-grid is cheaper and pays back fastest, but it must switch off whenever WAPDA is off (to protect line workers). If your light goes for a few hours every day or at night, a hybrid with a battery keeps fans, lights and the fridge running. Set your load-shedding times above to see the difference.'],
  ['Can I leave WAPDA completely?',
    'Yes, with an off-grid system: more panels and a bigger battery, because December and January fog cut the sun by about a third. Your quotation shows the cost, which months may fall short, and the bill if you keep WAPDA only as a backup.'],
  ['How accurate is the price?',
    'Prices come from the installer\'s price list, item by item (panels, inverter, battery, structure, wiring, approval). The final price is confirmed after a free site survey, because roof shape, shade and cable lengths differ from house to house.'],
  ['What happens to my bill photo?',
    'It is read once to find your monthly units and sanctioned load, then thrown away. Your name, address and reference number are not stored. You check the numbers before anything is calculated.'],
];

function Verdict({ start, end }) {
  const { t, dir } = useLang();
  const v = cutVerdict(start, end);
  const rows = [
    [t('strip.ongrid'), t('strip.off'), colors.dusk],
    [t('strip.hybrid'), v.hybrid === 'sun' ? t('strip.on_sun') : v.hybrid === 'battery' ? t('strip.on_batt') : t('strip.on_both'),
      colors.green],
  ];
  return (
    <Stack spacing={0.75} sx={{ mt: 1.5 }} {...dir}>
      {rows.map(([name, text, color]) => (
        <Stack key={name} direction="row" spacing={1.25} alignItems="baseline">
          <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color, flexShrink: 0, transform: 'translateY(1px)' }} />
          <Typography fontSize={15}><b>{name}</b> {text}</Typography>
        </Stack>
      ))}
      <Typography fontSize={13} color="text.secondary" dir="ltr" lang="en" sx={{ fontFamily: 'inherit' }}>
        {v.sun ? `${v.sun} h of this cut is in sunshine` : 'All of this cut is after dark'}
        {v.dark && v.sun ? `, ${v.dark} h after dark` : ''}.
      </Typography>
    </Stack>
  );
}

function Way({ icon, title, body, to, cta, big }) {
  const { dir } = useLang();
  return (
    <Box component={RouterLink} to={to} sx={{ display: 'flex', gap: 2, p: big ? 3 : 2.5, textDecoration: 'none', color: 'inherit',
      bgcolor: big ? colors.ink : '#fff', borderRadius: 3, border: big ? 'none' : `1px solid ${colors.line}`, height: '100%',
      transition: 'transform .15s', '&:hover': { transform: 'translateY(-2px)' } }}>
      <Box sx={{ color: big ? colors.sun : colors.ink, mt: 0.25 }}>{icon}</Box>
      <Box {...dir}>
        <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: big ? 24 : 19, color: big ? '#fff' : colors.ink,
          lineHeight: 1.2 }}>{title}</Typography>
        <Typography sx={{ mt: 0.75, color: big ? '#c9d8d4' : 'text.secondary', maxWidth: 520 }}>{body}</Typography>
        <Typography sx={{ mt: 1.5, fontWeight: 700, color: big ? colors.sun : colors.ink }}>{cta}</Typography>
        {big && (
          <Stack spacing={1} sx={{ mt: 3, maxWidth: 440 }} aria-hidden>
            <Box sx={{ alignSelf: 'flex-end', px: 1.5, py: 1, borderRadius: 2, bgcolor: '#1f4d55', color: '#fff', fontSize: 14 }}>
              Bill 25 hazar aata hai, hafte mein ek dafa 9 se 2 baje light jati hai
            </Box>
            <Box sx={{ alignSelf: 'flex-start', px: 1.5, py: 1, borderRadius: 2, bgcolor: '#fff', color: colors.ink, fontSize: 14 }}>
              Samajh gaya: hafte mein 1 din, 9 am se 2 pm. Yeh din ka waqt hai, is liye panels hi ghar chalayenge...
            </Box>
          </Stack>
        )}
      </Box>
    </Box>
  );
}

export default function Home() {
  const { t, dir, ur } = useLang();
  const [start, setStart] = useState(9);
  const [end, setEnd] = useState(14);

  return (
    <>
      {/* ---------------- hero ---------------- */}
      <Box sx={{ bgcolor: '#fff', borderBottom: `1px solid ${colors.line}` }}>
        <Container maxWidth="lg" sx={{ py: { xs: 5, md: 8 } }}>
          <Grid container spacing={{ xs: 4, md: 6 }} alignItems="center">
            <Grid item xs={12} md={6} {...dir}>
              <Typography variant="h1" sx={{ fontSize: { xs: 40, sm: 52, md: 60 }, maxWidth: 620,
                ...(ur && { fontFamily: '"Noto Nastaliq Urdu", serif', lineHeight: 1.9, letterSpacing: 0, fontSize: { xs: 32, md: 44 } }) }}>
                {t('hero.title')}
              </Typography>
              <Typography sx={{ mt: 2.5, fontSize: 18, color: 'text.secondary', maxWidth: 540 }}>{t('hero.body')}</Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mt: 4 }}>
                <Button component={RouterLink} to="/advisor" variant="contained" size="large" color="primary">{t('hero.start')}</Button>
                <Button component={RouterLink} to="/calculator" variant="outlined" size="large">{t('hero.calc')}</Button>
              </Stack>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box data-shot="daystrip"
                sx={{ p: { xs: 2, sm: 3 }, borderRadius: 4, bgcolor: colors.bg, border: `1px solid ${colors.line}` }}>
                <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 20 }} {...dir}>{t('strip.title')}</Typography>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.5, mb: 2 }}>
                  <TextField select size="small" value={start} onChange={(e) => setStart(Number(e.target.value))}
                    inputProps={{ 'aria-label': 'Load-shedding starts' }} sx={{ flex: 1 }}>
                    {HOURS.map((h) => <MenuItem key={h} value={h}>{clock(h)}</MenuItem>)}
                  </TextField>
                  <Typography color="text.secondary">to</Typography>
                  <TextField select size="small" value={end} onChange={(e) => setEnd(Number(e.target.value))}
                    inputProps={{ 'aria-label': 'Load-shedding ends' }} sx={{ flex: 1 }}>
                    {HOURS.map((h) => <MenuItem key={h} value={h}>{clock(h)}</MenuItem>)}
                  </TextField>
                </Stack>
                <DayStrip start={start} end={end} />
                <Stack direction="row" spacing={2} sx={{ mt: 1 }} {...dir}>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <Box sx={{ width: 14, height: 8, bgcolor: colors.sun, borderRadius: 1 }} />
                    <Typography fontSize={13} color="text.secondary">{t('strip.sun')}</Typography>
                  </Stack>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <Box sx={{ width: 14, height: 8, bgcolor: colors.dusk, borderRadius: 1 }} />
                    <Typography fontSize={13} color="text.secondary">{t('strip.cut')}</Typography>
                  </Stack>
                </Stack>
                <Verdict start={start} end={end} />
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* ---------------- three ways ---------------- */}
      <Container maxWidth="lg" sx={{ py: { xs: 5, md: 7 } }}>
        <Typography variant="h3" sx={{ fontSize: { xs: 28, md: 36 }, mb: 3 }} {...dir}>{t('ways.title')}</Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Way big icon={<ChatIcon sx={{ fontSize: 34 }} />} title={t('ways.chat.t')} body={t('ways.chat.b')} to="/advisor"
              cta={t('nav.talk')} />
          </Grid>
          <Grid item xs={12} md={6}>
            <Stack spacing={2} sx={{ height: '100%' }}>
              <Way icon={<CalcIcon sx={{ fontSize: 28 }} />} title={t('ways.calc.t')} body={t('ways.calc.b')} to="/calculator"
                cta={t('calc.title')} />
              <Way icon={<BatteryIcon sx={{ fontSize: 28 }} />} title={t('ways.backup.t')} body={t('ways.backup.b')} to="/backup"
                cta={t('backup.title')} />
            </Stack>
          </Grid>
        </Grid>
      </Container>

      {/* ---------------- WAPDA choices ---------------- */}
      <Box sx={{ bgcolor: '#fff', borderTop: `1px solid ${colors.line}`, borderBottom: `1px solid ${colors.line}` }}>
        <Container maxWidth="lg" sx={{ py: { xs: 5, md: 7 } }}>
          <Grid container spacing={4}>
            <Grid item xs={12} md={4} {...dir}>
              <Typography variant="h3" sx={{ fontSize: { xs: 28, md: 36 } }}>{t('wapda.title')}</Typography>
              <Typography sx={{ mt: 1.5, color: 'text.secondary', fontSize: 17 }}>{t('wapda.body')}</Typography>
            </Grid>
            <Grid item xs={12} md={8}>
              <Stack divider={<Box sx={{ borderTop: `1px solid ${colors.line}` }} />}>
                {[['wapda.net', colors.sky], ['wapda.noexp', colors.sun], ['wapda.off', colors.green]].map(([key, color]) => (
                  <Stack key={key} direction="row" spacing={2.5} sx={{ py: 2.25 }} {...dir}>
                    <Box sx={{ width: 6, borderRadius: 3, bgcolor: color, flexShrink: 0 }} />
                    <Box>
                      <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 20 }}>{t(`${key}.t`)}</Typography>
                      <Typography sx={{ color: 'text.secondary', mt: 0.5 }}>{t(`${key}.b`)}</Typography>
                    </Box>
                  </Stack>
                ))}
              </Stack>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* ---------------- trust ---------------- */}
      <Container maxWidth="lg" sx={{ py: { xs: 5, md: 7 } }}>
        <Grid container spacing={4}>
          <Grid item xs={12} md={4} {...dir}>
            <Typography variant="h3" sx={{ fontSize: { xs: 28, md: 36 } }}>{t('trust.title')}</Typography>
          </Grid>
          <Grid item xs={12} md={8}>
            <Grid container spacing={3}>
              {['trust.ai', 'trust.sun', 'trust.tariff', 'trust.price'].map((key) => (
                <Grid item xs={12} sm={6} key={key} {...dir}>
                  <Box sx={{ borderTop: `3px solid ${colors.ink}`, pt: 1.5 }}>
                    <Typography sx={{ fontSize: 16 }}>{t(key)}</Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Grid>
        </Grid>
      </Container>

      {/* ---------------- FAQ ---------------- */}
      <Container maxWidth="md" sx={{ pb: { xs: 4, md: 6 } }}>
        <Typography variant="h3" sx={{ fontSize: { xs: 28, md: 36 }, mb: 2 }} {...dir}>{t('faq.title')}</Typography>
        {FAQ.map(([q, a]) => (
          <Accordion key={q} disableGutters sx={{ bgcolor: 'transparent', borderBottom: `1px solid ${colors.line}`,
            '&:before': { display: 'none' } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontWeight: 700, fontSize: 17 }}>{q}</Typography>
            </AccordionSummary>
            <AccordionDetails><Typography color="text.secondary" sx={{ maxWidth: 680 }}>{a}</Typography></AccordionDetails>
          </Accordion>
        ))}
        <Box sx={{ mt: 5, p: { xs: 3, md: 4 }, borderRadius: 4, bgcolor: colors.sunSoft, display: 'flex', gap: 2,
          flexDirection: { xs: 'column', sm: 'row' }, alignItems: { sm: 'center' }, justifyContent: 'space-between' }}>
          <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 22, maxWidth: 460 }} {...dir}>{t('survey.sub')}</Typography>
          <Button component={RouterLink} to="/survey" variant="contained" size="large" sx={{ flexShrink: 0 }}>{t('survey.title')}</Button>
        </Box>
      </Container>
    </>
  );
}
