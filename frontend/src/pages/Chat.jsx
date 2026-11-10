/**
 * Chat.jsx - The AI advisor: type, speak or upload a bill photo. The quotation appears on the right
 * (on a phone: in the "Quotation" tab). What was read from a bill is shown to check before the AI uses it.
 */
import { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert, Badge, Box, Button, Chip, CircularProgress, IconButton, Stack, Tab, Tabs, TextField, Tooltip, Typography,
  useMediaQuery,
} from '@mui/material';
import SendIcon from '@mui/icons-material/SendRounded';
import ReceiptIcon from '@mui/icons-material/ReceiptLongRounded';
import VolumeUpIcon from '@mui/icons-material/VolumeUpRounded';
import VolumeOffIcon from '@mui/icons-material/VolumeOffRounded';
import RestartIcon from '@mui/icons-material/RestartAltRounded';
import PlaceIcon from '@mui/icons-material/PlaceOutlined';
import {
  clearError, confirmBill, sendMessage, setError, shareLocation, startChat, toggleSpeak, uploadBill,
} from '../store/chatSlice';
import BillCheck from '../components/BillCheck';
import DayStrip from '../components/DayStrip';
import MessageText from '../components/MessageText';
import QuoteView from '../components/QuoteView';
import VoiceButton from '../components/VoiceButton';
import { canSpeak, speak, stopSpeaking } from '../services/speech';
import { colors, DISPLAY } from '../theme';

const WELCOME = `Assalam-o-Alaikum! I'm **SolarSaathi**. I'll work out the right solar system for your home: size, price, your new bill and payback.

Fastest way: tap **Bill** and send a photo of your electricity bill. Or tell me your monthly units or bill amount, your city, and when your light goes.
Roman Urdu ya Urdu mein likhein, ya 🎤 dabakar bolein.`;

const SUGGESTIONS = [
  'Bill 25,000 aata hai, Rawalpindi. Hafte mein ek dafa 9 se 2 baje light jati hai',
  'My house uses 450 units a month in Lahore, load-shedding 2 hours every night',
  'I want to leave WAPDA completely. 300 units, Islamabad',
  'Is net metering still available?',
];

function Bubble({ role, children }) {
  const mine = role === 'user';
  return (
    <Stack direction="row" justifyContent={mine ? 'flex-end' : 'flex-start'} sx={{ mb: 1.5 }}>
      <Box sx={{ maxWidth: '86%', px: 1.75, py: 1.1, borderRadius: 2.5, bgcolor: mine ? colors.ink : '#fff',
        color: mine ? '#fff' : colors.ink, border: mine ? 'none' : `1px solid ${colors.line}`, wordBreak: 'break-word',
        borderBottomRightRadius: mine ? 4 : undefined, borderBottomLeftRadius: mine ? undefined : 4 }}>
        {children}
      </Box>
    </Stack>
  );
}

export default function Chat() {
  const dispatch = useDispatch();
  const { messages, quote, bill, sending, error, ready, features, speak: speakOn, location } = useSelector((s) => s.chat);
  const [text, setText] = useState('');
  const [tab, setTab] = useState('chat');
  const [seenQuote, setSeenQuote] = useState(null);
  const wide = useMediaQuery('(min-width:1000px)');
  const bottom = useRef(null);
  const fileInput = useRef(null);

  useEffect(() => { if (!ready) dispatch(startChat()); }, [dispatch, ready]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages.length, sending, tab, bill]);
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (speakOn && last?.role === 'assistant' && last.fresh) speak(last.content);
  }, [messages, speakOn]);

  const send = (value) => {
    const message = (value ?? text).trim();
    if (!message || sending) return;
    stopSpeaking();
    dispatch(sendMessage(message));
    setText('');
  };
  const pickBill = (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (file) dispatch(uploadBill(file));
  };
  const locate = () => {
    if (!navigator.geolocation) { dispatch(setError('This browser cannot share a location.')); return; }
    navigator.geolocation.getCurrentPosition(
      (p) => dispatch(shareLocation({ lat: p.coords.latitude, lon: p.coords.longitude })),
      () => dispatch(setError('Location not shared. Your city average will be used.')), { timeout: 10000 });
  };

  const newQuote = quote && quote.token !== seenQuote;
  const outage = quote?.result?.inputs?.outage;
  const quotePanel = quote ? <QuoteView quote={quote} compact /> : (
    <Box sx={{ p: 3, bgcolor: '#fff', borderRadius: 4, border: `1px solid ${colors.line}` }}>
      <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 22 }}>Your quotation appears here</Typography>
      <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 460 }}>
        Three systems compared, your bill if you keep or leave WAPDA, packages, instalments and a PDF.
      </Typography>
      <Box sx={{ mt: 3, opacity: 0.85 }}><DayStrip start={outage?.start_hour ?? 21} end={outage?.end_hour ?? 23} /></Box>
      <Typography fontSize={13} color="text.secondary" sx={{ mt: 1 }}>
        Tell the advisor when your light goes; it changes which system is best.
      </Typography>
      <Button component={RouterLink} to="/calculator" sx={{ mt: 2 }}>Prefer a form? Use the calculator</Button>
    </Box>
  );

  const chatPanel = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: wide ? 'calc(100vh - 110px)' : 'calc(100dvh - 160px)',
      bgcolor: '#fff', borderRadius: 4, border: `1px solid ${colors.line}`, overflow: 'hidden' }}>
      <Stack direction="row" alignItems="center" sx={{ px: 2, py: 1, borderBottom: `1px solid ${colors.line}` }}>
        <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, flex: 1 }}>AI solar advisor</Typography>
        <Tooltip title={location ? location.source : 'Use my exact location for NASA sunlight data'}>
          <span>
            <IconButton onClick={locate} aria-label="Use my location" color={location ? 'success' : 'default'}>
              <PlaceIcon />
            </IconButton>
          </span>
        </Tooltip>
        {canSpeak && (
          <Tooltip title={speakOn ? 'Stop reading answers aloud' : 'Read answers aloud'}>
            <IconButton onClick={() => { stopSpeaking(); dispatch(toggleSpeak()); }} aria-label="Read answers aloud">
              {speakOn ? <VolumeUpIcon sx={{ color: colors.sun }} /> : <VolumeOffIcon />}
            </IconButton>
          </Tooltip>
        )}
        <Tooltip title="Start again">
          <IconButton onClick={() => { stopSpeaking(); dispatch(startChat({ fresh: true })); setTab('chat'); }} aria-label="Start again">
            <RestartIcon />
          </IconButton>
        </Tooltip>
      </Stack>
      <Box sx={{ flex: 1, overflowY: 'auto', p: 2, bgcolor: colors.bg }}>
        {!features.ai_ready && ready && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            The AI advisor is switched off right now. The <RouterLink to="/calculator">calculator</RouterLink> gives the same answer.
          </Alert>
        )}
        <Bubble role="assistant"><MessageText text={WELCOME} /></Bubble>
        {messages.length === 0 && !bill && (
          <Stack sx={{ gap: 1, mb: 2 }}>
            {SUGGESTIONS.map((s) => (
              <Chip key={s} label={s} variant="outlined" onClick={() => send(s)}
                sx={{ bgcolor: '#fff', justifyContent: 'flex-start', height: 'auto', py: 0.75,
                  '& .MuiChip-label': { whiteSpace: 'normal' } }} />
            ))}
          </Stack>
        )}
        {messages.map((m, i) => (
          <Bubble key={i} role={m.role}>
            {m.role === 'user' ? <Typography fontSize={15} sx={{ whiteSpace: 'pre-wrap' }}>{m.content}</Typography>
              : <MessageText text={m.content} />}
          </Bubble>
        ))}
        {bill && bill.confirmed === false && !sending && (
          <BillCheck bill={bill} busy={sending} onConfirm={(v) => dispatch(confirmBill(v))} />
        )}
        {sending && (
          <Bubble role="assistant">
            <Stack direction="row" spacing={1} alignItems="center">
              <CircularProgress size={16} sx={{ color: colors.sun }} />
              <Typography fontSize={14} color="text.secondary">Working it out…</Typography>
            </Stack>
          </Bubble>
        )}
        {quote && !wide && newQuote && (
          <Button fullWidth variant="contained" color="secondary" onClick={() => { setTab('quote'); setSeenQuote(quote.token); }}>
            See your quotation
          </Button>
        )}
        <div ref={bottom} />
      </Box>
      {error && <Alert severity="error" onClose={() => dispatch(clearError())} sx={{ borderRadius: 0 }}>{error}</Alert>}
      <Box component="form" onSubmit={(e) => { e.preventDefault(); send(); }}
        sx={{ display: 'flex', gap: 1, alignItems: 'center', p: 1.25, borderTop: `1px solid ${colors.line}` }}>
        <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden onChange={pickBill} />
        <Tooltip title={features.bill_reading ? 'Send a photo of your electricity bill' : 'Bill reading is switched off'}>
          <span>
            <Button variant="outlined" startIcon={<ReceiptIcon />} disabled={sending || !features.bill_reading}
              onClick={() => fileInput.current?.click()} sx={{ whiteSpace: 'nowrap', height: 40 }}>Bill</Button>
          </span>
        </Tooltip>
        <TextField fullWidth size="small" placeholder="Type in English, Roman Urdu or اردو" value={text} disabled={!ready}
          onChange={(e) => setText(e.target.value)} inputProps={{ maxLength: 1000, 'aria-label': 'Message' }}
          multiline maxRows={4} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} />
        {features.voice && <VoiceButton disabled={sending} onText={(t) => send(t)} onError={(m) => dispatch(setError(m))} />}
        <IconButton type="submit" disabled={sending || !text.trim()} aria-label="Send"
          sx={{ bgcolor: colors.ink, color: '#fff', '&:hover': { bgcolor: '#1b4a53' }, '&.Mui-disabled': { bgcolor: colors.line } }}>
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  );

  return wide ? (
    <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 5fr) 7fr', gap: 2, p: 2, maxWidth: 1500, mx: 'auto', width: '100%' }}>
      {chatPanel}
      <Box sx={{ height: 'calc(100vh - 110px)', overflowY: 'auto', pr: 0.5 }}>{quotePanel}</Box>
    </Box>
  ) : (
    <Box sx={{ p: 1 }}>
      <Tabs value={tab} onChange={(e, v) => { setTab(v); if (v === 'quote' && quote) setSeenQuote(quote.token); }} variant="fullWidth"
        sx={{ mb: 1 }}>
        <Tab value="chat" label="Chat" />
        <Tab value="quote" label={<Badge color="secondary" variant="dot" invisible={!newQuote}>Quotation</Badge>} />
      </Tabs>
      {tab === 'chat' ? chatPanel : <Box sx={{ pb: 3 }}>{quotePanel}</Box>}
    </Box>
  );
}
