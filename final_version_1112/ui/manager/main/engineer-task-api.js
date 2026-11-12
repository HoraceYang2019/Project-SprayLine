function createEngineerTask(payload) {
  return managerApiRequest(getEngineerTaskApiUrl(), {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

function getEngineerTasks({ deliveryStatus = "", limit = 100, offset = 0 } = {}) {
  const endpoint = new URL(getEngineerTaskApiUrl(), window.location.origin);
  if (deliveryStatus) endpoint.searchParams.set("delivery_status", deliveryStatus);
  endpoint.searchParams.set("limit", String(limit));
  endpoint.searchParams.set("offset", String(offset));
  return managerApiRequest(endpoint.toString());
}

function getEngineerTask(taskId) {
  return managerApiRequest(`${getEngineerTaskApiUrl()}/${encodeURIComponent(taskId)}`);
}

function syncEngineerTaskAck(taskId) {
  return managerApiRequest(`${getEngineerTaskApiUrl()}/${encodeURIComponent(taskId)}/sync-ack`, {
    method: "POST",
    body: JSON.stringify({ force: false })
  });
}

