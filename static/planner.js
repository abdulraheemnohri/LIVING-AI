(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  let preparedPlanId = null;

  async function refreshPlanner() {
    try {
      const [plans, summary] = await Promise.all([
        api("/api/planner/proposals?limit=30"),
        api("/api/planner/learning-summary")
      ]);
      $("#planner-list").innerHTML = plans.items.map(p =>
        '<div class="item"><b>' + esc(p.goal) + '</b><p><small>' + esc(p.status) + ' · ' +
        esc(p.backend) + ' · ' + esc(p.step_count) + ' steps</small></p><small>Plan: ' +
        esc(p.plan_id) + '</small></div>'
      ).join("") || "No prepared plans yet.";
      $("#planner-learning-summary").textContent = JSON.stringify(summary, null, 2);
    } catch (e) {
      $("#planner-list").textContent = e.message;
      $("#planner-learning-summary").textContent = e.message;
    }
  }

  $("#plannerform")?.addEventListener("submit", async e => {
    e.preventDefault();
    const out = $("#planner-result");
    out.textContent = "Preparing plan…";
    $("#planner-submit").disabled = true;
    preparedPlanId = null;
    try {
      const result = await api("/api/planner/prepare", {method:"POST", body:JSON.stringify({
        goal:$("#plannerggoal").value,
        allow_remote:$("#plannerremote").checked,
        memory_limit:Number($("#planner-memory-limit").value)
      })});
      preparedPlanId = result.plan.plan_id;
      out.textContent = JSON.stringify(result, null, 2);
      $("#planner-submit").disabled = false;
      note("Plan prepared for review; nothing executed");
      await refreshPlanner();
    } catch (err) {
      out.textContent = err.message;
      note("Could not prepare plan");
    }
  });

  $("#planner-submit")?.addEventListener("click", async () => {
    if (!preparedPlanId) return;
    if (!confirm("Queue this prepared plan for review? This does not execute any action.")) return;
    try {
      const result = await api("/api/planner/submit", {method:"POST", body:JSON.stringify({plan_id:preparedPlanId})});
      $("#planner-result").textContent = JSON.stringify(result, null, 2);
      $("#planner-submit").disabled = true;
      preparedPlanId = null;
      note("Plan queued; execution not performed");
      await refreshPlanner();
    } catch (err) { note(err.message); }
  });

  $("#planner-refresh")?.addEventListener("click", refreshPlanner);
  $("#evaluationform")?.addEventListener("submit", async e => {
    e.preventDefault();
    try {
      const result = await api("/api/planner/evaluations", {method:"POST", body:JSON.stringify({
        goal:$("#evalgoal").value,
        score:Number($("#evalscore").value),
        outcome:$("#evaloutcome").value,
        feedback:$("#evalfeedback").value,
        plan_summary:$("#evalsummary").value,
        tags:[]
      })});
      note("Evaluation saved to local learning memory");
      $("#evaluationform").reset();
      $("#evalscore").value = "0.8";
      await refreshPlanner();
    } catch (err) { note(err.message); }
  });

  const priorGo = go;
  go = function(v) {
    priorGo(v);
    if (v === "planner") refreshPlanner();
  };
})();
