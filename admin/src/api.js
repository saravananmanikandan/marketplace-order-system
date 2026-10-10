import { API_BASE, MAX_RETRIES, NETWORK_ERROR_STATUS, SERVER_ERROR_STATUS } from "./constants.js";

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
    throw new ApiError(NETWORK_ERROR_STATUS, "Could not reach the server.");
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

export function advanceOrderStatus(id, expectedStatus) {
  return request(`/orders/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ expected_status: expectedStatus }),
  });
}

// A 4xx answer will not change on a retry, so only network errors and 5xx are retried.
export function shouldRetry(failureCount, error) {
  const retryable = error.status === NETWORK_ERROR_STATUS || error.status >= SERVER_ERROR_STATUS;
  return retryable && failureCount < MAX_RETRIES;
}
