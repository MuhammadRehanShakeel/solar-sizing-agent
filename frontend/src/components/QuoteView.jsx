/**
 * QuoteView.jsx - The quotation. Order = the questions a customer asks:
 *   1. What should I buy, what does it cost, what will my bill be?      (summary)
 *   2. How do the three systems compare?                                 (compare table)
 *   3. What if I keep / leave WAPDA?                                      (bill in every situation)
 *   4. Will it work in my load-shedding?                                  (day strip)
 *   5. Month by month, packages, instalments, price breakdown, where the numbers come from.
 * Used in the advisor chat, the calculator and the shared quotation page.
 */
import { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert, Box, Button, Chip, Grid, Stack, Tab, Table, TableBody, TableCell, TableHead, TableRow, Tabs, Typography,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/DownloadRounded';
import ShareIcon from '@mui/icons-material/ShareRounded';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import EventIcon from '@mui/icons-material/EventAvailableRounded';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import DayStrip from './DayStrip';
import { downloadFile } from '../services/api';
import { colors, DISPLAY, OPTION_COLORS } from '../theme';
import { lakh, OPTION_HINT, OPTION_NAMES, rupees } from '../utils/format';

const KINDS = ['on_grid', 'hybrid', 'off_grid'];
const ITEMS = { panels: 'Solar panels', inverter: 'Inverter', batteries: 'Lithium batteries', structure: 'Mounting structure',
  installation: 'Wiring, protection & labour', net_billing: 'Green meter + DISCO approval', margin: 'Installer margin' };
const SCENARIO_SHORT = { net_billing: 'With net billing', no_export: 'Connected, no green meter',
  disconnected: 'WAPDA disconnected', wapda_backup: 'WAPDA as backup only' };

function Section({ title, children, aside, shot }) {
  return (
    <Box component="section" data-shot={shot} sx={{ mt: 3.5 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 1.25, gap: 2 }}>
        <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 20 }}>{title}</Typography>
        {aside}
      </Stack>
      {children}
    </Box>
  );
}

function Figure({ label, value, sub, color = colors.ink }) {
  return (
    <Box>
      <Typography fontSize={13.5} color="text.secondary">{label}</Typography>
      <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: { xs: 24, sm: 28 }, color, lineHeight: 1.15 }}>
        {value}
      </Typography>
      {sub && <Typography fontSize={13} color="text.secondary">{sub}</Typography>}
    </Box>
  );
}

function outageText(inputs) {
  const o = inputs.outage;
  if (o) return o.days_per_week ? o.text : 'no load-shedding';
  return inputs.outage_hours ? `${inputs.outage_hours} h a day` : 'no load-shedding';
}

export default function QuoteView({ quote, compact = false }) {
  const result = quote.result;
  const [kind, setKind] = useState(result.recommended);
  const [message, setMessage] = useState('');
  useEffect(() => setKind(result.recommended), [quote.token, result.recommended]);
  const option = result.options[kind];
  const best = result.options[result.recommended];
  const link = `${window.location.origin}/quote/${quote.token}`;
  const mainKey = option.main_scenario;
  const months = option.months.map((m) => ({ ...m, after: m.bills ? m.bills[mainKey] : m.bill_after }));
  const outage = result.inputs.outage;
  const city = result.inputs.city === 'other' ? 'Pakistan' : result.inputs.city.replace(/\b\w/g, (c) => c.toUpperCase());
  const billAfter = best.monthly_bill_after ?? (result.current_bill.total - best.monthly_saving);

  const share = async () => {
    const text = `My solar quotation: ${OPTION_NAMES[result.recommended]} ${best.system_kw} kW`;
    if (navigator.share) {
      try { await navigator.share({ title: 'Solar quotation', text, url: link }); return; } catch { /* closed */ }
    }
    try { await navigator.clipboard.writeText(link); setMessage('Link copied.'); } catch { setMessage(link); }
  };

  return (
    <Box>
      {/* 1. summary */}
      <Box sx={{ p: { xs: 2, sm: 3 }, borderRadius: 3, bgcolor: '#fff', border: `1px solid ${colors.line}`,
        borderTop: `6px solid ${OPTION_COLORS[result.recommended]}` }}>
        <Typography fontSize={14} color="text.secondary">
          {result.inputs.average_units} units a month in {city}, load-shedding: {outageText(result.inputs)}
        </Typography>
        <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: { xs: 26, sm: 32 }, mt: 0.5, lineHeight: 1.15 }}>
          {OPTION_NAMES[result.recommended]}, {best.system_kw} kW
          {best.battery_kwh ? ` with a ${best.battery_kwh} kWh battery` : ''}
        </Typography>
        <Typography sx={{ mt: 1, maxWidth: 720 }}>{result.reason}</Typography>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={6} sm={3}><Figure label="Price" value={lakh(best.cost.total)} /></Grid>
          <Grid item xs={6} sm={3}><Figure label="Your bill" value={rupees(billAfter)}
            sub={`now ${rupees(result.current_bill.total)}`} color={colors.green} /></Grid>
          <Grid item xs={6} sm={3}><Figure label="Saving a month" value={rupees(best.monthly_saving)} color={colors.green} /></Grid>
          <Grid item xs={6} sm={3}><Figure label="Pays for itself in" value={best.payback_years ? `${best.payback_years} years` : '-'} /></Grid>
        </Grid>
        {result.notes.length > 0 && (
          <Stack spacing={0.5} sx={{ mt: 2 }}>
            {result.notes.map((n) => (
              <Typography key={n} fontSize={14} sx={{ pl: 1.5, borderLeft: `3px solid ${colors.sun}` }}>{n}</Typography>
            ))}
          </Stack>
        )}
        <Stack direction="row" sx={{ mt: 2.5, flexWrap: 'wrap', gap: 1 }}>
          <Button variant="contained" startIcon={<EventIcon />} component={RouterLink} to={`/survey?quote=${quote.token}`}>
            Book a free site survey
          </Button>
          <Button variant="outlined" startIcon={<DownloadIcon />}
            onClick={() => downloadFile(`/quotes/${quote.token}/pdf`, `solar_quote_Q-${String(quote.quote_id).padStart(5, '0')}.pdf`)
              .catch((e) => setMessage(e.message))}>
            PDF
          </Button>
          <Button variant="outlined" startIcon={<ShareIcon />} onClick={share}>Share</Button>
          <Button variant="outlined" color="success" startIcon={<WhatsAppIcon />} target="_blank" rel="noreferrer"
            href={`https://wa.me/?text=${encodeURIComponent(`My solar quotation: ${link}`)}`}>WhatsApp</Button>
        </Stack>
        {message && <Typography fontSize={13} sx={{ mt: 1 }}>{message}</Typography>}
      </Box>

      {/* 2. compare */}
      <Section title="The three systems side by side">
        <Box sx={{ overflowX: 'auto', bgcolor: '#fff', borderRadius: 3, border: `1px solid ${colors.line}` }}>
          <Table size="small" sx={{ minWidth: 520, '& td, & th': { py: 1 } }}>
            <TableHead>
              <TableRow>
                <TableCell />
                {KINDS.map((k) => (
                  <TableCell key={k} onClick={() => setKind(k)} sx={{ cursor: 'pointer', verticalAlign: 'top',
                    bgcolor: k === kind ? colors.bg : 'transparent', borderBottom: `3px solid ${OPTION_COLORS[k]}` }}>
                    <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700 }}>{OPTION_NAMES[k]}</Typography>
                    {k === result.recommended && <Chip size="small" label="Recommended" sx={{ mt: 0.5, bgcolor: colors.sunSoft }} />}
                    <Typography fontSize={12.5} color="text.secondary" sx={{ mt: 0.5, fontWeight: 400 }}>{OPTION_HINT[k]}</Typography>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {[
                ['Price', (o) => <b>{lakh(o.cost.total)}</b>],
                ['Panels', (o) => `${o.panels} × ${o.panel_watt} W (${o.system_kw} kW)`],
                ['Inverter', (o) => `${o.inverter_kw} kW`],
                ['Battery', (o) => (o.battery_kwh ? `${o.battery_kwh} kWh, about ${o.backup_hours} h backup` : 'None')],
                ['In load-shedding', (o) => ((o.works_in_load_shedding ?? o.kind !== 'on_grid') ? 'Keeps running' : 'Switches off')],
                ['Bill after solar', (o) => rupees(o.monthly_bill_after ?? 0)],
                ['Saving a month', (o) => <span style={{ color: colors.green, fontWeight: 700 }}>{rupees(o.monthly_saving)}</span>],
                ['Payback', (o) => (o.payback_years ? `${o.payback_years} years` : '-')],
                ['Roof needed', (o) => `about ${o.roof_sqft.toLocaleString()} sq ft`],
              ].map(([label, get]) => (
                <TableRow key={label}>
                  <TableCell sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}>{label}</TableCell>
                  {KINDS.map((k) => (
                    <TableCell key={k} sx={{ bgcolor: k === kind ? colors.bg : 'transparent' }}>
                      {get(result.options[k])}
                      {label === 'Price' && result.options[k].over_budget && (
                        <Typography component="span" fontSize={12} color="error.main"> above budget</Typography>
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      </Section>

      {/* 3. WAPDA situations */}
      {best.scenarios && (
        <Section shot="wapda" title="Your monthly bill, whatever you decide about WAPDA">
          <Grid container spacing={1.5}>
            {KINDS.map((k) => (
              <Grid item xs={12} md={compact ? 12 : 4} key={k}>
                <Box sx={{ p: 2, bgcolor: '#fff', borderRadius: 3, border: `1px solid ${colors.line}`, height: '100%' }}>
                  <Typography sx={{ fontWeight: 700 }}>{OPTION_NAMES[k]}</Typography>
                  {result.options[k].scenarios.map((s) => (
                    <Stack key={s.key} direction="row" justifyContent="space-between" sx={{ mt: 1, gap: 1 }}>
                      <Typography fontSize={14} color="text.secondary">{SCENARIO_SHORT[s.key]}</Typography>
                      <Typography fontSize={14} fontWeight={700} sx={{ whiteSpace: 'nowrap' }}>{rupees(s.monthly_bill)}</Typography>
                    </Stack>
                  ))}
                </Box>
              </Grid>
            ))}
          </Grid>
          <Typography fontSize={13} color="text.secondary" sx={{ mt: 1 }}>
            Bill now: {rupees(result.current_bill.total)} a month. Fixed charges stay as long as the WAPDA meter is connected.
          </Typography>
        </Section>
      )}

      {/* 4. load-shedding */}
      {outage?.days_per_week > 0 && outage.timing_known && (
        <Section shot="outage" title="Your load-shedding">
          <Box sx={{ p: 2, bgcolor: '#fff', borderRadius: 3, border: `1px solid ${colors.line}` }}>
            <Typography fontSize={14} sx={{ mb: 1 }}>{outage.text}</Typography>
            <DayStrip start={outage.start_hour} end={outage.end_hour} />
            <Typography fontSize={14} color="text.secondary" sx={{ mt: 1 }}>
              On-grid switches off for these {outage.hours_per_cut} hours. The hybrid runs
              {outage.daylight_hours ? ` ${outage.daylight_hours} h from the panels` : ''}
              {outage.daylight_hours && outage.dark_hours ? ' and' : ''}
              {outage.dark_hours ? ` ${outage.dark_hours} h from the battery` : ''}.
            </Typography>
          </Box>
        </Section>
      )}

      {/* 5. month by month */}
      <Section title="Month by month" aside={
        <Tabs value={kind} onChange={(e, v) => setKind(v)} sx={{ minHeight: 32, '& .MuiTab-root': { minHeight: 32, py: 0 } }}>
          {KINDS.map((k) => <Tab key={k} value={k} label={OPTION_NAMES[k]} />)}
        </Tabs>
      }>
        <Box sx={{ p: 2, bgcolor: '#fff', borderRadius: 3, border: `1px solid ${colors.line}` }}>
          <Typography fontWeight={700} fontSize={14}>Units: what you use and what the panels make</Typography>
          <Box sx={{ height: 210, mt: 1 }}>
            <ResponsiveContainer>
              <BarChart data={months} margin={{ left: -15, right: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={colors.line} />
                <XAxis dataKey="month" fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="used" name="You use" fill={colors.grid} isAnimationActive={false} radius={[3, 3, 0, 0]} />
                <Bar dataKey="generated" name="Solar makes" fill={colors.sun} isAnimationActive={false} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
          <Typography fontWeight={700} fontSize={14} sx={{ mt: 2 }}>
            Bill now and with solar ({SCENARIO_SHORT[mainKey] || 'with solar'})
          </Typography>
          <Box sx={{ height: 190, mt: 1 }}>
            <ResponsiveContainer>
              <BarChart data={months} margin={{ left: 0, right: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={colors.line} />
                <XAxis dataKey="month" fontSize={11} />
                <YAxis fontSize={11} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip formatter={(v) => rupees(v)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="bill_before" name="Bill now" fill={colors.dusk} isAnimationActive={false} radius={[3, 3, 0, 0]} />
                <Bar dataKey="after" name="With solar" fill={colors.green} isAnimationActive={false} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
          {option.short_months?.length > 0 && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              In {option.short_months.join(', ')} the sun alone may not cover everything on cloudy days.
            </Alert>
          )}
        </Box>
      </Section>

      {/* 6. packages + instalments */}
      {result.packages && (
        <Section title={`Packages for the ${OPTION_NAMES[result.recommended].toLowerCase()} system`}>
          <Stack divider={<Box sx={{ borderTop: `1px solid ${colors.line}` }} />}
            sx={{ bgcolor: '#fff', borderRadius: 3, border: `1px solid ${colors.line}`, px: 2 }}>
            {result.packages.map((p) => (
              <Stack key={p.tier} direction={{ xs: 'column', sm: 'row' }} spacing={{ xs: 0.5, sm: 2 }} sx={{ py: 1.75 }}
                alignItems={{ sm: 'center' }}>
                <Box sx={{ width: { sm: 110 }, flexShrink: 0 }}>
                  <Typography sx={{ fontWeight: 700 }}>{p.label}</Typography>
                  {p.tier === 'standard' && <Typography fontSize={12.5} color="text.secondary">quoted above</Typography>}
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography fontSize={14}>{p.parts}</Typography>
                  <Typography fontSize={13} color="text.secondary">{p.warranty}</Typography>
                </Box>
                <Box sx={{ textAlign: { sm: 'right' }, flexShrink: 0 }}>
                  <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: 20 }}>{lakh(p.total)}</Typography>
                  <Typography fontSize={13} color="text.secondary">{p.payback_years ? `pays back in ${p.payback_years} yr` : ''}</Typography>
                </Box>
              </Stack>
            ))}
          </Stack>
        </Section>
      )}
      {result.financing && (
        <Section title="Pay in instalments">
          <Box sx={{ p: 2, bgcolor: '#fff', borderRadius: 3, border: `1px solid ${colors.line}` }}>
            <Typography fontSize={14} color="text.secondary">
              Down payment {rupees(result.financing.down_payment)}, then monthly. Example with {result.financing.markup_percent}% yearly markup.
            </Typography>
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              {result.financing.plans.map((p) => (
                <Grid item xs={4} key={p.months}>
                  <Typography fontSize={13.5} color="text.secondary">{p.months} months</Typography>
                  <Typography sx={{ fontFamily: DISPLAY, fontWeight: 700, fontSize: { xs: 18, sm: 22 } }}>{rupees(p.monthly)}</Typography>
                  <Box sx={{ mt: 0.75, height: 6, borderRadius: 3, bgcolor: colors.bg, overflow: 'hidden' }}>
                    <Box sx={{ height: '100%', width: `${Math.min(100, p.covered_by_saving_percent)}%`, bgcolor: colors.green }} />
                  </Box>
                  <Typography fontSize={12.5} color="text.secondary" sx={{ mt: 0.5 }}>
                    saving covers {Math.min(100, p.covered_by_saving_percent)}%
                  </Typography>
                </Grid>
              ))}
            </Grid>
            <Typography fontSize={12.5} color="text.secondary" sx={{ mt: 1.5 }}>{result.financing.note}</Typography>
          </Box>
        </Section>
      )}

      {/* 7. price + long run */}
      <Section title={`Price breakdown: ${OPTION_NAMES[kind]}`}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={7}>
            <Table size="small" sx={{ bgcolor: '#fff', borderRadius: 3, overflow: 'hidden', border: `1px solid ${colors.line}` }}>
              <TableBody>
                {Object.entries(option.cost.items).filter(([, v]) => v).map(([k, v]) => (
                  <TableRow key={k}><TableCell>{ITEMS[k]}</TableCell><TableCell align="right">{rupees(v)}</TableCell></TableRow>
                ))}
                <TableRow><TableCell sx={{ fontWeight: 700 }}>Total</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>{rupees(option.cost.total)}</TableCell></TableRow>
              </TableBody>
            </Table>
          </Grid>
          <Grid item xs={12} md={5}>
            <Stack spacing={1.25} sx={{ p: 2, bgcolor: '#fff', borderRadius: 3, border: `1px solid ${colors.line}` }}>
              <Figure label="Solar per year" value={`${option.yearly_generation.toLocaleString()} units`} />
              <Figure label="Saving in 25 years" value={lakh(option.saving_25_years)} color={colors.green} />
              <Typography fontSize={13.5} color="text.secondary">
                {option.self_use_percent}% of the solar is used at home. About {option.co2_tonnes_per_year} tonnes of CO₂ avoided a year.
              </Typography>
            </Stack>
          </Grid>
        </Grid>
      </Section>

      <Box sx={{ mt: 3, pt: 2, borderTop: `1px solid ${colors.line}` }}>
        <Typography fontSize={13} color="text.secondary" sx={{ maxWidth: 760 }}>
          How this was worked out: {result.assumptions.yield_kwh_per_kw_year} units per kW of panels a year
          ({result.assumptions.sunlight_source || 'city average'}); panels Rs {result.assumptions.panel_price_per_watt}/W;
          battery Rs {Number(result.assumptions.battery_per_kwh).toLocaleString()}/kWh; net-billing export Rs {result.assumptions.export_rate}/unit;
          bills from {result.assumptions.tariff || 'the NEPRA domestic tariff (Feb 2026)'}. Estimates only: the final price comes after a free site survey.
        </Typography>
      </Box>
    </Box>
  );
}
