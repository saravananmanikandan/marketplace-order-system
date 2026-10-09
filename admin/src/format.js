const MINOR_UNITS_BASE = 10;

function minorUnitDigits(currency) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).resolvedOptions()
    .maximumFractionDigits;
}

export function formatMoney(cents, currency) {
  const amount = cents / MINOR_UNITS_BASE ** minorUnitDigits(currency);
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
}

export function formatTime(isoString) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(isoString));
}
