import { API_BASE } from "./constants.js";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function readErrorMessage(response) {
  try {
    const body = await response.json();
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new ApiError(0, "Could not reach the server.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }
  return response.json();
}

function toQueryString(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value != null) query.set(key, value);
  });
  return query.toString();
}

export function fetchOrders(params) {
  return request(`/orders?${toQueryString(params)}`);
}

export function fetchOrder(id) {
  return request(`/orders/${id}`);
}

export function advanceOrderStatus(id) {
  return request(`/orders/${id}/status`, { method: "PATCH" });
}
