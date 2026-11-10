/** Audit.jsx - (admin) who did what: logins, price changes, lead updates. */
import { useEffect, useState } from 'react';
import { Alert, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import api from '../../services/api';
import PageHeader from '../../components/PageHeader';
import { colors } from '../../theme';
import { dateTime } from '../../utils/format';

export default function Audit() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => { api.get('/admin/audit').then((r) => setRows(r.data)).catch((e) => setError(e.message)); }, []);
  return (
    <>
      <PageHeader title="Audit log" subtitle="The last 200 staff actions" />
      {error && <Alert severity="error">{error}</Alert>}
      <TableContainer component={Paper} sx={{ border: `1px solid ${colors.line}` }}>
        <Table size="small">
          <TableHead><TableRow><TableCell>When</TableCell><TableCell>Who</TableCell><TableCell>Action</TableCell><TableCell>Details</TableCell><TableCell>IP</TableCell></TableRow></TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.audit_id}>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>{dateTime(r.created_at)}</TableCell>
                <TableCell>{r.full_name || '-'}</TableCell>
                <TableCell>{r.action.replace(/_/g, ' ')}</TableCell>
                <TableCell>{[r.target, r.details].filter(Boolean).join(' · ')}</TableCell>
                <TableCell>{r.ip_address}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}
