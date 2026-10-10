import { formatMoney } from "../format.js";

const COLUMNS = ["Item", "Quantity", "Unit price", "Line total"];

export default function LineItemsTable({ items, currency }) {
  if (items.length === 0) return <p className="muted">No line items.</p>;

  return (
    <table className="items orders">
      <caption className="visually-hidden">Line items</caption>
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
        {items.map((item, index) => (
          <tr key={`${item.name}-${index}`}>
            <td data-label="Item">{item.name}</td>
            <td data-label="Quantity">{item.quantity}</td>
            <td data-label="Unit price">{formatMoney(item.unit_price_cents, currency)}</td>
            <td data-label="Line total">{formatMoney(item.line_total_cents, currency)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
