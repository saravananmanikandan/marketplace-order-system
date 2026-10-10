import { ApiError } from "../api.js";

const DEMO_API_BASE = "/demo/api";
const NETWORK_ERROR_STATUS = 0;

async function demoRequest(path, options) {
  let response;
  try {
    response = await fetch(`${DEMO_API_BASE}${path}`, options);
  } catch {
    throw new ApiError(NETWORK_ERROR_STATUS, "Could not reach the server.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, body?.detail ?? response.statusText);
  }
  return body;
}

export function fetchSimulatorConfig() {
  return demoRequest("/config");
}

export function sendSimulatedWebhook(options) {
  return demoRequest("/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
}
