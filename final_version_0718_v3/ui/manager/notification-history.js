const historyState = { tab: "decisions", offset: 0, limit: 50, total: 0, legacyTimer: null };
const apiBase = () => String(CONFIG.MANAGER_API_BASE_URL).replace(/\/$/, "");
const value = id => document.getElementById(id)?.value.trim() || "";
const html = text => String(text ?? "-").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const dateTime = text => text ? new Intl.DateTimeFormat("zh-TW", {dateStyle:"short",timeStyle:"medium",timeZone:"Asia/Taipei"}).format(new Date(text)) : "-";
const fileSize = bytes => Number.isFinite(Number(bytes)) ? `${(Number(bytes) / 1024).toFixed(1)} KB` : "-";

function managerAttachmentUrl(attachmentId) {
  return `${apiBase()}/api/manager/engineer-task-attachments/${encodeURIComponent(attachmentId)}`;
}

function renderAttachment(attachment) {
  if (attachment.attachmentStatus === "deleted") {
    return `<article class="attachment-card deleted"><p>${html(attachment.originalFilename)}</p><small>附件已刪除</small></article>`;
  }
  const url = html(managerAttachmentUrl(attachment.attachmentId));
  return `<figure class="attachment-card"><a href="${url}" target="_blank" rel="noopener"><img src="${url}" alt="${html(attachment.originalFilename)}" loading="lazy"></a><figcaption><strong>${html(attachment.originalFilename)}</strong><small>${html(attachment.mimeType)} · ${fileSize(attachment.sizeBytes)}</small><a href="${url}" target="_blank" rel="noopener">開啟原圖</a></figcaption></figure>`;
}

function renderReports(task) {
  const reports = task.reports || [], attachments = task.attachments || [];
  if (!reports.length) return '<p class="empty-state">尚無工程回報</p>';
  const assignees = new Map((task.assignees || []).map(item => [item.assigneeId, item.engineerName]));
  const reportIds = new Set(reports.map(item => item.reportId));
  const cards = reports.map(report => {
    const images = attachments.filter(item => item.reportId === report.reportId);
    return `<article class="manager-report-card"><header><div><span class="badge">${html(report.reportType)}</span><strong>${html(assignees.get(report.reportedByAssigneeId) || "Engineer")}</strong></div><time>${dateTime(report.reportedAt)}</time></header><dl class="report-fields"><dt>觀察狀況</dt><dd>${html(report.observedCondition)}</dd><dt>確認原因</dt><dd>${html(report.confirmedCause)}</dd><dt>採取措施</dt><dd>${html(report.actionTaken)}</dd><dt>處理結果</dt><dd>${html(report.resultDescription)}</dd><dt>剩餘問題</dt><dd>${html(report.remainingIssue)}</dd><dt>備註</dt><dd>${html(report.note)}</dd></dl><h4>回報附件 (${images.length})</h4>${images.length?`<div class="attachment-grid">${images.map(renderAttachment).join("")}</div>`:'<p class="empty-state">此回報沒有附件</p>'}</article>`;
  }).join("");
  const unlinked = attachments.filter(item => !reportIds.has(item.reportId));
  return cards + (unlinked.length ? `<h4>其他附件 (${unlinked.length})</h4><div class="attachment-grid">${unlinked.map(renderAttachment).join("")}</div>` : "");
}

function query() {
  const params = new URLSearchParams({limit:String(historyState.limit), offset:String(historyState.offset)});
  const fields = {dateFrom:"date_from",dateTo:"date_to",hour:"hour",stationId:"station_id",batchId:"batch_id",decisionType:"decision_type",deliveryStatus:"delivery_status",workflowStatus:"workflow_status",engineerEmail:"engineer_email",taskId:"task_id"};
  Object.entries(fields).forEach(([id,key]) => { if (value(id)) params.set(key,value(id)); });
  return params;
}

async function loadHistory() {
  const endpoint = historyState.tab === "decisions" ? `${apiBase()}/api/manager/notification-decisions?${query()}` : `${getEngineerTaskApiUrl()}?${query()}`;
  document.getElementById("statusLine").textContent = "載入中...";
  try {
    const result = await managerApiRequest(endpoint);
    historyState.total = result.total || 0;
    renderRows(result.items || []);
    document.getElementById("statusLine").textContent = `共 ${historyState.total} 筆，Asia/Taipei`;
  } catch (error) { document.getElementById("statusLine").textContent = `載入失敗：${error.uiReason || error.message}`; }
  renderPager();
}

function renderRows(items) {
  const head = document.getElementById("historyHead"), body = document.getElementById("historyBody");
  if (historyState.tab === "decisions") {
    head.innerHTML = "<tr><th>時間</th><th>站別</th><th>風險</th><th>決策</th><th>抑制次數</th><th>原因</th></tr>";
    body.innerHTML = items.map(row => `<tr><td>${dateTime(row.createdAt)}</td><td>${html(row.stationId)}</td><td>${html(row.riskLevel)}</td><td><span class="badge">${html(row.decisionType)}</span></td><td>${html(row.suppressedCount)}</td><td>${html(row.decisionReason)}</td></tr>`).join("") || '<tr><td colspan="6">無資料</td></tr>';
  } else {
    head.innerHTML = "<tr><th>建立時間</th><th>Task</th><th>站別／批次</th><th>問題</th><th>指派</th><th>流程</th><th>操作</th></tr>";
    body.innerHTML = items.map(row => `<tr><td>${dateTime(row.createdAt)}</td><td class="mono">${html(row.taskId)}</td><td>${html(row.stationName)}<br>${html(row.batchLabel || row.batchId)}</td><td>${html(row.issue)}</td><td>${(row.assignees||[]).map(a=>`${a.isPrimary?"★ ":""}${html(a.engineerName)} / ${html(a.deliveryStatus)} / ${a.acknowledgedAt?"已 ACK":"未 ACK"}`).join("<br>")}</td><td><span class="badge">${html(row.workflowStatus)}</span></td><td><button class="button small" data-task="${html(row.taskId)}">明細</button></td></tr>`).join("") || '<tr><td colspan="7">無資料</td></tr>';
  }
}

function renderPager() {
  const page = Math.floor(historyState.offset/historyState.limit)+1, pages = Math.max(1,Math.ceil(historyState.total/historyState.limit));
  document.getElementById("pageLabel").textContent = `${page} / ${pages}`;
  document.getElementById("previousPage").disabled = historyState.offset===0;
  document.getElementById("nextPage").disabled = historyState.offset+historyState.limit>=historyState.total;
}

async function openTask(taskId) {
  const [task,timeline] = await Promise.all([getEngineerTask(taskId),managerApiRequest(`${getEngineerTaskApiUrl()}/${taskId}/timeline`)]);
  const canReview = task.workflowStatus === "completion_submitted";
  const reviewDisabled = canReview ? "" : ' disabled aria-disabled="true" title="只有等待 Manager 驗收的任務才能操作"';
  document.getElementById("taskDetail").innerHTML = `<h2>${html(task.stationName)} / ${html(task.issue)}</h2><p class="mono">${html(task.taskId)}</p><dl><dt>流程</dt><dd>${html(task.workflowStatus)}</dd><dt>建議</dt><dd>${html(task.recommendation)}</dd></dl><h3>指派</h3>${(task.assignees||[]).map(a=>`<p>${a.isPrimary?"Primary":"Collaborator"}：${html(a.engineerName)}，${a.isRequiredParticipant?"必要參與者":"非必要"}，${html(a.deliveryStatus)}，${a.acknowledgedAt?"已 ACK":"未 ACK"}</p>`).join("")}<section class="report-detail-section"><h3>工程回報 (${(task.reports||[]).length})</h3>${renderReports(task)}</section><h3>Timeline</h3><ol class="timeline">${(timeline.items||[]).map(e=>`<li><strong>${html(e.eventType)}</strong><span>${dateTime(e.eventTime)} ${html(e.actorName||e.actorType)}</span><p>${html(e.message||"")}</p></li>`).join("")}</ol><div class="action-row"><button class="button" data-resend-first>重送第一位未 ACK</button><button class="button secondary" data-review="accept"${reviewDisabled}>驗收通過</button><button class="button danger" data-review="reject"${reviewDisabled}>退回</button></div>`;
  const dialog=document.getElementById("taskDialog"); dialog.dataset.taskId=taskId; dialog.dataset.workflowStatus=task.workflowStatus; dialog.dataset.assignees=JSON.stringify(task.assignees||[]); dialog.showModal();
}

async function taskAction(event) {
  const dialog=document.getElementById("taskDialog"), taskId=dialog.dataset.taskId, assignees=JSON.parse(dialog.dataset.assignees||"[]");
  if(event.target.matches("[data-resend-first]")){const a=assignees.find(x=>x.isActive&&!x.acknowledgedAt);if(!a)return alert("沒有可重送對象");if(!confirm("重送會輪替安全 token，確定繼續？"))return;await managerApiRequest(`${getEngineerTaskApiUrl()}/${taskId}/resend`,{method:"POST",body:JSON.stringify({assigneeIds:[a.assigneeId],warningConfirmed:true})});}
  if(event.target.dataset.review){
    if(dialog.dataset.workflowStatus!=="completion_submitted")return alert("只有等待 Manager 驗收的任務才能執行驗收或退回");
    const action=event.target.dataset.review, reason=action==="reject"?prompt("請輸入退回原因"):null;
    if(action==="reject"&&!reason)return;
    const recipients=action==="reject"?assignees.filter(x=>x.isActive).slice(0,1).map(x=>x.assigneeId):[];
    const reviewButtons=[...dialog.querySelectorAll("[data-review]")];
    reviewButtons.forEach(button=>{button.disabled=true;});
    try {
      await managerApiRequest(`${getEngineerTaskApiUrl()}/${taskId}/review`,{method:"POST",body:JSON.stringify({action,managerName:"Manager",applicableChecks:["異常原因已確認"],confirmedChecks:["異常原因已確認"],reason,notifyAssigneeIds:recipients})});
    } catch (error) {
      reviewButtons.forEach(button=>{button.disabled=false;});
      throw error;
    }
  }
  dialog.close(); loadHistory();
}

async function syncLegacyAcks() {
  if (document.hidden || historyState.tab!=="tasks") return;
  const result=await getEngineerTasks({deliveryStatus:"sent",limit:50});
  for(const task of result.items||[]){if(task.legacyAckSyncRequired) await syncEngineerTaskAck(task.taskId).catch(()=>null);}
}
function updatePolling(){clearInterval(historyState.legacyTimer);historyState.legacyTimer=null;if(!document.hidden&&historyState.tab==="tasks"){syncLegacyAcks();historyState.legacyTimer=setInterval(syncLegacyAcks,120000);}}

document.addEventListener("click",event=>{const tab=event.target.closest("[data-tab]");if(tab){document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===tab));historyState.tab=tab.dataset.tab;historyState.offset=0;updatePolling();loadHistory();}const task=event.target.closest("[data-task]");if(task)openTask(task.dataset.task).catch(error=>alert(error.message));});
document.getElementById("searchButton").onclick=()=>{historyState.offset=0;loadHistory();};
document.getElementById("previousPage").onclick=()=>{historyState.offset=Math.max(0,historyState.offset-historyState.limit);loadHistory();};
document.getElementById("nextPage").onclick=()=>{historyState.offset+=historyState.limit;loadHistory();};
document.getElementById("closeDialog").onclick=()=>document.getElementById("taskDialog").close();
document.getElementById("taskDetail").addEventListener("click",event=>taskAction(event).catch(error=>alert(error.uiReason||error.message)));
document.addEventListener("visibilitychange",updatePolling);window.addEventListener("beforeunload",()=>clearInterval(historyState.legacyTimer));
const start=new Date();start.setDate(start.getDate()-6);document.getElementById("dateFrom").value=start.toISOString().slice(0,10);loadHistory();
