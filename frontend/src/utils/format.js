/** Small display helpers. Pakistani style: Rs 14.5 lakh, 1,25,000 is written 125,000 here for clarity. */
export const rupees = (n) => `Rs ${Math.round(Number(n || 0)).toLocaleString('en-US')}`;

export function lakh(n) {
  const v = Number(n || 0);
  if (v >= 10000000) return `Rs ${(v / 10000000).toFixed(2)} crore`;
  if (v >= 100000) return `Rs ${(v / 100000).toFixed(1)} lakh`;
  return rupees(v);
}

export const OPTION_NAMES = { on_grid: 'On-grid', hybrid: 'Hybrid + battery', off_grid: 'Off-grid' };
export const OPTION_HINT = {
  on_grid: 'Cheapest. Lowers the bill. No power during load-shedding.',
  hybrid: 'Lowers the bill AND keeps fans, lights and fridge on during load-shedding.',
  off_grid: 'No WAPDA connection needed. Big battery, highest price.',
};
export const LEAD_STATUS = {
  new: { label: 'New', color: 'warning' },
  contacted: { label: 'Contacted', color: 'info' },
  site_visit: { label: 'Site visit', color: 'secondary' },
  won: { label: 'Won', color: 'success' },
  lost: { label: 'Lost', color: 'default' },
};

export function dateTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

export const isUrdu = (text) => /[؀-ۿ]/.test(text || '');
