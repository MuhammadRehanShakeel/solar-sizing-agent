/** Prices.jsx - The price list every quotation uses. Admins edit; sales people can only read. */
import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { Alert, Box, Button, Grid, InputAdornment, LinearProgress, Paper, TextField, Typography } from '@mui/material';
import api from '../../services/api';
import PageHeader from '../../components/PageHeader';
import { colors } from '../../theme';

export default function Prices() {
  const isAdmin = useSelector((s) => s.auth.user.role === 'admin');
  const [rows, setRows] = useState(null);
  const [edits, setEdits] = useState({});
  const [message, setMessage] = useState(null);
  useEffect(() => { api.get('/admin/prices').then((r) => setRows(r.data)).catch((e) => setMessage({ type: 'error', text: e.message })); }, []);

  const save = async () => {
    const prices = Object.fromEntries(Object.entries(edits).map(([k, v]) => [k, Number(v)]));
    try {
      setRows((await api.put('/admin/prices', { prices })).data);
      setEdits({});
      setMessage({ type: 'success', text: 'Saved. Every new quotation uses these prices.' });
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    }
  };

  if (!rows) return message ? <Alert severity="error">{message.text}</Alert> : <LinearProgress />;
  const groups = [...new Set(rows.map((r) => r.group))];
  return (
    <>
      <PageHeader title="Prices" subtitle="Market rates used by the AI advisor and the calculator"
        action={isAdmin && <Button variant="contained" disabled={!Object.keys(edits).length} onClick={save}>Save changes</Button>} />
      {message && <Alert severity={message.type} sx={{ mb: 2 }} onClose={() => setMessage(null)}>{message.text}</Alert>}
      {!isAdmin && <Alert severity="info" sx={{ mb: 2 }}>Only an admin can change prices.</Alert>}
      <Grid container spacing={2}>
        {groups.map((g) => (
          <Grid item xs={12} md={6} key={g}>
            <Paper sx={{ p: 2, border: `1px solid ${colors.line}` }}>
              <Typography fontWeight={700} sx={{ mb: 1.5 }}>{g}</Typography>
              {rows.filter((r) => r.group === g).map((r) => (
                <Box key={r.key} sx={{ mb: 1.5 }}>
                  <TextField fullWidth size="small" label={r.label} type="number" disabled={!isAdmin}
                    value={edits[r.key] ?? r.value} onChange={(e) => setEdits({ ...edits, [r.key]: e.target.value })}
                    InputProps={{ endAdornment: <InputAdornment position="end">{r.unit}</InputAdornment> }} />
                </Box>
              ))}
            </Paper>
          </Grid>
        ))}
      </Grid>
    </>
  );
}
