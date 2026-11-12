function parseDateKey(dateKey) {
  const [year, month, day] = String(dateKey || "").split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDateLabel(dateKey) {
  const date = parseDateKey(dateKey);
  if (Number.isNaN(date.getTime())) return String(dateKey || "-");
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}/${month}/${day}`;
}

function getResponseHourFromDb(dbResponse) {
  const rawHour = dbResponse?.responseMeta?.selectedHour;
  const hour = Number(rawHour);
  return Number.isFinite(hour) ? Math.max(0, Math.min(23, hour)) : null;
}

function getResponseDateKeyFromDb(dbResponse) {
  const dateKey = dbResponse?.responseMeta?.selectedDate;
  return typeof dateKey === "string" && dateKey ? dateKey : null;
}

function getInitialReportDateKey() {
  return null;
}

function getLatestDateKeyFromDb(dbResponse = currentDatabaseResponse) {
  const dateKey = dbResponse?.responseMeta?.latestDate;
  return typeof dateKey === "string" && dateKey ? dateKey : null;
}

function getLatestHourFromDb(dbResponse = currentDatabaseResponse) {
  const rawHour = dbResponse?.responseMeta?.latestHour;
  const hour = Number(rawHour);
  return Number.isFinite(hour) ? Math.max(0, Math.min(23, hour)) : null;
}

function getAvailableDatesFromDb(dbResponse = currentDatabaseResponse) {
  const availableDates = dbResponse?.responseMeta?.availableDates;
  return Array.isArray(availableDates) ? availableDates.map(String) : [];
}

function getAvailableHoursByDateFromDb(dbResponse = currentDatabaseResponse) {
  const value = dbResponse?.responseMeta?.availableHoursByDate;
  return value && typeof value === "object" ? value : {};
}

function getAvailableHoursForDate(dateKey, dbResponse = currentDatabaseResponse) {
  if (!dateKey) return [];

  const hoursByDate = getAvailableHoursByDateFromDb(dbResponse);
  const source = Array.isArray(hoursByDate[dateKey])
    ? hoursByDate[dateKey]
    : dateKey === getResponseDateKeyFromDb(dbResponse) && Array.isArray(dbResponse?.responseMeta?.availableHours)
      ? dbResponse.responseMeta.availableHours
      : [];

  return source
    .map(value => Number(value))
    .filter(value => Number.isFinite(value) && value >= 0 && value <= 23)
    .sort((left, right) => left - right);
}

function formatHourRangeLabel(hour) {
  const hourNumber = Number(hour);
  if (!Number.isFinite(hourNumber)) return "選擇小時";
  const label = String(Math.max(0, Math.min(23, hourNumber))).padStart(2, "0");
  return `${label}:00 - ${label}:59`;
}

function generateDateOptions() {
  const latestDate = getLatestDateKeyFromDb(currentDatabaseResponse);
  return getAvailableDatesFromDb(currentDatabaseResponse).map(dateKey => ({
    key: dateKey,
    label: dateKey === latestDate ? `${formatDateLabel(dateKey)} (DB latest)` : formatDateLabel(dateKey)
  }));
}

function generateHourOptionsForSelectedDate() {
  return getAvailableHoursForDate(selectedReportDate).map(hour => ({
    value: String(hour),
    label: formatHourRangeLabel(hour)
  }));
}

function getSelectedHourSelectValue() {
  const hour = selectedReportHour ?? getResponseHourFromDb(currentDatabaseResponse);
  return Number.isFinite(hour) ? String(hour) : "";
}

function syncSelectedDateHourFromDb(dbResponse) {
  selectedReportDate = getResponseDateKeyFromDb(dbResponse);
  selectedReportHourMode = "hour";
  selectedReportHour = getResponseHourFromDb(dbResponse);
  selectedBatchId = dbResponse?.managerView?.batchSelector?.selectedBatchId || null;
}

function storeHourlySnapshotForDbResponse(_dbResponse) {
}
