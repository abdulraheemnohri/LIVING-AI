(() => {
  const $ = s => document.querySelector(s);
  const safe = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  async function loadTasks() {
    const list = $("#tasklist");
    if (!list) return;
    list.textContent = "Loading tasks…";
    try {
      const data = await api("/api/tasks?limit=100");
      list.innerHTML = data.items.map(t => {
        const detail = safe(t.last_detail || "");
        const actions = (t.status === "failed" ? '<button data-retry="' + safe(t.task_id) + '">Retry failed task</button>' : "") +
          (t.status === "needs_approval" ? '<button data-approve="' + safe(t.task_id) + '">Approve one attempt</button>' : "");
        return '<div class="item"><b>' + safe(t.title) + '</b><p><small>' + safe(t.status) + ' · action: ' + safe(t.action) + ' · attempt ' + safe(t.attempts) + '/' + safe(Number(t.max_retries) + 1) + '</small></p><p>' + detail + '</p><button data-inspect="' + safe(t.task_id) + '">Inspect history</button> ' + actions + '</div>';
      }).join("") || "No tasks yet. Queue a task above.";
      list.querySelectorAll("[data-inspect]").forEach(b => b.onclick = () => inspectTask(b.dataset.inspect));
      list.querySelectorAll("[data-retry]").forEach(b => b.onclick = async () => {
        try { await api("/api/tasks/" + encodeURIComponent(b.dataset.retry) + "/retry", {method:"POST", body:"{}"}); note("Retry queued"); await loadTasks(); }
        catch (e) { note(e.message); }
      });
      list.querySelectorAll("[data-approve]").forEach(b => b.onclick = async () => {
        try { await api("/api/tasks/" + encodeURIComponent(b.dataset.approve) + "/approve", {method:"POST", body:"{}"}); note("Task approved and re-queued; run a cycle to process it"); await loadTasks(); }
        catch (e) { note(e.message); }
      });
    } catch (e) { list.textContent = e.message; }
  }
  async function inspectTask(id) {
    try {
      const t = await api("/api/tasks/" + encodeURIComponent(id));
      $("#taskdetail").textContent = JSON.stringify(t, null, 2);
    } catch (e) { $("#taskdetail").textContent = e.message; }
  }
  $("#taskform")?.addEventListener("submit", async e => {
    e.preventDefault();
    const out = $("#task-result");
    out.textContent = "Queueing task…";
    try {
      const t = await api("/api/tasks", {method:"POST", body:JSON.stringify({
        title:$("#tasktitle").value,
        action:$("#taskaction").value,
        payload:{text:$("#tasktext").value}
      })});
      out.textContent = JSON.stringify({queued:true, task_id:t.task_id, status:t.status, execution_performed:false}, null, 2);
      $("#tasktext").value = "";
      note("Task queued; no action executed yet");
      await loadTasks();
    } catch (err) { out.textContent = err.message; note("Could not queue task"); }
  });
  $("#run-task-cycle")?.addEventListener("click", async () => {
    const out = $("#task-result");
    if (!confirm("Run one bounded cycle of queued tasks? Registered reversible actions may execute now.")) return;
    out.textContent = "Running one cycle…";
    try {
      const result = await api("/api/tasks/run-once", {method:"POST", body:"{}"});
      out.textContent = JSON.stringify(result, null, 2);
      note("Cycle finished; review task outcomes");
      await loadTasks();
    } catch (err) { out.textContent = err.message; note("Cycle failed"); }
  });
  $("#refresh-tasks")?.addEventListener("click", loadTasks);
  if (typeof go === "function") {
    const oldGo = go;
    go = function(v) { oldGo(v); if (v === "tasks") loadTasks(); };
  }
  document.querySelectorAll('[data-view="tasks"]').forEach(b => b.addEventListener("click", () => loadTasks()));
})();
