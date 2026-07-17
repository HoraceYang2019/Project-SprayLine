async function managerApiRequest(endpoint, options = {}) {
  if (!endpoint) throw new Error("Manager API endpoint is not configured.");
  let response;
  try {
    response = await fetch(endpoint, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
  } catch (error) {
    throw buildManagerUiError({
      title: "Manager API connection failed",
      endpoint,
      reason: error.message || "Failed to fetch",
      suggestion: "Please confirm API Server is running on port 8011.",
      cause: error
    });
  }

  const bodyText = await response.text();
  let payload = null;
  if (bodyText) {
    try {
      payload = JSON.parse(bodyText);
    } catch (error) {
      throw buildManagerUiError({
        title: "Manager API response parse error",
        endpoint,
        status: `${response.status} ${response.statusText}`.trim(),
        reason: "invalid JSON response",
        cause: error
      });
    }
  }
  if (!response.ok) {
    throw buildManagerUiError({
      title: "Manager API HTTP error",
      endpoint,
      status: `${response.status} ${response.statusText}`.trim(),
      reason: payload?.detail || payload?.message || bodyText || "Request failed"
    });
  }
  return payload;
}

