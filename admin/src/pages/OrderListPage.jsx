import { useEffect } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchOrders } from "../api.js";
import OrderFilters from "../components/OrderFilters.jsx";
import OrderTable from "../components/OrderTable.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Pagination from "../components/Pagination.jsx";
import RefreshNote from "../components/RefreshNote.jsx";
import StatusPills from "../components/StatusPills.jsx";
import { ORDERS_QUERY_KEY, REFRESH_INTERVAL_MS } from "../constants.js";
import { formatClock } from "../format.js";
import { useOrderListParams } from "../hooks/useOrderListParams.js";

const SKELETON_ROWS = 5;

function LoadingSkeleton() {
  return (
    <div className="card list-skeleton" role="status">
      <span className="visually-hidden">Loading orders…</span>
      {Array.from({ length: SKELETON_ROWS }, (_, index) => (
        <div key={index} className="skeleton-row" aria-hidden="true">
          <span className="skeleton-bar skeleton-short" />
          <span className="skeleton-bar skeleton-long" />
          <span className="skeleton-bar skeleton-medium" />
          <span className="skeleton-bar skeleton-short" />
        </div>
      ))}
    </div>
  );
}

function StateCard({ role, children }) {
  return (
    <div className="card state-card" role={role}>
      {children}
    </div>
  );
}

export default function OrderListPage() {
  const { params, hasFilters, updateParams, clearParams } = useOrderListParams();

  const { data, isPending, isError, isRefetchError, error, refetch, isPlaceholderData, dataUpdatedAt } =
    useQuery({
      queryKey: [ORDERS_QUERY_KEY, "list", params],
      queryFn: () => fetchOrders(params),
      placeholderData: keepPreviousData,
      refetchInterval: REFRESH_INTERVAL_MS,
    });

  // The API answers a page past the end with the last page (for example after
  // orders moved out of the current status filter), so the address follows it.
  // Placeholder data belongs to the previous address, so it is not compared.
  const answeredPage = isPlaceholderData ? undefined : data?.page;
  useEffect(() => {
    if (answeredPage !== undefined && answeredPage !== params.page) {
      updateParams({ page: answeredPage }, { replace: true });
    }
  }, [answeredPage, params.page, updateParams]);

  return (
    <section aria-labelledby="orders-heading">
      <PageHeader
        title="Orders"
        titleId="orders-heading"
        aside={
          <>
            {dataUpdatedAt > 0 && <span className="muted">Updated {formatClock(dataUpdatedAt)}</span>}
            {isRefetchError && <RefreshNote />}
          </>
        }
      />
      <StatusPills value={params.status} onChange={(status) => updateParams({ status })} />
      <OrderFilters
        params={params}
        hasFilters={hasFilters}
        onChange={updateParams}
        onClear={clearParams}
      />

      {isPending && <LoadingSkeleton />}

      {isError && !data && (
        <StateCard role="alert">
          <p>
            Could not load orders ({error.message.replace(/\.$/, "")}). Check that the API is
            running, then try again.
          </p>
          <button type="button" className="button" onClick={() => refetch()}>
            Try again
          </button>
        </StateCard>
      )}

      {data && data.results.length === 0 && (
        <StateCard role="status">
          <p>
            {hasFilters
              ? "No orders match these filters; clear them to see every order."
              : "No orders yet; they appear here as soon as a webhook arrives."}
          </p>
        </StateCard>
      )}

      {data && data.results.length > 0 && (
        <div className={isPlaceholderData ? "results is-stale" : "results"}>
          <div className="card table-card">
            <OrderTable
              orders={data.results}
              ordering={params.ordering}
              onSortChange={(ordering) => updateParams({ ordering })}
            />
          </div>
          <Pagination
            page={params.page}
            count={data.count}
            hasPrevious={Boolean(data.previous)}
            hasNext={Boolean(data.next)}
            onPageChange={(page) => updateParams({ page })}
          />
        </div>
      )}
    </section>
  );
}
