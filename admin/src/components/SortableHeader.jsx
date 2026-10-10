import { ASCENDING, DESCENDING } from "../constants.js";
import { ariaSortFor, nextOrdering } from "../sorting.js";
import { ArrowDownIcon, ArrowUpIcon } from "./Icons.jsx";

const ARROWS = { [ASCENDING]: ArrowUpIcon, [DESCENDING]: ArrowDownIcon };

export default function SortableHeader({ column, ordering, onSortChange }) {
  const sortState = ariaSortFor(column, ordering);
  const Arrow = ARROWS[sortState];

  return (
    <th scope="col" aria-sort={sortState} className={`col-${column.key}`}>
      <button
        type="button"
        className={Arrow ? "sort-button is-sorted" : "sort-button"}
        onClick={() => onSortChange(nextOrdering(column, ordering))}
      >
        {column.label}
        {Arrow && <Arrow />}
      </button>
    </th>
  );
}
