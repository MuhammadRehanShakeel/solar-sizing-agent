/** Surveys.jsx - (staff) site-survey bookings: confirm by phone, mark done, keep notes. */
import { useEffect, useState } from 'react';
import {
  Alert, Button, IconButton, MenuItem, Paper, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tabs,
  TextField, Tooltip, Typography,
} from '@mui/material';
import PhoneIcon from '@mui/icons-material/PhoneRounded';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import api from '../../services/api';
import PageHeader from '../../components/PageHeader';
import { colors } from '../../theme';
import { lakh, OPTION_NAMES } from '../../utils/format';

const STATUS = { requested: 'Requested', confirmed: 'Confirmed', done: 'Done', cancelled: 'Cancelled' };
const SLOT = { morning: '10 am - 1 pm', afternoon: '1 pm - 4 pm', evening: '4 pm - 7 pm' };
const whatsapp = (phone) => `https://wa.me/92${phone.replace(/^(\+92|0092|0)/, '')}`;

export default function Surveys() {
  const [status, setStatus] = useState('');
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [notes, setNotes] = useState({});

  const load = () => api.get('/admin/surveys', { params: { status: status || undefined } }).then((r) => setRows(r.data))
    .catch((e) => setError(e.message));
  useEffect(() => { load(); }, [status]);                                              // eslint-disable-line

  const update = async (row, body) => {
    setError('');
    try { await api.put(`/admin/surveys/${row.booking_id}`, body); load(); } catch (e) { setError(e.message); }
  };

  return (
    <>
      <PageHeader title="Site surveys" subtitle="Call to confirm the visit the day before. Requested visits come first." />
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Tabs value={status} onChange={(e, v) => setStatus(v)} variant="scrollable" sx={{ mb: 1.5 }}>
        <Tab value="" label="All" />
        {Object.entries(STATUS).map(([k, label]) => <Tab key={k} value={k} label={label} />)}
      </Tabs>
      <TableContainer component={Paper} sx={{ border: `1px solid ${colors.line}` }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>When</TableCell><TableCell>Customer</TableCell><TableCell>Area</TableCell><TableCell>System</TableCell>
              <TableCell>Status</TableCell><TableCell sx={{ minWidth: 200 }}>Notes</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={6}><Typography color="text.secondary" sx={{ py: 2 }}>
                No bookings yet. Customers book from their quotation or the website menu.</Typography></TableCell></TableRow>
            )}
            {rows.map((r) => (
              <TableRow key={r.booking_id} hover>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  <Typography fontWeight={700} fontSize={14}>
                    {new Date(r.preferred_date).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })}
                  </Typography>
                  <Typography fontSize={12.5} color="text.secondary">{SLOT[r.time_slot]}</Typography>
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  <Typography fontWeight={600} fontSize={14}>{r.customer_name}</Typography>
                  {r.phone}
                  <Tooltip title="Call"><IconButton size="small" href={`tel:${r.phone}`}><PhoneIcon fontSize="small" /></IconButton></Tooltip>
                  <Tooltip title="WhatsApp"><IconButton size="small" color="success" href={whatsapp(r.phone)} target="_blank">
                    <WhatsAppIcon fontSize="small" /></IconButton></Tooltip>
                </TableCell>
                <TableCell>{r.area}</TableCell>
                <TableCell>
                  {r.public_token ? (
                    <Button size="small" href={`/quote/${r.public_token}`} target="_blank" sx={{ px: 0 }}>
                      {OPTION_NAMES[r.recommended]} {r.recommended_kw} kW, {lakh(r.recommended_cost)}
                    </Button>
                  ) : <Typography fontSize={13} color="text.secondary">No quote</Typography>}
                </TableCell>
                <TableCell>
                  <TextField select size="small" value={r.status} onChange={(e) => update(r, { status: e.target.value })}
                    sx={{ minWidth: 130 }}>
                    {Object.entries(STATUS).map(([k, label]) => <MenuItem key={k} value={k}>{label}</MenuItem>)}
                  </TextField>
                </TableCell>
                <TableCell>
                  <TextField size="small" fullWidth placeholder="e.g. roof faces south, 2 floors" value={notes[r.booking_id] ?? r.notes ?? ''}
                    onChange={(e) => setNotes({ ...notes, [r.booking_id]: e.target.value })}
                    onBlur={() => notes[r.booking_id] !== undefined && notes[r.booking_id] !== (r.notes ?? '')
                      && update(r, { notes: notes[r.booking_id] })} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}
