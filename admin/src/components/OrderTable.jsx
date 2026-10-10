import { useNavigate } from "react-router-dom";
import { PROVIDERS, SORT_COLUMNS, labelFor } from "../constants.js";
import { formatMoney, formatTime } from "../format.js";
import SortableHeader from "./SortableHeader.jsx";
import StatusBadge from "./StatusBadge.jsx";

function OrderRow({ order }) {
  const navigate = useNavigate();
  const openDetail = () => navigate(`/orders/${order.id}`);

  function handleKeyDown(event) {
    if (event.key === "Enter") openDetail();
  }

  return (
    <tr
      tabIndex={0}
      onClick={openDetail}
      onKeyDown={handleKeyDown}
      className="order-row"
      aria-label={`Open order ${order.external_order_id} for ${order.customer.name || "unknown customer"}`}
    >
      <td data-label="Provider">{labelFor(PROVIDERS, order.provider)}</td>
      <td data-label="Order ID" className="mono">
        {order.external_order_id}
      </td>
      <td data-label="Customer">{order.customer.name || "—"}</td>
      <td data-label="Status">
        <StatusBadge status={order.status} />
      </td>
      <td data-label="Total">{formatMoney(order.total_cents, order.currency)}</td>
      <td data-label="Time">{formatTime(order.created_at)}</td>
    </tr>
  );
}

export default function OrderTable({ orders, ordering, onSortChange }) {
  return (
    <table className="orders">
      <caption className="visually-hidden">Orders</caption>
      <thead>
        <tr>
          {SORT_COLUMNS.map((column) => (
            <SortableHeader
              key={column.key}
              column={column}
              ordering={ordering}
              onSortChange={onSortChange}
            />
          ))}
        </tr>
      </thead>
      <tbody>
        {orders.map((order) => (
          <OrderRow key={order.id} order={order} />
        ))}
      </tbody>
    </table>
  );
}
