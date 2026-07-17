var ACK_KEY_PREFIX = "engineer_task_ack_";

function doPost(e) {
  try {
    var payload = parseRequestPayload(e);
    if (payload.action !== "send_task") {
      return jsonResponse({ success: false, error: "Unsupported action" });
    }
    return sendEngineerTask(payload);
  } catch (error) {
    return jsonResponse({ success: false, error: String(error.message || error) });
  }
}

function doGet(e) {
  var action = String((e && e.parameter && e.parameter.action) || "");
  var taskId = String((e && e.parameter && e.parameter.taskId) || "");
  if (action === "ack_task") return acknowledgeTask(taskId, e.parameter || {});
  if (action === "ack_status") return jsonResponse(getAckStatus(taskId));
  if (action === "ack_status_jsonp") {
    return jsonpResponse(getAckStatus(taskId), String(e.parameter.callback || "callback"));
  }
  return jsonResponse({ success: false, error: "Unsupported action" });
}

function parseRequestPayload(e) {
  var content = e && e.postData && e.postData.contents;
  if (content) return JSON.parse(content);
  var formPayload = e && e.parameter && e.parameter.payload;
  if (formPayload) return JSON.parse(formPayload);
  throw new Error("Request payload is required");
}

function sendEngineerTask(payload) {
  var taskId = requireText(payload.taskId, "taskId");
  var recipient = requireText(payload.engineerEmail || payload.to, "engineerEmail");
  var title = requireText(payload.title, "title");
  var scriptUrl = ScriptApp.getService().getUrl();
  var ackUrl = scriptUrl + "?action=ack_task&taskId=" + encodeURIComponent(taskId) +
    "&ackBy=" + encodeURIComponent(payload.engineerName || "Engineer") +
    "&ackEmail=" + encodeURIComponent(recipient);
  var textBody = String(payload.messageText || payload.task || payload.recommendation || "") +
    "\n\nTask ID: " + taskId + "\nACK: " + ackUrl;
  var htmlBody = escapeHtml(textBody).replace(/\n/g, "<br>") +
    '<p><a href="' + escapeHtml(ackUrl) + '">確認已收到任務</a></p>';

  MailApp.sendEmail({ to: recipient, subject: title, body: textBody, htmlBody: htmlBody });
  return jsonResponse({
    success: true,
    taskId: taskId,
    recipient: recipient,
    sentAt: new Date().toISOString()
  });
}

function acknowledgeTask(taskId, params) {
  requireText(taskId, "taskId");
  var ack = {
    acknowledged: true,
    taskId: taskId,
    ackAt: new Date().toISOString(),
    ackBy: String(params.ackBy || "Engineer"),
    ackEmail: String(params.ackEmail || ""),
    ackNote: String(params.ackNote || ""),
    source: "apps_script"
  };
  PropertiesService.getScriptProperties().setProperty(ACK_KEY_PREFIX + taskId, JSON.stringify(ack));
  return HtmlService.createHtmlOutput("<h2>任務已確認</h2><p>Task ID: " + escapeHtml(taskId) + "</p>");
}

function getAckStatus(taskId) {
  requireText(taskId, "taskId");
  var saved = PropertiesService.getScriptProperties().getProperty(ACK_KEY_PREFIX + taskId);
  if (!saved) return { acknowledged: false, taskId: taskId, source: "apps_script" };
  return JSON.parse(saved);
}

function jsonResponse(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

function jsonpResponse(value, callback) {
  var safeCallback = /^[A-Za-z_$][0-9A-Za-z_$\.]*$/.test(callback) ? callback : "callback";
  return ContentService.createTextOutput(safeCallback + "(" + JSON.stringify(value) + ");")
    .setMimeType(ContentService.MimeType.JAVASCRIPT);
}

function requireText(value, fieldName) {
  var text = String(value || "").trim();
  if (!text) throw new Error(fieldName + " is required");
  return text;
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
