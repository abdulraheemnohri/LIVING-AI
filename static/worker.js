(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  async function refreshWorker() {
    try {
      const d = await api("/api/worker/status");
      const w = d.worker;
      $("#worker-state").textContent = !w.enabled ? "Disabled" : w.paused ? "Paused" : "Resumed · manual only";
      $("#worker-approvals").textContent = d.pending_approval;
      $("#worker-budget").textContent = w.cycles_remaining + " / " + w.max_cycles_per_run;
      $("#worker-goals").innerHTML = d.goals.map(g =>
        '<div class="item"><b>' + esc(g.title) + '</b><p><small>' + esc(g.status) + ' · ' + esc(g.action) + '</small></p><p>' + esc(g.result || "") + '</p>' +
        (g.status === "needs_approval" ? '<button data-worker-approve="' + esc(g.id) + '">Approve this goal</button>' : '') + '</div>'
      ).join("") || "No goals in the queue.";
      $("#worker-history").textContent = JSON.stringify({events:d.events,runs:d.runs}, null, 2);
      $("#worker-goals").querySelectorAll("[data-worker-approve]").forEach(b => b.onclick = async () => {
        if (!confirm("Approve this single goal? It will be queued, not executed immediately.")) return;
        try {
          const result = await api("/api/worker/goals/" + encodeURIComponent(b.dataset.workerApprove) + "/approve", {method:"POST",body:"{}"});
          $("#worker-result").textContent = JSON.stringify(result, null, 2);
          note("Goal approved and queued; execution still requires a manual tick");
          await refreshWorker();
        } catch (e) { note(e.message); }
      });
    } catch (e) {
      $("#worker-result").textContent = e.message;
      $("#worker-state").textContent = "Unavailable";
    }
  }
  async function action(path, body) {
    try {
      const d = await api(path, {method:"POST",body:JSON.stringify(body || {})});
      $("#worker-result").textContent = JSON.stringify(d, null, 2);
      note(d.execution_performed ? "Worker tick completed; inspect results" : "Worker control updated; no execution performed");
      await refreshWorker();
    } catch (e) {
      $("#worker-result").textContent = e.message;
      note("Worker action failed");
    }
  }
  $("#worker-enable")?.addEventListener("click", () => action("/api/worker/enable"));
  $("#worker-disable")?.addEventListener("click", () => action("/api/worker/disable"));
  $("#worker-resume")?.addEventListener("click", () => action("/api/worker/resume"));
  $("#worker-pause")?.addEventListener("click", () => action("/api/worker/pause"));
  $("#worker-refresh")?.addEventListener("click", refreshWorker);
  $("#worker-tick")?.addEventListener("click", () => {
    if (!confirm("Run one worker tick now? Only previously approved, queued goals may execute.")) return;
    action("/api/worker/tick");
  });
  $("#worker-configure")?.addEventListener("click", () => action("/api/worker/configure", {
    max_cycles_per_run: Number($("#worker-budget-input").value)
  }));
  $("#worker-recommend-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    const out = $("#worker-recommendations");
    out.textContent = "Reviewing stored outcomes…";
    try {
      const d = await api("/api/worker/recommendations", {method:"POST",body:JSON.stringify({
        goal:$("#worker-recommend-goal").value, limit:5
      })});
      out.textContent = JSON.stringify(d, null, 2);
    } catch (err) { out.textContent = err.message; }
  });
  const previousGo = go;
  go = function(v) {
    previousGo(v);
    if (v === "worker") refreshWorker();
  };
})();
