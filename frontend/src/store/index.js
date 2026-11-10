import { configureStore } from '@reduxjs/toolkit';
import auth from './authSlice';
import chat from './chatSlice';

export const store = configureStore({ reducer: { auth, chat } });
