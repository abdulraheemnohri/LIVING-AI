(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  async function refreshEvaluation() {
    try {
      const d = await api("/api/evaluation/runs?limit=10");
      const items = d.items || [];
      const latest = items[0];
      $("#evaluation-score").textContent = latest ? Math.round(latest.score * 100) + "%" : "—";
      $("#evaluation-passed").textContent = latest ? latest.passed + " / " + latest.total : "—";
      $("#evaluation-history").innerHTML = items.map(run =>
        '<div class="item"><b>' + esc(new Date(run.created_at * 1000).toLocaleString()) +
        '</b><p><small>' + esc(run.passed) + ' / ' + esc(run.total) + ' passed · ' +
        esc(Math.round(run.score * 100)) + '% · ' + esc(run.run_id) + '</small></p>' +
        '<details><summary>View case results</summary><pre>' +
        esc(JSON.stringify(run.results, null, 2)) + '</pre></details></div>'
      ).join("") || "No evaluation runs recorded yet.";
    } catch (e) {
      $("#evaluation-history").textContent = e.message;
    }
  }
  $("#evaluation-run")?.addEventListener("click", async () => {
    const button = $("#evaluation-run");
    button.disabled = true;
    $("#evaluation-result").textContent = "Running offline regression suite…";
    try {
      const result = await api("/api/evaluation/run", {method:"POST", body:"{}"});
      $("#evaluation-result").textContent = JSON.stringify(result, null, 2);
      $("#evaluation-score").textContent = Math.round(result.score * 100) + "%";
      $("#evaluation-passed").textContent = result.passed + " / " + result.total;
      note("Evaluation complete; no actions executed");
      await refreshEvaluation();
    } catch (e) {
      $("#evaluation-result").textContent = e.message;
      note("Evaluation failed");
    } finally {
      button.disabled = false;
    }
  });
  async function refreshGateHistory() {
    try {
      const data = await api("/api/evaluation/gate/history?limit=10");
      $("#evaluation-gate-history").innerHTML = (data.items || []).map(item =>
        '<div class="item"><b>' + esc(item.eligible ? "Eligible for human review" : "Blocked") +
        '</b><p><small>' + esc(new Date(item.created_at * 1000).toLocaleString()) +
        ' · window ' + esc(item.window_size) + ' · threshold ' +
        esc(Math.round(item.min_score * 100)) + '%</small></p><details><summary>Decision details</summary><pre>' +
        esc(JSON.stringify({reasons:item.reasons,recommendations:item.recommendations,run_ids:item.run_ids}, null, 2)) +
        '</pre></details></div>'
      ).join("") || "No gate decisions recorded yet.";
    } catch (e) {
      $("#evaluation-gate-history").textContent = e.message;
    }
  }
  $("#evaluation-gate-check")?.addEventListener("click", async () => {
    const button = $("#evaluation-gate-check");
    button.disabled = true;
    $("#evaluation-gate-result").textContent = "Assessing recent saved runs…";
    try {
      const result = await api("/api/evaluation/gate/check?window=3&min_score=1.0", {method:"POST", body:"{}"});
      $("#evaluation-gate-status").textContent = result.eligible ? "Human review eligible" : "Blocked";
      $("#evaluation-gate-count").textContent = result.runs_checked + " / " + result.window_size;
      $("#evaluation-gate-result").textContent = JSON.stringify(result, null, 2);
      note(result.eligible ? "Gate passed; human review still required" : "Gate blocked; inspect failed runs");
      await refreshGateHistory();
    } catch (e) {
      $("#evaluation-gate-result").textContent = e.message;
      note("Gate check failed");
    } finally {
      button.disabled = false;
    }
  });
  $("#evaluation-refresh")?.addEventListener("click", async () => {
    await refreshEvaluation();
    await refreshGateHistory();
  });
  const priorGo = go;
  go = function(v) {
    priorGo(v);
    if (v === "evaluation") { refreshEvaluation(); refreshGateHistory(); }
  };
})();