import {
  ASCENDING,
  DEFAULT_ORDERING,
  DESCENDING,
  DESCENDING_PREFIX,
  SORT_COLUMNS,
} from "./constants.js";

export function parseOrdering(ordering) {
  const descending = ordering.startsWith(DESCENDING_PREFIX);
  return {
    key: descending ? ordering.slice(DESCENDING_PREFIX.length) : ordering,
    direction: descending ? DESCENDING : ASCENDING,
  };
}

export function buildOrdering(key, direction) {
  return direction === DESCENDING ? `${DESCENDING_PREFIX}${key}` : key;
}

export function nextOrdering(column, currentOrdering) {
  const current = parseOrdering(currentOrdering);
  if (current.key !== column.key) return buildOrdering(column.key, column.firstDirection);
  const flipped = current.direction === ASCENDING ? DESCENDING : ASCENDING;
  return buildOrdering(column.key, flipped);
}

export function ariaSortFor(column, currentOrdering) {
  const current = parseOrdering(currentOrdering);
  return current.key === column.key ? current.direction : "none";
}

export function normalizeOrdering(ordering) {
  const { key } = parseOrdering(ordering ?? "");
  return SORT_COLUMNS.some((column) => column.key === key) ? ordering : DEFAULT_ORDERING;
}
