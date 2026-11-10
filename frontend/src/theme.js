/**
 * theme.js - SolarSaathi look.
 *
 * The idea: a Pakistani home's day in two colours - SUN (when the panels work) and DUSK
 * (load-shedding). Everything else is calm: cool "bill-paper" background, deep teal ink,
 * leaf green for money saved. Change colours here and the whole app follows.
 */
import { createTheme } from '@mui/material/styles';

export const colors = {
  bg: '#eef3f0',          // cool bill-paper
  panel: '#ffffff',
  ink: '#10343b',         // deep teal ink
  sun: '#f2b300',         // daylight / the panels
  sunSoft: '#fdf3cf',
  dusk: '#4b3f86',        // load-shedding
  duskSoft: '#e9e5f6',
  green: '#1b7f55',       // money saved
  greenSoft: '#e1f1e8',
  sky: '#2c7da0',         // on-grid
  red: '#b4232f',
  muted: '#566c68',
  line: '#d4dfda',
  grid: '#9fb1ac',
};

export const DISPLAY = '"Bricolage Grotesque", "Source Sans 3", sans-serif';
export const URDU = '"Noto Nastaliq Urdu", serif';
export const OPTION_COLORS = { on_grid: colors.sky, hybrid: colors.sun, off_grid: colors.green };

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: colors.ink },
    secondary: { main: colors.sun, contrastText: colors.ink },
    success: { main: colors.green },
    error: { main: colors.red },
    background: { default: colors.bg, paper: colors.panel },
    text: { primary: colors.ink, secondary: colors.muted },
    divider: colors.line,
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif',
    fontSize: 15,
    h1: { fontFamily: DISPLAY, fontWeight: 700, letterSpacing: -1.5, lineHeight: 1.02 },
    h2: { fontFamily: DISPLAY, fontWeight: 700, letterSpacing: -1, lineHeight: 1.08 },
    h3: { fontFamily: DISPLAY, fontWeight: 700, letterSpacing: -0.6, lineHeight: 1.12 },
    h4: { fontFamily: DISPLAY, fontWeight: 700, letterSpacing: -0.4 },
    h5: { fontFamily: DISPLAY, fontWeight: 700, letterSpacing: -0.2 },
    h6: { fontFamily: DISPLAY, fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600, fontSize: 15 },
    body1: { lineHeight: 1.55 },
  },
  components: {
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } }, defaultProps: { elevation: 0 } },
    MuiCard: { defaultProps: { elevation: 0 } },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 999, paddingLeft: 18, paddingRight: 18 } },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
    MuiTableCell: { styleOverrides: { root: { borderColor: colors.line } } },
    MuiOutlinedInput: { styleOverrides: { root: { backgroundColor: '#fff' } } },
    MuiCssBaseline: {
      styleOverrides: {
        '*:focus-visible': { outline: `3px solid ${colors.sun}`, outlineOffset: 2 },
        '@media (prefers-reduced-motion: reduce)': { '*': { animation: 'none !important', transition: 'none !important' } },
        '[lang="ur"]': { fontFamily: URDU, lineHeight: 2.1 },
      },
    },
  },
});

export default theme;
