/**
 * chatSlice.js - The customer's conversation with the agent.
 *
 * The session_id is kept in localStorage, so closing and reopening the app continues the same chat
 * (and the same quotation). "New chat" forgets it.
 */
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import api, { storage } from '../services/api';

const KEY = 'ss_session';

export const startChat = createAsyncThunk('chat/start', async ({ fresh = false } = {}) => {
  const old = fresh ? null : storage.get(KEY, localStorage);
  if (old) {
    try {
      return (await api.get(`/chat/${old}`)).data;          // continue the earlier chat
    } catch { /* expired or deleted: start a new one */ }
  }
  const status = (await api.post('/chat/start')).data;
  storage.set(KEY, status.session_id, localStorage);
  return { ...status, messages: [], quote: null, bill: null };
});

export const sendMessage = createAsyncThunk('chat/send', async (text, { getState, rejectWithValue }) => {
  try {
    return (await api.post('/chat', { session_id: getState().chat.sessionId, message: text })).data;
  } catch (e) {
    return rejectWithValue(e.message);
  }
});

export const uploadBill = createAsyncThunk('chat/bill', async (file, { getState, rejectWithValue }) => {
  const form = new FormData();
  form.append('session_id', getState().chat.sessionId);
  form.append('file', file);
  try {
    return (await api.post('/chat/bill', form)).data;
  } catch (e) {
    return rejectWithValue(e.message);
  }
});

export const confirmBill = createAsyncThunk('chat/confirmBill', async ({ units, sanctioned }, { getState, rejectWithValue }) => {
  try {
    return (await api.post('/chat/bill/confirm', { session_id: getState().chat.sessionId, monthly_units: units,
      sanctioned_load_kw: sanctioned || null })).data;
  } catch (e) {
    return rejectWithValue(e.message);
  }
});

export const shareLocation = createAsyncThunk('chat/location', async ({ lat, lon }, { getState, rejectWithValue }) => {
  try {
    return (await api.post('/chat/location', { session_id: getState().chat.sessionId, lat, lon })).data;
  } catch (e) {
    return rejectWithValue(e.message);
  }
});

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    sessionId: null, messages: [], quote: null, bill: null, sending: false, error: null, ready: false, location: null,
    features: { ai_ready: false, bill_reading: false, voice: false, installer: '' },
    speak: storage.get('ss_speak', localStorage) === '1',
  },
  reducers: {
    setQuote(state, action) { state.quote = action.payload; },
    toggleSpeak(state) {
      state.speak = !state.speak;
      storage.set('ss_speak', state.speak ? '1' : '0', localStorage);
    },
    clearError(state) { state.error = null; },
    setError(state, action) { state.error = action.payload; },
  },
  extraReducers: (builder) => {
    builder
      .addCase(startChat.fulfilled, (state, { payload }) => {
        state.sessionId = payload.session_id;
        state.messages = (payload.messages || []).filter((m) => m.role !== 'event');
        state.quote = payload.quote;
        state.bill = payload.bill;
        state.location = null;
        state.features = { ai_ready: payload.ai_ready, bill_reading: payload.bill_reading, voice: payload.voice,
          installer: payload.installer };
        state.ready = true;
        state.error = null;
      })
      .addCase(startChat.rejected, (state, action) => { state.error = action.error.message; state.ready = true; })
      .addCase(sendMessage.pending, (state, action) => {
        state.messages.push({ role: 'user', content: action.meta.arg });
        state.sending = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, { payload }) => {
        state.sending = false;
        state.messages.push({ role: 'assistant', content: payload.reply, fresh: true });
        if (payload.quote) state.quote = payload.quote;
      })
      .addCase(sendMessage.rejected, (state, action) => { state.sending = false; state.error = action.payload; })
      .addCase(uploadBill.pending, (state) => {
        state.messages.push({ role: 'user', content: '📄 Bill photo uploaded' });
        state.sending = true;
        state.error = null;
      })
      .addCase(uploadBill.fulfilled, (state, { payload }) => {
        state.sending = false;
        state.bill = payload.bill;                       // shown as a card to check before the AI continues
      })
      .addCase(uploadBill.rejected, (state, action) => { state.sending = false; state.error = action.payload; })
      .addCase(confirmBill.pending, (state, action) => {
        state.messages.push({ role: 'user', content: `Bill checked: ${action.meta.arg.units.length} months, average ${
          Math.round(action.meta.arg.units.reduce((a, b) => a + b, 0) / action.meta.arg.units.length)} units` });
        state.sending = true;
        state.error = null;
      })
      .addCase(confirmBill.fulfilled, (state, { payload }) => {
        state.sending = false;
        state.bill = payload.bill;
        state.messages.push({ role: 'assistant', content: payload.reply, fresh: true });
        if (payload.quote) state.quote = payload.quote;
      })
      .addCase(confirmBill.rejected, (state, action) => { state.sending = false; state.error = action.payload; })
      .addCase(shareLocation.fulfilled, (state, { payload }) => { state.location = payload; })
      .addCase(shareLocation.rejected, (state, action) => { state.error = action.payload; });
  },
});

export const { setQuote, toggleSpeak, clearError, setError } = chatSlice.actions;
export default chatSlice.reducer;
