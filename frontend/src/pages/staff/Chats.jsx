/** Chats.jsx - (staff) every recent conversation, also the ones that did not leave a phone number. */
import { useEffect, useState } from 'react';
import { Alert, Chip, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import api from '../../services/api';
import PageHeader from '../../components/PageHeader';
import ChatDialog from '../../components/ChatDialog';
import { colors } from '../../theme';
import { dateTime, LEAD_STATUS, OPTION_NAMES } from '../../utils/format';

export default function Chats() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(null);
  useEffect(() => { api.get('/admin/chats').then((r) => setRows(r.data)).catch((e) => setError(e.message)); }, []);

  return (
    <>
      <PageHeader title="Conversations" subtitle="Read what customers asked and how the AI answered (click a row)" />
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <TableContainer component={Paper} sx={{ border: `1px solid ${colors.line}` }}>
        <Table size="small">
          <TableHead>
            <TableRow><TableCell>Last active</TableCell><TableCell align="right">Messages</TableCell><TableCell>Quotation</TableCell><TableCell>Lead</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 && <TableRow><TableCell colSpan={4}><Typography color="text.secondary" sx={{ py: 2 }}>No conversations yet.</Typography></TableCell></TableRow>}
            {rows.map((c) => (
              <TableRow key={c.session_id} hover sx={{ cursor: 'pointer' }} onClick={() => setOpen(c.session_id)}>
                <TableCell>{dateTime(c.last_active)}</TableCell>
                <TableCell align="right">{c.turns}</TableCell>
                <TableCell>{c.recommended ? `${OPTION_NAMES[c.recommended]} ${c.recommended_kw} kW · ${(c.city || '').replace(/^\w/, (x) => x.toUpperCase())}` : '-'}</TableCell>
                <TableCell>{c.customer_name ? <Chip size="small" color={LEAD_STATUS[c.lead_status]?.color} label={`${c.customer_name} · ${LEAD_STATUS[c.lead_status]?.label}`} /> : '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <ChatDialog sessionId={open} onClose={() => setOpen(null)} />
    </>
  );
}
