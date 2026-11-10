/**
 * SiteLayout.jsx - Header (menu + English/اردو switch) and footer for every public page.
 */
import { useState } from 'react';
import { Link as RouterLink, NavLink, Outlet, useLocation } from 'react-router-dom';
import { Box, Button, Container, Drawer, IconButton, Link, List, ListItemButton, ListItemText, Stack,
  ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import MenuIcon from '@mui/icons-material/MenuRounded';
import Logo from './Logo';
import { useLang } from '../services/i18n';
import { colors } from '../theme';

const NAV = [['/advisor', 'nav.advisor'], ['/calculator', 'nav.calculator'], ['/backup', 'nav.backup'],
  ['/survey', 'nav.survey']];

function LangSwitch() {
  const { lang, setLang } = useLang();
  return (
    <ToggleButtonGroup size="small" exclusive value={lang} onChange={(e, v) => v && setLang(v)} aria-label="Language"
      sx={{ '& .MuiToggleButton-root': { px: 1.2, py: 0.3, textTransform: 'none', fontWeight: 600 } }}>
      <ToggleButton value="en">EN</ToggleButton>
      <ToggleButton value="ur" lang="ur" sx={{ fontFamily: '"Noto Nastaliq Urdu", serif', lineHeight: 1.4 }}>اردو</ToggleButton>
    </ToggleButtonGroup>
  );
}

export default function SiteLayout({ fullHeight = false }) {
  const { t, dir } = useLang();
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: colors.bg, display: 'flex', flexDirection: 'column' }}>
      <Box component="header" sx={{ bgcolor: '#fff', borderBottom: `1px solid ${colors.line}`, position: 'sticky', top: 0,
        zIndex: 10 }}>
        <Container maxWidth="lg" sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 1.1 }}>
          <RouterLink to="/" style={{ textDecoration: 'none' }} aria-label="SolarSaathi home"><Logo small /></RouterLink>
          <Stack component="nav" direction="row" spacing={0.5} sx={{ display: { xs: 'none', md: 'flex' }, ml: 2, flex: 1 }}>
            {NAV.map(([to, key]) => (
              <Button key={to} component={NavLink} to={to} color="inherit" {...dir}
                sx={{ color: colors.muted, borderRadius: 2, '&.active': { color: colors.ink, bgcolor: colors.bg } }}>
                {t(key)}
              </Button>
            ))}
          </Stack>
          <Box sx={{ flex: { xs: 1, md: 0 } }} />
          <LangSwitch />
          {pathname !== '/advisor' && (
            <Button component={RouterLink} to="/advisor" variant="contained" color="secondary"
              sx={{ display: { xs: 'none', sm: 'inline-flex' }, whiteSpace: 'nowrap' }} {...dir}>{t('nav.talk')}</Button>
          )}
          <IconButton sx={{ display: { md: 'none' } }} onClick={() => setOpen(true)} aria-label="Menu"><MenuIcon /></IconButton>
        </Container>
      </Box>
      <Drawer anchor="right" open={open} onClose={() => setOpen(false)}>
        <List sx={{ width: 260, pt: 2 }}>
          {[['/', 'nav.home'], ...NAV, ['/staff', 'nav.staff']].map(([to, key]) => (
            <ListItemButton key={to} component={RouterLink} to={to} onClick={() => setOpen(false)} selected={pathname === to}>
              <ListItemText primary={t(key)} {...dir} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>

      <Box component="main" sx={{ flex: 1, display: fullHeight ? 'flex' : 'block', flexDirection: 'column' }}>
        <Outlet />
      </Box>

      {!fullHeight && (
        <Box component="footer" sx={{ borderTop: `1px solid ${colors.line}`, bgcolor: '#fff', mt: 6 }}>
          <Container maxWidth="lg" sx={{ py: 3, display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'space-between',
            alignItems: 'center' }}>
            <Typography fontSize={14} color="text.secondary">
              SolarSaathi is a portfolio project by Muhammad Rehan Shakeel. Quotations are estimates, not offers.
            </Typography>
            <Stack direction="row" spacing={2}>
              <Link component={RouterLink} to="/staff" fontSize={14} color="text.secondary">{t('nav.staff')}</Link>
              <Link href="https://github.com/MuhammadRehanShakeel/solar-sizing-agent" fontSize={14} color="text.secondary">
                Source code
              </Link>
            </Stack>
          </Container>
        </Box>
      )}
    </Box>
  );
}
