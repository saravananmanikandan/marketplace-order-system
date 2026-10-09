import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { advanceOrderStatus, fetchOrder } from "../api.js";
import BackLink from "../components/BackLink.jsx";
import RefreshNote from "../components/RefreshNote.jsx";
import LineItemsTable from "../components/LineItemsTable.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import {
  ORDERS_QUERY_KEY,
  PROVIDERS,
  REFRESH_INTERVAL_MS,
  STATUSES,
  labelFor,
  nextStatus,
} from "../constants.js";
import { formatMoney, formatTime } from "../format.js";

const NOT_FOUND = 404;

function DebugBlock({ order }) {
  return (
    <details className="debug">
      <summary>Debug data</summary>
      <p>
        Raw total: <code>{order.total_cents}</code> cents ({order.currency})
      </p>
      <pre>{JSON.stringify(order.raw_payload, null, 2)}</pre>
    </details>
  );
}

function AdvanceButton({ order }) {
  const queryClient = useQueryClient();
  const upcoming = nextStatus(order.status);

  const advance = useMutation({
    mutationFn: () => advanceOrderStatus(order.id),
    onSuccess: (updated) => {
      queryClient.setQueryData([ORDERS_QUERY_KEY, "detail", String(order.id)], updated);
      queryClient.invalidateQueries({ queryKey: [ORDERS_QUERY_KEY] });
    },
  });

  return (
    <div className="advance">
      <button
        type="button"
        className="button"
        disabled={!upcoming || advance.isPending}
        onClick={() => advance.mutate()}
      >
        {upcoming ? `Move to ${labelFor(STATUSES, upcoming)}` : "No further steps"}
      </button>
      {advance.isError && <p role="alert" className="error-text">{advance.error.message}</p>}
    </div>
  );
}

function OrderDetail({ order }) {
  return (
    <article className="detail">
      <header className="detail-header">
        <div>
          <h1>Order {order.external_order_id}</h1>
          <p className="muted">
            {labelFor(PROVIDERS, order.provider)} · {formatTime(order.created_at)}
          </p>
        </div>
        <StatusBadge status={order.status} />
      </header>

      <section aria-labelledby="customer-heading">
        <h2 id="customer-heading">Customer</h2>
        <p>{order.customer.name || "No name provided"}</p>
        <p className="muted">{order.customer.phone || "No phone provided"}</p>
      </section>

      <section aria-labelledby="items-heading">
        <h2 id="items-heading">Items</h2>
        <LineItemsTable items={order.line_items} currency={order.currency} />
        <p className="total">
          Total <strong>{formatMoney(order.total_cents, order.currency)}</strong>
        </p>
      </section>

      <section aria-labelledby="status-heading">
        <h2 id="status-heading">Status</h2>
        <AdvanceButton order={order} />
      </section>

      <DebugBlock order={order} />
    </article>
  );
}

export default function OrderDetailPage() {
  const { id } = useParams();
  const { data, isPending, isError, isRefetchError, error, refetch } = useQuery({
    queryKey: [ORDERS_QUERY_KEY, "detail", id],
    queryFn: () => fetchOrder(id),
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  return (
    <section>
      <BackLink />
      {isPending && <div className="message" role="status">Loading order…</div>}
      {isError && !data && error.status === NOT_FOUND && (
        <div className="message" role="alert">This order does not exist.</div>
      )}
      {isError && !data && error.status !== NOT_FOUND && (
        <div className="message" role="alert">
          Could not load the order: {error.message}{" "}
          <button type="button" className="button" onClick={() => refetch()}>
            Try again
          </button>
        </div>
      )}
      {isRefetchError && <RefreshNote />}
      {data && <OrderDetail order={data} />}
    </section>
  );
}
