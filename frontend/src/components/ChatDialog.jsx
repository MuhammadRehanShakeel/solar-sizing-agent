/** ChatDialog.jsx - (staff) read one customer conversation and open its quotation. */
import { useEffect, useState } from 'react';
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, Typography } from '@mui/material';
import api from '../services/api';
import MessageText from './MessageText';
import { colors } from '../theme';
import { dateTime } from '../utils/format';

export default function ChatDialog({ sessionId, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!sessionId) return;
    setData(null);
    api.get(`/admin/chats/${sessionId}`).then((r) => setData(r.data)).catch((e) => setError(e.message));
  }, [sessionId]);

  return (
    <Dialog open={Boolean(sessionId)} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Conversation</DialogTitle>
      <DialogContent dividers sx={{ bgcolor: '#fdfbf7' }}>
        {error && <Alert severity="error">{error}</Alert>}
        {!data && !error && <LinearProgress />}
        {data?.messages.map((m) => (
          <Box key={m.message_id} sx={{ mb: 1.5, ml: m.role === 'user' ? 6 : 0, mr: m.role === 'user' ? 0 : 6 }}>
            <Typography fontSize={11.5} color="text.secondary">
              {m.role === 'user' ? 'Customer' : 'SolarSaathi'} · {dateTime(m.created_at)}
              {m.model && <Chip size="small" label={m.model} sx={{ ml: 1, height: 18, fontSize: 10.5 }} />}
              {m.tools_used && <Chip size="small" variant="outlined" label={`tools: ${m.tools_used}`} sx={{ ml: 0.5, height: 18, fontSize: 10.5 }} />}
            </Typography>
            <Box sx={{ p: 1.25, borderRadius: 2, bgcolor: m.role === 'user' ? colors.ink : '#fff', color: m.role === 'user' ? '#fff' : colors.ink,
              border: `1px solid ${colors.line}` }}>
              {m.role === 'user' ? <Typography fontSize={14}>{m.content}</Typography> : <MessageText text={m.content} />}
            </Box>
          </Box>
        ))}
        {data && !data.messages.length && <Typography color="text.secondary">No messages.</Typography>}
      </DialogContent>
      <DialogActions>
        {data?.quote && <Button href={`/quote/${data.quote.public_token}`} target="_blank">Open quotation Q-{String(data.quote.quote_id).padStart(5, '0')}</Button>}
        <Button variant="contained" onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
