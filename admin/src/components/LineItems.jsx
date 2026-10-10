import { formatMoney } from "../format.js";

export default function LineItems({ items, currency, totalCents }) {
  return (
    <>
      {items.length === 0 ? (
        <p className="muted">No line items.</p>
      ) : (
        <ul className="line-items" aria-label="Line items">
          {items.map((item, index) => (
            <li key={`${item.name}-${index}`} className="line-item">
              <div className="line-item-text">
                <p className="line-item-name">{item.name}</p>
                {item.notes ? <p className="line-item-notes">{item.notes}</p> : null}
                <p className="muted line-item-meta num">
                  {item.quantity} × {formatMoney(item.unit_price_cents, currency)}
                </p>
              </div>
              <p className="line-item-total num">
                {formatMoney(item.line_total_cents, currency)}
              </p>
            </li>
          ))}
        </ul>
      )}
      <p className="line-items-total">
        <span>Total</span>
        <span className="num">{formatMoney(totalCents, currency)}</span>
      </p>
    </>
  );
}
