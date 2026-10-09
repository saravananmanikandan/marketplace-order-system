import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { DEFAULT_ORDERING, FIRST_PAGE } from "../constants.js";
import { normalizeOrdering } from "../sorting.js";

const DEFAULTS = { ordering: DEFAULT_ORDERING, page: FIRST_PAGE };

function readPage(rawPage) {
  const page = Number(rawPage);
  return Number.isInteger(page) && page >= FIRST_PAGE ? page : FIRST_PAGE;
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
    provider: searchParams.get("provider") ?? "",
    status: searchParams.get("status") ?? "",
    search: searchParams.get("search") ?? "",
    ordering: normalizeOrdering(searchParams.get("ordering")),
    page: readPage(searchParams.get("page")),
  };

  const updateParams = useCallback(
    (changes, options) => setSearchParams((current) => applyChanges(current, changes), options),
    [setSearchParams],
  );

  const clearParams = useCallback(() => setSearchParams(new URLSearchParams()), [setSearchParams]);

  return { params, updateParams, clearParams };
}
