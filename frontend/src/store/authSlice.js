/**
 * authSlice.js - Which STAFF member is logged in (customers never log in).
 * Kept in sessionStorage: gone when the tab closes, safer on a shared shop computer.
 */
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import api, { storage } from '../services/api';

export const login = createAsyncThunk('auth/login', async ({ email, password }, { rejectWithValue }) => {
  try {
    return (await api.post('/auth/login', { email, password })).data;
  } catch (e) {
    return rejectWithValue(e.message);
  }
});

function save(state, payload) {
  state.user = payload.user;
  state.token = payload.access_token;
  storage.set('ss_token', payload.access_token);
  storage.set('ss_user', JSON.stringify(payload.user));
}

let saved = null;
try { saved = JSON.parse(storage.get('ss_user') || 'null'); } catch { saved = null; }

const authSlice = createSlice({
  name: 'auth',
  initialState: { user: saved, token: storage.get('ss_token'), loading: false, error: null },
  reducers: {
    setSession(state, action) { save(state, action.payload); },
    logout(state) {
      storage.remove('ss_token');
      storage.remove('ss_user');
      state.user = null;
      state.token = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => { state.loading = true; state.error = null; })
      .addCase(login.fulfilled, (state, action) => { state.loading = false; save(state, action.payload); })
      .addCase(login.rejected, (state, action) => { state.loading = false; state.error = action.payload; });
  },
});

export const { logout, setSession } = authSlice.actions;
export default authSlice.reducer;
