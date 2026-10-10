const MINOR_UNITS_BASE = 10;
const FALLBACK_MINOR_UNIT_DIGITS = 2;

function minorUnitDigits(currency) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).resolvedOptions()
    .maximumFractionDigits;
}

// Intl throws on a currency code it does not know, and one bad row must not
// take the whole page down, so the plain amount and code are shown instead.
export function formatMoney(cents, currency) {
  try {
    const amount = cents / MINOR_UNITS_BASE ** minorUnitDigits(currency);
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
  } catch {
    const amount = cents / MINOR_UNITS_BASE ** FALLBACK_MINOR_UNIT_DIGITS;
    return `${amount.toFixed(FALLBACK_MINOR_UNIT_DIGITS)} ${currency}`;
  }
}

export function formatTime(isoString) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(isoString));
}

export function formatClock(timestampMs) {
  return new Intl.DateTimeFormat(undefined, { timeStyle: "medium" }).format(new Date(timestampMs));
}
