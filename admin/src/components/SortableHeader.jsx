import { ASCENDING, DESCENDING } from "../constants.js";
import { ariaSortFor, nextOrdering } from "../sorting.js";

const ARROWS = { [ASCENDING]: "▲", [DESCENDING]: "▼" };

export default function SortableHeader({ column, ordering, onSortChange }) {
  const sortState = ariaSortFor(column, ordering);

  return (
    <th scope="col" aria-sort={sortState}>
      <button
        type="button"
        className="sort-button"
        onClick={() => onSortChange(nextOrdering(column, ordering))}
      >
        {column.label}
        <span className="sort-arrow" aria-hidden="true">
          {ARROWS[sortState] ?? ""}
        </span>
      </button>
    </th>
  );
}
