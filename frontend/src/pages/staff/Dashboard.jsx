/** Dashboard.jsx - (staff) chats, quotes, leads and sales at a glance. */
import { useEffect, useState } from 'react';
import { Alert, Grid, LinearProgress, Paper, ToggleButton, ToggleButtonGroup, Typography, Box } from '@mui/material';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from 'recharts';
import api from '../../services/api';
import PageHeader from '../../components/PageHeader';
import { colors, OPTION_COLORS, DISPLAY } from '../../theme';
import { lakh, LEAD_STATUS, OPTION_NAMES } from '../../utils/format';

function Stat({ label, value, hint, color }) {
  return (
    <Paper sx={{ p: 2.2, height: '100%', border: `1px solid ${colors.line}` }}>
      <Typography fontSize={12.5} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.6 }}>{label}</Typography>
      <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 30, color: color || colors.ink }}>{value}</Typography>
      {hint && <Typography fontSize={12.5} color="text.secondary">{hint}</Typography>}
    </Paper>
  );
}

function Panel({ title, children, height = 240 }) {
  return (
    <Paper sx={{ p: 2, border: `1px solid ${colors.line}` }}>
      <Typography fontWeight={700} sx={{ mb: 1 }}>{title}</Typography>
      <Box sx={{ height }}>{children}</Box>
    </Paper>
  );
}

export default function Dashboard() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { api.get('/admin/stats', { params: { days } }).then((r) => setData(r.data)).catch((e) => setError(e.message)); }, [days]);

  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return <LinearProgress />;
  const options = data.by_option.map((o) => ({ name: OPTION_NAMES[o.name] || o.name, value: o.n, key: o.name }));
  const funnel = Object.keys(LEAD_STATUS).map((k) => ({ name: LEAD_STATUS[k].label, n: data.leads_by_status.find((x) => x.name === k)?.n || 0 }));

  return (
    <>
      <PageHeader title="Dashboard" subtitle="What the AI advisor did for the business"
        action={(
          <ToggleButtonGroup size="small" exclusive value={days} onChange={(e, v) => v && setDays(v)}>
            {[7, 30, 90].map((d) => <ToggleButton key={d} value={d}>{d} days</ToggleButton>)}
          </ToggleButtonGroup>
        )} />
      <Grid container spacing={2}>
        <Grid item xs={6} md={3}><Stat label="Conversations" value={data.chats} hint={`${data.chat_to_lead_percent}% became leads`} /></Grid>
        <Grid item xs={6} md={3}><Stat label="Quotations" value={data.quotes} hint={`average ${data.average_kw} kW`} color={colors.sun} /></Grid>
        <Grid item xs={6} md={3}><Stat label="Leads" value={data.leads} hint={`${data.won} won, ${data.surveys ?? 0} site surveys booked`} color={colors.green} /></Grid>
        <Grid item xs={6} md={3}><Stat label="Value quoted" value={lakh(data.quoted_value)} hint="recommended systems" /></Grid>
        <Grid item xs={12} md={8}>
          <Panel title="Quotations per day">
            <ResponsiveContainer>
              <BarChart data={data.by_day.map((d) => ({ ...d, day: d.day.slice(5) }))}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={colors.line} />
                <XAxis dataKey="day" fontSize={11} /><YAxis allowDecimals={false} fontSize={11} /><Tooltip />
                <Bar dataKey="n" name="Quotations" fill={colors.sun} isAnimationActive={false} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </Grid>
        <Grid item xs={12} md={4}>
          <Panel title="Recommended systems">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={options} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} isAnimationActive={false}>
                  {options.map((o) => <Cell key={o.key} fill={OPTION_COLORS[o.key] || colors.grid} />)}
                </Pie>
                <Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </Panel>
        </Grid>
        <Grid item xs={12} md={6}>
          <Panel title="Lead pipeline">
            <ResponsiveContainer>
              <BarChart data={funnel} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" allowDecimals={false} fontSize={11} /><YAxis type="category" dataKey="name" fontSize={12} width={80} /><Tooltip />
                <Bar dataKey="n" name="Leads" fill={colors.ink} isAnimationActive={false} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </Grid>
        <Grid item xs={12} md={6}>
          <Panel title="Quotations by city">
            <ResponsiveContainer>
              <BarChart data={data.by_city.map((c) => ({ ...c, name: c.name.replace(/^\w/, (x) => x.toUpperCase()) }))}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={colors.line} />
                <XAxis dataKey="name" fontSize={11} /><YAxis allowDecimals={false} fontSize={11} /><Tooltip />
                <Bar dataKey="n" name="Quotations" fill={colors.sky} isAnimationActive={false} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </Grid>
        <Grid item xs={12}>
          <Typography fontSize={12.5} color="text.secondary">
            Answers by model: {data.models.map((m) => `${m.name} (${m.n})`).join(' · ') || 'none yet'}
          </Typography>
        </Grid>
      </Grid>
    </>
  );
}
