import { useEffect, useState } from "react";
import { PROVIDERS, SEARCH_DEBOUNCE_MS, SORT_OPTIONS } from "../constants.js";
import { SearchIcon } from "./Icons.jsx";

function Select({ label, value, options, onChange, anyLabel, className = "" }) {
  return (
    <label className={`field ${className}`.trim()}>
      <span className="visually-hidden">{label}</span>
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

export default function OrderFilters({ params, hasFilters, onChange, onClear }) {
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
        <span className="visually-hidden">Search</span>
        <SearchIcon />
        <input
          type="search"
          value={searchText}
          placeholder="Search customer name or order ID"
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
        className="field-sort"
        label="Sort by"
        value={params.ordering}
        options={SORT_OPTIONS}
        onChange={(ordering) => onChange({ ordering })}
      />
      {hasFilters && (
        <button type="button" className="button button-ghost" onClick={onClear}>
          Clear filters
        </button>
      )}
    </form>
  );
}
