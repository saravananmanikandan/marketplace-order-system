import { STATUSES, STATUS_PROGRESSION, labelFor } from "../constants.js";
import StatusBadge from "./StatusBadge.jsx";

const CANCELLED = "cancelled";

export default function OrderProgress({ status }) {
  if (status === CANCELLED) return <StatusBadge status={status} />;

  const current = STATUS_PROGRESSION.indexOf(status);
  return (
    <ol className="progress">
      {STATUS_PROGRESSION.map((step, index) => (
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
