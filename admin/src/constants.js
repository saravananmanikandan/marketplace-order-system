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

export const TERMINAL_STATUSES = ["completed", "cancelled"];

export const ORDERING_NEWEST_FIRST = "-created_at";
export const ORDERING_OLDEST_FIRST = "created_at";
export const DEFAULT_ORDERING = ORDERING_NEWEST_FIRST;

export const SORT_OPTIONS = [
  { value: ORDERING_NEWEST_FIRST, label: "Newest first" },
  { value: ORDERING_OLDEST_FIRST, label: "Oldest first" },
];

export const SEARCH_DEBOUNCE_MS = 300;
export const FIRST_PAGE = 1;

export const ORDERS_QUERY_KEY = "orders";

export const labelFor = (options, value) =>
  options.find((option) => option.value === value)?.label ?? value;
