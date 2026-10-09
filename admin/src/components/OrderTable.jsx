import { useNavigate } from "react-router-dom";
import { PROVIDERS, labelFor } from "../constants.js";
import { formatMoney, formatTime } from "../format.js";
import StatusBadge from "./StatusBadge.jsx";

const COLUMNS = ["Provider", "Order ID", "Customer", "Status", "Total", "Time"];

function OrderRow({ order }) {
  const navigate = useNavigate();
  const openDetail = () => navigate(`/orders/${order.id}`);

  function handleKeyDown(event) {
    if (event.key === "Enter") openDetail();
  }

  return (
    <tr tabIndex={0} onClick={openDetail} onKeyDown={handleKeyDown} className="order-row">
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

export default function OrderTable({ orders }) {
  return (
    <table className="orders">
      <thead>
        <tr>
          {COLUMNS.map((column) => (
            <th key={column} scope="col">
              {column}
            </th>
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
