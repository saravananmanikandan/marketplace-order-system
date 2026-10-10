export const API_BASE = "/api";

export const PROVIDERS = [
  { value: "uber", label: "Uber Eats" },
  { value: "doordash", label: "DoorDash" },
];

export const STATUSES = [
  { value: "new", label: "New" },
  { value: "accepted", label: "Accepted" },
  { value: "preparing", label: "Preparing" },
  { value: "ready", label: "Ready" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

export const STATUS_PROGRESSION = ["new", "accepted", "preparing", "ready", "completed"];
export const TERMINAL_STATUSES = ["completed", "cancelled"];

export const DEFAULT_ORDERING = "-created_at";
export const DESCENDING_PREFIX = "-";

export const ASCENDING = "ascending";
export const DESCENDING = "descending";

// firstDirection is what a first click on the column sorts by.
export const SORT_COLUMNS = [
  { key: "provider", label: "Provider", firstDirection: ASCENDING, ascending: "Provider A to Z", descending: "Provider Z to A" },
  { key: "external_order_id", label: "Order ID", firstDirection: ASCENDING, ascending: "Order ID A to Z", descending: "Order ID Z to A" },
  { key: "customer_name", label: "Customer", firstDirection: ASCENDING, ascending: "Customer A to Z", descending: "Customer Z to A" },
  { key: "status", label: "Status", firstDirection: ASCENDING, ascending: "Status, new first", descending: "Status, cancelled first" },
  { key: "total_cents", label: "Total", firstDirection: DESCENDING, ascending: "Total, low to high", descending: "Total, high to low" },
  { key: "created_at", label: "Time", firstDirection: DESCENDING, ascending: "Time, oldest first", descending: "Time, newest first" },
];

export const SORT_OPTIONS = SORT_COLUMNS.flatMap((column) => [
  { value: column.key, label: column.ascending },
  { value: `${DESCENDING_PREFIX}${column.key}`, label: column.descending },
]);

export const SEARCH_DEBOUNCE_MS = 300;
export const REFRESH_INTERVAL_MS = 5000;
export const FIRST_PAGE = 1;

export const ORDERS_QUERY_KEY = "orders";

export const MAX_RETRIES = 2;
export const NETWORK_ERROR_STATUS = 0;
export const SERVER_ERROR_STATUS = 500;
export const NOT_FOUND_STATUS = 404;
export const CONFLICT_STATUS = 409;

export const labelFor = (options, value) =>
  options.find((option) => option.value === value)?.label ?? value;

export function nextStatus(status) {
  if (TERMINAL_STATUSES.includes(status)) return null;
  return STATUS_PROGRESSION[STATUS_PROGRESSION.indexOf(status) + 1];
}
