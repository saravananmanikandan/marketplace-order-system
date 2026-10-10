import { STATUSES, labelFor } from "../constants.js";
import StatusBadge from "./StatusBadge.jsx";

const CANCELLED = "cancelled";
// The steps are drawn in the order of the status labels; which step comes
// next is decided by the API (`next_status`), not here.
const STEPS = STATUSES.map((option) => option.value).filter((value) => value !== CANCELLED);

export default function OrderProgress({ status }) {
  if (status === CANCELLED) return <StatusBadge status={status} />;

  const current = STEPS.indexOf(status);
  return (
    <ol className="progress">
      {STEPS.map((step, index) => (
        <li
          key={step}
          className={index <= current ? "progress-step is-reached" : "progress-step"}
          aria-current={index === current ? "step" : undefined}
        >
          <span className="progress-segment" aria-hidden="true" />
          <span className="progress-name">
            {labelFor(STATUSES, step)}
            {index < current && <span className="visually-hidden"> (done)</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}
