import { useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { advanceOrderStatus, fetchOrder } from "../api.js";
import BackLink from "../components/BackLink.jsx";
import LineItems from "../components/LineItems.jsx";
import OrderProgress from "../components/OrderProgress.jsx";
import PageHeader from "../components/PageHeader.jsx";
import RefreshNote from "../components/RefreshNote.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import {
  CONFLICT_STATUS,
  NOT_FOUND_STATUS,
  ORDERS_QUERY_KEY,
  PROVIDERS,
  REFRESH_INTERVAL_MS,
  STATUSES,
  labelFor,
} from "../constants.js";
import { formatMoney, formatTime } from "../format.js";

function DebugBlock({ order }) {
  return (
    <details className="card debug">
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
  const upcoming = order.next_status;
  // isPending only disables the button after a re-render, so a fast double
  // click could still send two requests; the ref blocks the second at once.
  const inFlight = useRef(false);

  const advance = useMutation({
    mutationFn: () => advanceOrderStatus(order.id, order.status),
    onSuccess: (updated) => {
      queryClient.setQueryData([ORDERS_QUERY_KEY, "detail", String(order.id)], updated);
    },
    onSettled: () => {
      inFlight.current = false;
      queryClient.invalidateQueries({ queryKey: [ORDERS_QUERY_KEY] });
    },
  });

  function handleClick() {
    if (inFlight.current) return;
    inFlight.current = true;
    advance.mutate();
  }

  const isConflict = advance.error?.status === CONFLICT_STATUS;

  return (
    <div className="advance">
      {upcoming ? (
        <button
          type="button"
          className="button button-block"
          disabled={advance.isPending}
          onClick={handleClick}
        >
          Move to {labelFor(STATUSES, upcoming)}
        </button>
      ) : (
        <p className="muted">No further steps</p>
      )}
      {isConflict && (
        <p role="status" className="muted">
          This order changed somewhere else. The latest status is shown above.
        </p>
      )}
      {advance.isError && !isConflict && (
        <p role="alert" className="error-text">{advance.error.message}</p>
      )}
    </div>
  );
}

function lineItemsAddUp(order) {
  const sum = order.line_items.reduce((total, item) => total + item.line_total_cents, 0);
  return sum === order.total_cents;
}

function TotalCard({ order }) {
  return (
    <section className="card card-body detail-total" aria-labelledby="total-heading">
      <h2 id="total-heading" className="card-label">
        Total
      </h2>
      <p className="total-amount num">{formatMoney(order.total_cents, order.currency)}</p>
      <dl className="facts">
        <div>
          <dt>Provider</dt>
          <dd>{labelFor(PROVIDERS, order.provider)}</dd>
        </div>
        <div>
          <dt>Order id</dt>
          <dd className="mono">{order.external_order_id}</dd>
        </div>
        <div>
          <dt>Received</dt>
          <dd>{formatTime(order.created_at)}</dd>
        </div>
        <div>
          <dt>Currency</dt>
          <dd>{order.currency}</dd>
        </div>
      </dl>
      <AdvanceButton order={order} />
    </section>
  );
}

function ItemsCard({ order }) {
  return (
    <section className="card card-body detail-items" aria-labelledby="items-heading">
      <h2 id="items-heading" className="card-title">
        Items
      </h2>
      <LineItems items={order.line_items} currency={order.currency} totalCents={order.total_cents} />
      {!lineItemsAddUp(order) && (
        <p className="muted line-items-note">
          Line items do not add up to the total. Taxes and fees are not itemised here.
        </p>
      )}
    </section>
  );
}

function CustomerCard({ customer }) {
  return (
    <section className="card card-body detail-customer" aria-labelledby="customer-heading">
      <h2 id="customer-heading" className="card-title">
        Customer
      </h2>
      <p className="customer-name">{customer.name || "No name provided"}</p>
      <p className="muted">
        {customer.phone || "No phone provided"}
        {customer.phone && customer.phone_code && <> · code {customer.phone_code}</>}
      </p>
    </section>
  );
}

function ProgressCard({ status }) {
  return (
    <section className="card card-body detail-progress" aria-labelledby="progress-heading">
      <h2 id="progress-heading" className="card-title">
        Progress
      </h2>
      <OrderProgress status={status} />
    </section>
  );
}

function OrderDetail({ order, refreshFailed }) {
  return (
    <article>
      <PageHeader
        before={<BackLink />}
        title={`Order ${order.external_order_id}`}
        meta={
          <div className="page-meta">
            <p className="muted">{labelFor(PROVIDERS, order.provider)}</p>
            <p className="muted">Received {formatTime(order.created_at)}</p>
          </div>
        }
        aside={
          <>
            {refreshFailed && <RefreshNote />}
            <StatusBadge status={order.status} />
          </>
        }
      />
      {/* Two columns from 1024 px; below that the cards stack in reading order. */}
      <div className="detail-layout">
        <div className="detail-side">
          <TotalCard order={order} />
          <ProgressCard status={order.status} />
        </div>
        <div className="detail-main">
          <ItemsCard order={order} />
          <CustomerCard customer={order.customer} />
        </div>
        <DebugBlock order={order} />
      </div>
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

  if (data) return <OrderDetail order={data} refreshFailed={isRefetchError} />;

  return (
    <section>
      <BackLink />
      {isPending && (
        <div className="card state-card" role="status">
          <p>Loading order…</p>
        </div>
      )}
      {isError && error.status === NOT_FOUND_STATUS && (
        <div className="card state-card" role="alert">
          <p>This order does not exist; go back to the order list to pick another one.</p>
        </div>
      )}
      {isError && error.status !== NOT_FOUND_STATUS && (
        <div className="card state-card" role="alert">
          <p>
            Could not load the order ({error.message.replace(/\.$/, "")}). Check that the API is
            running, then try again.
          </p>
          <button type="button" className="button" onClick={() => refetch()}>
            Try again
          </button>
        </div>
      )}
    </section>
  );
}
