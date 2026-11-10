/** Login.jsx - Staff sign in (installer admin / sales). Customers never need this. */
import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Navigate, Link as RouterLink } from 'react-router-dom';
import { Alert, Box, Button, Link, Paper, TextField, Typography } from '@mui/material';
import { login } from '../../store/authSlice';
import Logo from '../../components/Logo';
import { colors } from '../../theme';

export default function Login() {
  const dispatch = useDispatch();
  const { user, loading, error } = useSelector((s) => s.auth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  if (user) return <Navigate to="/staff" replace />;

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2,
      background: `radial-gradient(circle at 20% 10%, ${colors.sunSoft}, ${colors.bg} 45%)` }}>
      <Paper component="form" onSubmit={(e) => { e.preventDefault(); dispatch(login({ email, password })); }}
        sx={{ p: 4, width: '100%', maxWidth: 380, border: `1px solid ${colors.line}` }}>
        <Logo />
        <Typography variant="h5" sx={{ mt: 3 }}>Staff sign in</Typography>
        <Typography color="text.secondary" fontSize={14} sx={{ mb: 2.5 }}>Leads, conversations and the price list.</Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <TextField label="Email" type="email" fullWidth required autoComplete="username" value={email}
          onChange={(e) => setEmail(e.target.value)} sx={{ mb: 2 }} />
        <TextField label="Password" type="password" fullWidth required autoComplete="current-password" value={password}
          onChange={(e) => setPassword(e.target.value)} sx={{ mb: 3 }} />
        <Button type="submit" variant="contained" size="large" fullWidth disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </Button>
        <Typography fontSize={13} sx={{ mt: 2.5, textAlign: 'center' }}>
          Looking for solar? <Link component={RouterLink} to="/">Chat with SolarSaathi</Link>
        </Typography>
      </Paper>
    </Box>
  );
}
