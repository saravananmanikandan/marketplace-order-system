import { Link, useLocation } from "react-router-dom";
import { LIST_SEARCH_STATE_KEY, ORDERS_PATH } from "../constants.js";
import { ChevronLeftIcon } from "./Icons.jsx";

// The list hands its filters to the detail page when a row is opened, so this
// always returns to the list with them, wherever the previous history entry is.
function listSearchFrom(state) {
  const search = state?.[LIST_SEARCH_STATE_KEY];
  return typeof search === "string" && search.startsWith("?") ? search : "";
}

export default function BackLink() {
  const location = useLocation();

  return (
    <Link
      to={{ pathname: ORDERS_PATH, search: listSearchFrom(location.state) }}
      className="button button-ghost back-button"
    >
      <ChevronLeftIcon />
      Back to orders
    </Link>
  );
}
