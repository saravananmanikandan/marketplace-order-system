import { useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { DEFAULT_ORDERING, FIRST_PAGE, PROVIDERS, STATUSES } from "../constants.js";
import { normalizeOrdering } from "../sorting.js";

const DEFAULTS = { ordering: DEFAULT_ORDERING, page: FIRST_PAGE };

function readPage(rawPage) {
  const page = Number(rawPage);
  return Number.isInteger(page) && page >= FIRST_PAGE ? page : FIRST_PAGE;
}

function readChoice(rawValue, options) {
  return options.some((option) => option.value === rawValue) ? rawValue : "";
}

function applyChanges(current, changes) {
  const next = new URLSearchParams(current);
  Object.entries(changes).forEach(([key, value]) => {
    const isDefault = value === "" || value == null || value === DEFAULTS[key];
    if (isDefault) next.delete(key);
    else next.set(key, value);
  });
  if (!("page" in changes)) next.delete("page");
  return next;
}

export function useOrderListParams() {
  const [searchParams, setSearchParams] = useSearchParams();

  const params = {
    provider: readChoice(searchParams.get("provider"), PROVIDERS),
    status: readChoice(searchParams.get("status"), STATUSES),
    search: searchParams.get("search") ?? "",
    ordering: normalizeOrdering(searchParams.get("ordering")),
    page: readPage(searchParams.get("page")),
  };

  // Values outside the allowed lists are dropped from the address too, so the
  // controls, the address and the list always show the same filters.
  const { provider, status, ordering, page } = params;
  useEffect(() => {
    const cleaned = applyChanges(searchParams, { provider, status, ordering, page });
    if (cleaned.toString() !== searchParams.toString()) {
      setSearchParams(cleaned, { replace: true });
    }
  }, [searchParams, setSearchParams, provider, status, ordering, page]);

  const updateParams = useCallback(
    (changes, options) => setSearchParams((current) => applyChanges(current, changes), options),
    [setSearchParams],
  );

  const clearParams = useCallback(() => setSearchParams(new URLSearchParams()), [setSearchParams]);

  return { params, updateParams, clearParams };
}
