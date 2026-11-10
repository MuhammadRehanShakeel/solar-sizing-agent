/** Leads.jsx - (staff) customers who asked for a call-back: call, update the status, read the chat. */
import { useEffect, useState } from 'react';
import {
  Alert, Button, Chip, IconButton, MenuItem, Paper, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Tabs, TextField, Tooltip, Typography,
} from '@mui/material';
import PhoneIcon from '@mui/icons-material/PhoneRounded';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import api from '../../services/api';
import PageHeader from '../../components/PageHeader';
import ChatDialog from '../../components/ChatDialog';
import { colors } from '../../theme';
import { dateTime, lakh, LEAD_STATUS, OPTION_NAMES } from '../../utils/format';

const whatsapp = (phone) => `https://wa.me/92${phone.replace(/^(\+92|0092|0)/, '')}`;

export default function Leads() {
  const [status, setStatus] = useState('');
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [chat, setChat] = useState(null);
  const [notes, setNotes] = useState({});

  const load = () => api.get('/admin/leads', { params: { status: status || undefined } }).then((r) => setRows(r.data)).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [status]);

  const update = async (lead, body) => {
    setError('');
    try { await api.put(`/admin/leads/${lead.lead_id}`, body); load(); } catch (e) { setError(e.message); }
  };

  return (
    <>
      <PageHeader title="Leads" subtitle="Customers who agreed to a call-back. Call within one working day." />
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Tabs value={status} onChange={(e, v) => setStatus(v)} variant="scrollable" sx={{ mb: 1.5 }}>
        <Tab value="" label="All" />
        {Object.entries(LEAD_STATUS).map(([k, s]) => <Tab key={k} value={k} label={s.label} />)}
      </Tabs>
      <TableContainer component={Paper} sx={{ border: `1px solid ${colors.line}` }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Customer</TableCell><TableCell>Phone</TableCell><TableCell>System</TableCell>
              <TableCell>Status</TableCell><TableCell sx={{ minWidth: 200 }}>Notes</TableCell><TableCell>Created</TableCell><TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={7}><Typography color="text.secondary" sx={{ py: 2 }}>No leads here yet.</Typography></TableCell></TableRow>}
            {rows.map((l) => (
              <TableRow key={l.lead_id} hover>
                <TableCell>
                  <Typography fontWeight={600} fontSize={14}>{l.customer_name}</Typography>
                  <Typography fontSize={12} color="text.secondary">{(l.city || '').replace(/^\w/, (c) => c.toUpperCase())} · {l.average_units} units/month</Typography>
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  {l.phone}
                  <Tooltip title="Call"><IconButton size="small" href={`tel:${l.phone}`}><PhoneIcon fontSize="small" /></IconButton></Tooltip>
                  <Tooltip title="WhatsApp"><IconButton size="small" color="success" href={whatsapp(l.phone)} target="_blank"><WhatsAppIcon fontSize="small" /></IconButton></Tooltip>
                </TableCell>
                <TableCell>
                  <Chip size="small" label={OPTION_NAMES[l.preferred_option] || l.preferred_option} sx={{ mb: 0.3 }} />
                  <Typography fontSize={12} color="text.secondary">{l.recommended_kw} kW · {lakh(l.recommended_cost)}</Typography>
                </TableCell>
                <TableCell>
                  <TextField select size="small" value={l.status} onChange={(e) => update(l, { status: e.target.value })} sx={{ minWidth: 130 }}>
                    {Object.entries(LEAD_STATUS).map(([k, s]) => <MenuItem key={k} value={k}>{s.label}</MenuItem>)}
                  </TextField>
                </TableCell>
                <TableCell>
                  <TextField size="small" fullWidth placeholder="e.g. site visit Saturday" value={notes[l.lead_id] ?? l.notes ?? ''}
                    onChange={(e) => setNotes({ ...notes, [l.lead_id]: e.target.value })}
                    onBlur={() => notes[l.lead_id] !== undefined && notes[l.lead_id] !== (l.notes ?? '') && update(l, { notes: notes[l.lead_id] })} />
                  {l.updated_by_name && <Typography fontSize={11} color="text.secondary">by {l.updated_by_name}</Typography>}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>{dateTime(l.created_at)}</TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  <Button size="small" onClick={() => setChat(l.session_id)}>Chat</Button>
                  {l.public_token && <Button size="small" href={`/quote/${l.public_token}`} target="_blank">Quote</Button>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <ChatDialog sessionId={chat} onClose={() => setChat(null)} />
    </>
  );
}
