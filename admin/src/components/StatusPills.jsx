import { STATUSES } from "../constants.js";

const ALL_STATUSES = { value: "", label: "All" };

export default function StatusPills({ value, onChange }) {
  return (
    <div className="status-pills" role="group" aria-label="Filter by status">
      {[ALL_STATUSES, ...STATUSES].map((option) => (
        <button
          key={option.value || "all"}
          type="button"
          className="status-pill"
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
