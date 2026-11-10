/**
 * BillCheck.jsx - "This is what we read from your bill. Is it right?"
 * The customer can fix any month before the AI uses the numbers.
 */
import { useEffect, useState } from 'react';
import { Box, Button, Grid, InputAdornment, Stack, TextField, Typography } from '@mui/material';
import { colors, DISPLAY } from '../theme';

export default function BillCheck({ bill, onConfirm, busy }) {
  const history = bill.history?.length ? bill.history : bill.monthly_units.map((u, i) => ({ month: `Month ${i + 1}`, units: u }));
  const [units, setUnits] = useState(history.map((h) => String(h.units)));
  const [load, setLoad] = useState(bill.sanctioned_load_kw ? String(bill.sanctioned_load_kw) : '');
  useEffect(() => setUnits(history.map((h) => String(h.units))), [bill]);          // eslint-disable-line

  const numbers = units.map((u) => Number(u)).filter((u) => u > 0 && u <= 50000);
  const average = numbers.length ? Math.round(numbers.reduce((a, b) => a + b, 0) / numbers.length) : 0;
  return (
    <Box sx={{ p: 2, borderRadius: 3, bgcolor: '#fff', border: `2px solid ${colors.sun}`, mb: 1.5 }}>
      <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 18 }}>Please check what I read from your bill</Typography>
      <Typography fontSize={14} color="text.secondary" sx={{ mb: 1.5 }}>
        {bill.disco ? `${bill.disco} bill. ` : ''}Fix any month that is wrong, then confirm. The photo itself was not saved.
      </Typography>
      <Grid container spacing={1}>
        {history.map((h, i) => (
          <Grid item xs={4} sm={3} key={`${h.month}-${i}`}>
            <TextField size="small" fullWidth label={h.month} value={units[i] ?? ''} inputProps={{ inputMode: 'numeric' }}
              onChange={(e) => setUnits(units.map((u, j) => (j === i ? e.target.value.replace(/\D/g, '') : u)))} />
          </Grid>
        ))}
      </Grid>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems={{ sm: 'center' }} sx={{ mt: 1.5 }}>
        <TextField size="small" label="Sanctioned load" value={load} sx={{ width: { sm: 170 } }}
          onChange={(e) => setLoad(e.target.value.replace(/[^\d.]/g, ''))}
          InputProps={{ endAdornment: <InputAdornment position="end">kW</InputAdornment> }} />
        <Typography sx={{ flex: 1 }} fontSize={15}>Average: <b>{average} units</b> a month</Typography>
        <Button variant="contained" disabled={busy || !numbers.length}
          onClick={() => onConfirm({ units: numbers, sanctioned: Number(load) || null })}>
          These are right
        </Button>
      </Stack>
    </Box>
  );
}
