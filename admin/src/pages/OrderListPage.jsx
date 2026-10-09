import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchOrders } from "../api.js";
import OrderFilters from "../components/OrderFilters.jsx";
import OrderTable from "../components/OrderTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { ORDERS_QUERY_KEY } from "../constants.js";
import { useOrderListParams } from "../hooks/useOrderListParams.js";

function Message({ role, children }) {
  return (
    <div className="message" role={role}>
      {children}
    </div>
  );
}

export default function OrderListPage() {
  const { params, updateParams, clearParams } = useOrderListParams();

  const { data, isPending, isError, error, refetch, isPlaceholderData } = useQuery({
    queryKey: [ORDERS_QUERY_KEY, "list", params],
    queryFn: () => fetchOrders(params),
    placeholderData: keepPreviousData,
  });

  return (
    <section aria-labelledby="orders-heading">
      <h1 id="orders-heading">Orders</h1>
      <OrderFilters params={params} onChange={updateParams} onClear={clearParams} />

      {isPending && <Message role="status">Loading orders…</Message>}

      {isError && (
        <Message role="alert">
          Could not load orders: {error.message}{" "}
          <button type="button" className="button" onClick={() => refetch()}>
            Try again
          </button>
        </Message>
      )}

      {data && data.results.length === 0 && (
        <Message role="status">No orders match these filters.</Message>
      )}

      {data && data.results.length > 0 && (
        <div className={isPlaceholderData ? "results is-stale" : "results"}>
          <OrderTable orders={data.results} />
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
