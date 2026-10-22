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
  $("#evaluation-refresh")?.addEventListener("click", refreshEvaluation);
  const priorGo = go;
  go = function(v) {
    priorGo(v);
    if (v === "evaluation") refreshEvaluation();
  };
})();