import { useEffect, useState } from "react";
import { PROVIDERS, SEARCH_DEBOUNCE_MS, SORT_OPTIONS, STATUSES } from "../constants.js";

function Select({ label, value, options, onChange, anyLabel }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {anyLabel && <option value="">{anyLabel}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function OrderFilters({ params, onChange, onClear }) {
  const [searchText, setSearchText] = useState(params.search);

  useEffect(() => {
    setSearchText(params.search);
  }, [params.search]);

  useEffect(() => {
    if (searchText === params.search) return undefined;
    const timer = setTimeout(
      () => onChange({ search: searchText.trim() }, { replace: true }),
      SEARCH_DEBOUNCE_MS,
    );
    return () => clearTimeout(timer);
  }, [searchText, params.search, onChange]);

  return (
    <form className="filters" role="search" onSubmit={(event) => event.preventDefault()}>
      <label className="field field-search">
        <span>Search</span>
        <input
          type="search"
          value={searchText}
          placeholder="Customer name or order ID"
          onChange={(event) => setSearchText(event.target.value)}
        />
      </label>
      <Select
        label="Provider"
        value={params.provider}
        options={PROVIDERS}
        anyLabel="All providers"
        onChange={(provider) => onChange({ provider })}
      />
      <Select
        label="Status"
        value={params.status}
        options={STATUSES}
        anyLabel="All statuses"
        onChange={(status) => onChange({ status })}
      />
      <Select
        label="Sort by time"
        value={params.ordering}
        options={SORT_OPTIONS}
        onChange={(ordering) => onChange({ ordering })}
      />
      <button type="button" className="button button-quiet" onClick={onClear}>
        Clear filters
      </button>
    </form>
  );
}
