/**
 * speech.js - The agent talks back using the browser's own voice (free, works offline).
 * Urdu script is read with an Urdu voice if the phone has one; English / Roman Urdu with an English voice.
 */
import { isUrdu } from '../utils/format';

export const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window;

function clean(text) {
  return (text || '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/[*#_`>]/g, '')
    .replace(/\bRs\b\.?/g, 'rupees')
    .replace(/\bkWh\b/g, 'kilowatt hours')
    .replace(/\bkW\b/g, 'kilowatt');
}

export function speak(text) {
  if (!canSpeak) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(clean(text));
  const urdu = isUrdu(text);
  const voices = window.speechSynthesis.getVoices();
  const voice = voices.find((v) => v.lang?.toLowerCase().startsWith(urdu ? 'ur' : 'en-in'))
    || voices.find((v) => v.lang?.toLowerCase().startsWith(urdu ? 'hi' : 'en'));
  if (voice) utterance.voice = voice;
  utterance.lang = voice?.lang || (urdu ? 'ur-PK' : 'en-US');
  utterance.rate = 1.0;
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking() {
  if (canSpeak) window.speechSynthesis.cancel();
}
