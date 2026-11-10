import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { CssBaseline, ThemeProvider } from '@mui/material';
import '@fontsource/source-sans-3/400.css';
import '@fontsource/source-sans-3/600.css';
import '@fontsource/source-sans-3/700.css';
import '@fontsource/bricolage-grotesque/600.css';
import '@fontsource/bricolage-grotesque/700.css';
import '@fontsource/noto-nastaliq-urdu/400.css';
import '@fontsource/noto-nastaliq-urdu/600.css';
import App from './App';
import { store } from './store';
import theme from './theme';
import { LangProvider } from './services/i18n';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <LangProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </LangProvider>
      </ThemeProvider>
    </Provider>
  </React.StrictMode>
);

// PWA: "install" the website like an app (only in the built version, never while developing)
if (import.meta.env.PROD && 'serviceWorker' in navigator && !window.Capacitor) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}));
}
