import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ORDERS_QUERY_KEY } from "../constants.js";
import { fetchCurlCommand, sendSimulatedWebhook } from "./demoApi.js";

const UBER = "uber_eats";
const DOORDASH = "doordash";
const PROVIDER_LABELS = { [UBER]: "Uber Eats", [DOORDASH]: "DoorDash" };
const PRESET_LABELS = { official: "Official sample", random: "Random order", custom: "Custom" };
const CUSTOM_PRESET = "custom";
const OFFICIAL_PRESET = "official";
const NEW_ORDER = "new";
const REUSE_ORDER = "reuse";
const CENTS_PER_DOLLAR = 100;
const FOCUSABLE =
  'button:not([disabled]), input:not([disabled]), select:not([disabled]), summary, [href], [tabindex]:not([tabindex="-1"])';

let nextRowKey = 0;
const emptyRow = () => ({ key: nextRowKey++, name: "", quantity: "1", price: "" });

function pillTone(status) {
  if (status >= 200 && status < 300) return "ok";
  if (status >= 400 && status < 500) return "warn";
  return "error";
}

function useFocusTrap(dialogRef, onClose) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialogRef.current?.querySelector(FOCUSABLE)?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [dialogRef]);

  return function handleKeyDown(event) {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...dialogRef.current.querySelectorAll(FOCUSABLE)];
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
}

function ItemsEditor({ rows, setRows, maxItems }) {
  const update = (key, field, value) =>
    setRows((current) => current.map((row) => (row.key === key ? { ...row, [field]: value } : row)));

  return (
    <div className="sim-items">
      {rows.map((row, index) => (
        <div className="sim-item-row" key={row.key}>
          <label className="field sim-item-name">
            <span>Item {index + 1} name</span>
            <input value={row.name} onChange={(event) => update(row.key, "name", event.target.value)} />
          </label>
          <label className="field sim-item-qty">
            <span>Qty</span>
            <input
              type="number"
              min="1"
              max="99"
              value={row.quantity}
              onChange={(event) => update(row.key, "quantity", event.target.value)}
            />
          </label>
          <label className="field sim-item-price">
            <span>Price ($)</span>
            <input
              type="number"
              min="0"
              step="0.01"
              inputMode="decimal"
              value={row.price}
              onChange={(event) => update(row.key, "price", event.target.value)}
            />
          </label>
          <button
            type="button"
            className="button button-quiet sim-item-remove"
            aria-label={`Remove item ${index + 1}`}
            disabled={rows.length === 1}
            onClick={() => setRows((current) => current.filter((other) => other.key !== row.key))}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        className="button button-quiet"
        disabled={rows.length >= maxItems}
        onClick={() => setRows((current) => [...current, emptyRow()])}
      >
        Add item
      </button>
    </div>
  );
}

function SendResult({ result }) {
  const { deliveries, sent, order_id: orderId } = result;
  return (
    <>
      <p className="muted">
        Order id <code>{orderId}</code>
      </p>
      <ul className="sim-deliveries">
        {deliveries.map((delivery, index) => (
          <li key={index}>
            <span>Delivery {index + 1}</span>{" "}
            <span className={`sim-pill sim-pill-${pillTone(delivery.status)}`}>
              {delivery.status ?? "No response"}
            </span>
            <pre>{delivery.body || "(empty body)"}</pre>
          </li>
        ))}
      </ul>
      <details className="sim-sent">
        <summary>What was sent</summary>
        <p>
          POST <code>{sent.url}</code>
        </p>
        <pre>{JSON.stringify(sent.headers, null, 2)}</pre>
        <pre>{JSON.stringify(sent.body, null, 2)}</pre>
        {sent.staged_get_order && (
          <>
            <p>Get Order response the API will fetch</p>
            <pre>{JSON.stringify(sent.staged_get_order, null, 2)}</pre>
          </>
        )}
      </details>
    </>
  );
}

function toOptions(form, rows, lastOrderId) {
  const options = {
    provider: form.provider,
    preset: form.preset,
    order_id: form.orderChoice === REUSE_ORDER && lastOrderId ? lastOrderId : NEW_ORDER,
    auth: form.auth,
    deliveries: form.sendTwice ? 2 : 1,
  };
  if (form.provider === UBER) options.uber_state = form.uberState;
  if (form.preset === CUSTOM_PRESET) {
    options.customer = {
      first_name: form.firstName,
      last_name: form.lastName,
      phone: form.phone,
    };
    options.items = rows.map((row) => ({
      name: row.name,
      quantity: Number(row.quantity),
      unit_price_cents: Math.round(Number(row.price) * CENTS_PER_DOLLAR),
    }));
  }
  return options;
}

export default function SimulatorDrawer({ config, lastOrderIds, onSent, onClose }) {
  const dialogRef = useRef(null);
  const handleKeyDown = useFocusTrap(dialogRef, onClose);
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    provider: UBER,
    preset: CUSTOM_PRESET,
    firstName: "",
    lastName: "",
    phone: "",
    uberState: config.uber_states[0],
    orderChoice: NEW_ORDER,
    auth: "valid",
    sendTwice: false,
  });
  const [rows, setRows] = useState(() => [emptyRow()]);
  const lastOrderId = lastOrderIds?.[form.provider];
  const isCustom = form.preset === CUSTOM_PRESET;
  // The official sample is sent unchanged apart from its id, so it keeps its own state.
  const usesUberState = form.preset !== OFFICIAL_PRESET;
  const setField = (field) => (event) => {
    const { type, checked, value } = event.target;
    setForm((current) => ({ ...current, [field]: type === "checkbox" ? checked : value }));
  };

  const send = useMutation({
    mutationFn: () => sendSimulatedWebhook(toOptions(form, rows, lastOrderId)),
    onSuccess: (result) => {
      onSent(result.last_order_ids);
      queryClient.invalidateQueries({ queryKey: [ORDERS_QUERY_KEY] });
    },
  });

  const [copyMessage, setCopyMessage] = useState("");
  const curlRef = useRef(null);
  const updatesExistingOrder = form.orderChoice === REUSE_ORDER && Boolean(lastOrderId);
  const copyCurl = useMutation({
    mutationFn: () => fetchCurlCommand(toOptions(form, rows, lastOrderId)),
    onMutate: () => setCopyMessage(""),
    onSuccess: async (copied) => {
      const effect = updatesExistingOrder ? "updates" : "creates";
      try {
        await navigator.clipboard.writeText(copied.curl);
        setCopyMessage(`Copied. Running it ${effect} order ${copied.order_id}.`);
      } catch {
        // Without clipboard access, select the text so it can be copied by hand.
        window.getSelection().selectAllChildren(curlRef.current);
        setCopyMessage(`Selected below: press Cmd+C or Ctrl+C. Running it ${effect} order ${copied.order_id}.`);
      }
    },
  });

  function handleSubmit(event) {
    event.preventDefault();
    if (!send.isPending) send.mutate();
  }

  return createPortal(
    <div className="sim-layer">
      <div className="sim-backdrop" onClick={onClose} />
      <div
        ref={dialogRef}
        className="sim-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sim-title"
        onKeyDown={handleKeyDown}
      >
        <header className="sim-header">
          <h2 id="sim-title">Webhook simulator</h2>
          <span className="demo-tag">Demo tool</span>
          <button
            type="button"
            className="button button-quiet sim-close"
            aria-label="Close webhook simulator"
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <form className="sim-form" onSubmit={handleSubmit}>
          <fieldset className="sim-segments">
            <legend>Provider</legend>
            {[UBER, DOORDASH].map((provider) => (
              <label key={provider} className="sim-segment">
                <input
                  type="radio"
                  name="sim-provider"
                  value={provider}
                  checked={form.provider === provider}
                  onChange={setField("provider")}
                />
                <span>{PROVIDER_LABELS[provider]}</span>
              </label>
            ))}
          </fieldset>

          <label className="field">
            <span>Preset</span>
            <select value={form.preset} onChange={setField("preset")}>
              {config.presets.map((preset) => (
                <option key={preset} value={preset}>
                  {PRESET_LABELS[preset] ?? preset}
                </option>
              ))}
            </select>
          </label>

          <fieldset className="sim-group" disabled={!isCustom}>
            <legend>Customer and items {!isCustom && <span className="muted">(Custom only)</span>}</legend>
            <div className="sim-row">
              <label className="field">
                <span>First name</span>
                <input value={form.firstName} onChange={setField("firstName")} />
              </label>
              <label className="field">
                <span>Last name</span>
                <input value={form.lastName} onChange={setField("lastName")} />
              </label>
            </div>
            <label className="field">
              <span>Phone</span>
              <input type="tel" value={form.phone} onChange={setField("phone")} />
            </label>
            <ItemsEditor rows={rows} setRows={setRows} maxItems={config.limits.items} />
          </fieldset>

          {form.provider === UBER && (
            <label className="field">
              <span>
                Uber order state {!usesUberState && "(not used by Official sample)"}
              </span>
              <select
                value={form.uberState}
                disabled={!usesUberState}
                onChange={setField("uberState")}
              >
                {config.uber_states.map((state) => (
                  <option key={state} value={state}>
                    {state}
                  </option>
                ))}
              </select>
            </label>
          )}

          <fieldset className="sim-group">
            <legend>Order id</legend>
            <label className="sim-choice">
              <input
                type="radio"
                name="sim-order-id"
                value={NEW_ORDER}
                checked={form.orderChoice === NEW_ORDER || !lastOrderId}
                onChange={setField("orderChoice")}
              />
              New order
            </label>
            <label className="sim-choice">
              <input
                type="radio"
                name="sim-order-id"
                value={REUSE_ORDER}
                disabled={!lastOrderId}
                checked={form.orderChoice === REUSE_ORDER && Boolean(lastOrderId)}
                onChange={setField("orderChoice")}
              />
              Reuse last order id {lastOrderId && <code className="sim-id">{lastOrderId}</code>}
            </label>
          </fieldset>

          <label className="field">
            <span>Authentication</span>
            <select value={form.auth} onChange={setField("auth")}>
              <option value="valid">Valid signature or token</option>
              <option value="invalid">Invalid signature or token</option>
            </select>
          </label>

          <label className="sim-choice">
            <input type="checkbox" checked={form.sendTwice} onChange={setField("sendTwice")} />
            Send twice at the same moment
          </label>

          <button type="submit" className="button sim-send" disabled={send.isPending}>
            {send.isPending ? "Sending…" : "Send"}
          </button>

          <div className="sim-curl">
            <button
              type="button"
              className="button button-quiet sim-copy-curl"
              disabled={copyCurl.isPending}
              onClick={() => copyCurl.mutate()}
            >
              {copyCurl.isPending ? "Preparing…" : "Copy curl command"}
            </button>
            <p className="muted sim-hint">
              Builds the same webhook without sending it. Each copy gets a new order id, so
              pasting it adds a new order (unless "Reuse last order id" is chosen).
            </p>
            {copyCurl.isError && (
              <p role="alert" className="error-text">
                {copyCurl.error.message}
              </p>
            )}
            <p role="status" className="sim-copy-status">
              {copyMessage}
            </p>
            {copyCurl.isSuccess && (
              <pre ref={curlRef} tabIndex={0} aria-label="Copied curl command">
                {copyCurl.data.curl}
              </pre>
            )}
          </div>
        </form>

        <section className="sim-result" aria-live="polite" aria-label="Result">
          {send.isError && (
            <p role="alert" className="error-text">
              {send.error.message}
            </p>
          )}
          {send.isSuccess && <SendResult result={send.data} />}
        </section>
      </div>
    </div>,
    document.body,
  );
}
