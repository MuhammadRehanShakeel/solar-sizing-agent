/** QuotePage.jsx - The shared quotation link (/quote/<token>): anyone with the link can view and download it. */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Alert, Container, LinearProgress, Typography } from '@mui/material';
import api from '../services/api';
import QuoteView from '../components/QuoteView';
import { dateTime } from '../utils/format';

export default function QuotePage() {
  const { token } = useParams();
  const [quote, setQuote] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    api.get(`/quotes/${token}`).then((r) => setQuote({ ...r.data, token })).catch((e) => setError(e.message));
  }, [token]);

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
      {error && <Alert severity="error">{error}</Alert>}
      {!quote && !error && <LinearProgress />}
      {quote && (
        <>
          <Typography variant="h2" sx={{ fontSize: { xs: 30, md: 40 } }}>
            Solar quotation Q-{String(quote.quote_id).padStart(5, '0')}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3, mt: 0.5 }}>
            {quote.customer_name ? `For ${quote.customer_name}, made ` : 'Made '}{dateTime(quote.created_at)}. Valid for 7 days.
          </Typography>
          <QuoteView quote={quote} />
        </>
      )}
    </Container>
  );
}
