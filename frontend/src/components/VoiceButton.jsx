/**
 * VoiceButton.jsx - Tap to record, tap again to send (max 45 seconds).
 * The recording goes to /chat/voice (Whisper on Groq) and comes back as text.
 * Phones only allow the microphone on HTTPS pages or inside the Android app.
 */
import { useEffect, useRef, useState } from 'react';
import { CircularProgress, IconButton, Tooltip } from '@mui/material';
import MicIcon from '@mui/icons-material/MicNoneRounded';
import StopIcon from '@mui/icons-material/StopRounded';
import api from '../services/api';
import { colors } from '../theme';

const MAX_SECONDS = 45;
const supported = typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined';

export default function VoiceButton({ onText, onError, disabled }) {
  const [state, setState] = useState('idle');           // idle | recording | working
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef(null);
  const timer = useRef(null);

  useEffect(() => () => { clearInterval(timer.current); recorder.current?.stream.getTracks().forEach((t) => t.stop()); }, []);

  const stop = () => {
    clearInterval(timer.current);
    if (recorder.current?.state === 'recording') recorder.current.stop();
  };

  const start = async () => {
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      onError('Microphone blocked. Allow the microphone for this site (on a phone the page must be https).');
      return;
    }
    const type = ['audio/webm', 'audio/mp4', 'audio/ogg'].find((t) => MediaRecorder.isTypeSupported?.(t)) || '';
    const rec = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
    const chunks = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      setState('working');
      const blob = new Blob(chunks, { type: (rec.mimeType || 'audio/webm').split(';')[0] });
      const form = new FormData();
      form.append('audio', blob, `voice.${blob.type.split('/')[1] || 'webm'}`);
      try {
        const { data } = await api.post('/chat/voice', form);
        onText(data.text);
      } catch (e) {
        onError(e.message);
      }
      setState('idle');
    };
    recorder.current = rec;
    rec.start();
    setSeconds(0);
    setState('recording');
    timer.current = setInterval(() => setSeconds((s) => {
      if (s + 1 >= MAX_SECONDS) stop();
      return s + 1;
    }), 1000);
  };

  if (!supported) return null;
  const title = state === 'recording' ? `Recording ${seconds}s - tap to send` : 'Speak (English / Urdu)';
  return (
    <Tooltip title={title}>
      <span>
        <IconButton disabled={disabled || state === 'working'} onClick={state === 'recording' ? stop : start}
          aria-label={title}
          sx={{ bgcolor: state === 'recording' ? colors.red : colors.sunSoft, color: state === 'recording' ? '#fff' : colors.ink,
            '&:hover': { bgcolor: state === 'recording' ? colors.red : '#ffe9b8' },
            animation: state === 'recording' ? 'pulse 1.2s infinite' : 'none',
            '@keyframes pulse': { '0%,100%': { boxShadow: '0 0 0 0 rgba(220,38,38,.5)' }, '50%': { boxShadow: '0 0 0 8px rgba(220,38,38,0)' } } }}>
          {state === 'working' ? <CircularProgress size={22} /> : state === 'recording' ? <StopIcon /> : <MicIcon />}
        </IconButton>
      </span>
    </Tooltip>
  );
}
