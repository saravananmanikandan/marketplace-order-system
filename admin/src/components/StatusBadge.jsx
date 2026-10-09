import { STATUSES, labelFor } from "../constants.js";

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{labelFor(STATUSES, status)}</span>;
}
