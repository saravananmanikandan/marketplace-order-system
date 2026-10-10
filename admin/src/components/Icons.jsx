// Small hand-drawn icons; they are decorative, so screen readers skip them.
function Icon({ children }) {
  return (
    <svg
      className="icon"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export function SearchIcon() {
  return (
    <Icon>
      <circle cx="7" cy="7" r="4.5" />
      <path d="M10.5 10.5 14 14" />
    </Icon>
  );
}

export function ChevronLeftIcon() {
  return (
    <Icon>
      <path d="M10 3.5 5.5 8l4.5 4.5" />
    </Icon>
  );
}

export function ArrowUpIcon() {
  return (
    <Icon>
      <path d="M8 13V3M4 7l4-4 4 4" />
    </Icon>
  );
}

export function ArrowDownIcon() {
  return (
    <Icon>
      <path d="M8 3v10M4 9l4 4 4-4" />
    </Icon>
  );
}
