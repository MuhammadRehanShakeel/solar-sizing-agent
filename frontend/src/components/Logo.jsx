import { Box, Typography } from '@mui/material';
import { colors, DISPLAY } from '../theme';

export default function Logo({ small = false, light = false }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box component="img" src="/icon.svg" alt="" sx={{ width: small ? 30 : 38, height: small ? 30 : 38 }} />
      <Box>
        <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: small ? 19 : 23, lineHeight: 1,
          letterSpacing: -0.4, color: light ? '#fff' : colors.ink }}>
          SolarSaathi
        </Typography>
        {!small && (
          <Typography sx={{ fontSize: 12, color: light ? '#cbd5e1' : colors.muted }}>Solar advisor for Pakistani homes</Typography>
        )}
      </Box>
    </Box>
  );
}
