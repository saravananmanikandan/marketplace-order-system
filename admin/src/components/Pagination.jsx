export default function Pagination({ page, count, hasPrevious, hasNext, onPageChange }) {
  // Everything fits on one page, so there is nowhere to go.
  if (!hasPrevious && !hasNext) return null;

  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        type="button"
        className="button button-secondary"
        disabled={!hasPrevious}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </button>
      <span className="pagination-status">
        Page {page}, {count} {count === 1 ? "order" : "orders"}
      </span>
      <button
        type="button"
        className="button button-secondary"
        disabled={!hasNext}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </nav>
  );
}
