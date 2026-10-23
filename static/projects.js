(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  let selected = null, projects = [], workItems = [];
  const labels = {active:"Active",on_hold:"On hold",completed:"Completed",archived:"Archived",todo:"To do",in_progress:"In progress",blocked:"Blocked",done:"Done",low:"Low",medium:"Medium",high:"High",critical:"Critical"};
  const dateText = s => s ? esc(s) : "No due date";
  function projectPayload(){return {name:$("#pm-name").value.trim(),description:$("#pm-description").value,status:$("#pm-status").value,priority:$("#pm-priority").value,due_date:$("#pm-due-date").value};}
  function itemPayload(){return {title:$("#pm-item-title").value.trim(),description:$("#pm-item-description").value,status:$("#pm-item-status").value,priority:$("#pm-item-priority").value,due_date:$("#pm-item-due").value,dependency_id:$("#pm-item-dependency").value,milestone_id:$("#pm-item-milestone").value};}
  function resetProjectForm(){ $("#pm-project-form").reset();$("#pm-project-id").value="";$("#pm-form-title").textContent="Create a project";$("#pm-save-project").textContent="Create project";$("#pm-cancel-edit").classList.add("hidden"); }
  function resetItemForm(){ $("#pm-item-form").reset();$("#pm-item-id").value="";$("#pm-item-dependency").value="";$("#pm-item-milestone").value="";$("#pm-save-item").textContent="Add work item";$("#pm-cancel-item").classList.add("hidden"); }
  async function loadProjects(){
    const list=$("#pm-project-list");list.textContent="Loading workspace…";
    try{
      const d=await api("/api/projects");projects=d.items||[];
      $("#pm-project-count").textContent=d.summary.projects;$("#pm-item-count").textContent=d.summary.work_items;$("#pm-completed-count").textContent=d.summary.completed;$("#pm-blocked-count").textContent=d.summary.blocked;
      renderProjects();
      if(selected && projects.some(p=>p.id===selected)){const p=projects.find(p=>p.id===selected);renderSelectedProject(p);await loadItems();}
      else if(selected){selected=null;$("#pm-workspace").classList.add("hidden");}
    }catch(e){list.textContent=e.message;}
  }
  function renderProjects(){
    const q=$("#pm-search").value.trim().toLowerCase();
    const filtered=projects.filter(p=>(p.name+" "+p.description+" "+p.status).toLowerCase().includes(q));
    $("#pm-project-list").innerHTML=filtered.map(p=>'<button type="button" class="project-card '+(p.id===selected?"selected":"")+'" data-pm-select="'+esc(p.id)+'"><span class="project-card-top"><b>'+esc(p.name)+'</b><span class="status-pill status-'+esc(p.status)+'">'+esc(labels[p.status]||p.status)+'</span></span><span class="project-card-description">'+esc(p.description||"No description yet")+'</span><span class="project-card-meta"><span>'+esc(labels[p.priority]||p.priority)+' priority</span><span>'+p.completed_count+'/'+p.item_count+' items</span><span>'+dateText(p.due_date)+'</span></span><span class="progress-track"><span style="width:'+Number(p.progress||0)+'%"></span></span></button>').join("")||'<p class="empty-state">No matching projects. Create one to get started.</p>';
    document.querySelectorAll("[data-pm-select]").forEach(b=>b.onclick=()=>selectProject(b.dataset.pmSelect));
  }
  function renderSelectedProject(p){
    $("#pm-workspace").classList.remove("hidden");$("#pm-selected-title").textContent=p.name;$("#pm-selected-description").textContent=p.description||"No project description.";
    $("#pm-progress-fill").style.width=(p.progress||0)+"%";$("#pm-progress-label").textContent=(p.progress||0)+"% complete · "+p.completed_count+"/"+p.item_count+" work items";
  }
  async function selectProject(id){selected=id;const p=projects.find(x=>x.id===id);if(!p)return;renderProjects();renderSelectedProject(p);resetItemForm();await loadItems();await refreshProjectExtras();await loadMilestones();await loadActivity();$("#pm-workspace").scrollIntoView({behavior:"smooth",block:"start"});}
  async function loadItems(){
    if(!selected)return;
    try{const d=await api("/api/projects/"+encodeURIComponent(selected)+"/items");workItems=d.items||[];populateRelationSelectors();renderItems();}catch(e){$("#pm-work-list").textContent=e.message;}
  }
  function populateRelationSelectors(){
    const dep=$("#pm-item-dependency"), ms=$("#pm-item-milestone"), currentDep=dep.value, currentMs=ms.value, editing=$("#pm-item-id").value;
    dep.innerHTML='<option value="">No dependency</option>'+workItems.filter(i=>i.id!==editing).map(i=>'<option value="'+esc(i.id)+'">'+esc(i.title)+'</option>').join("");
    dep.value=currentDep;
    const milestoneCards=[...document.querySelectorAll("#pm-milestone-list [data-pm-edit-milestone]")];
    const milestoneOptions=window.__livingAIMilestones||[];
    ms.innerHTML='<option value="">No milestone</option>'+milestoneOptions.map(m=>'<option value="'+esc(m.id)+'">'+esc(m.title)+'</option>').join("");
    ms.value=currentMs;
  }
  function renderItems(){
    const filter=$("#pm-status-filter").value;
    const items=workItems.filter(i=>filter==="all"||i.status===filter);
    $("#pm-work-list").innerHTML=items.map(i=>'<div class="work-item"><div class="work-item-heading"><b>'+esc(i.title)+'</b><span class="status-pill status-'+esc(i.status)+'">'+esc(labels[i.status]||i.status)+'</span></div><p>'+esc(i.description||"No details provided.")+'</p><div class="project-card-meta"><span class="priority-'+esc(i.priority)+'">'+esc(labels[i.priority]||i.priority)+' priority</span><span>'+dateText(i.due_date)+'</span></div><div class="button-row"><button type="button" class="secondary small-button" data-pm-edit-item="'+esc(i.id)+'">Edit</button><button type="button" class="danger small-button" data-pm-delete-item="'+esc(i.id)+'">Delete</button></div></div>').join("")||'<p class="empty-state">No items in this view yet.</p>';
    document.querySelectorAll("[data-pm-edit-item]").forEach(b=>b.onclick=()=>editItem(b.dataset.pmEditItem));
    document.querySelectorAll("[data-pm-delete-item]").forEach(b=>b.onclick=()=>removeItem(b.dataset.pmDeleteItem));
  }
  async function loadMilestones(){
    if(!selected)return;
    try{
      const d=await api("/api/projects/"+encodeURIComponent(selected)+"/milestones"), items=d.items||[];window.__livingAIMilestones=items;populateRelationSelectors();
      const statuses={planned:"Planned",in_progress:"In progress",completed:"Completed",at_risk:"At risk"};
      $("#pm-milestone-list").innerHTML=items.map(m=>'<div class="work-item"><div class="work-item-heading"><b>'+esc(m.title)+'</b><span class="status-pill">'+esc(statuses[m.status]||m.status)+'</span></div><p>'+esc(m.description||"No description.")+'</p><div class="project-card-meta"><span>'+dateText(m.due_date)+'</span></div><div class="button-row"><button type="button" class="secondary small-button" data-pm-edit-milestone="'+esc(m.id)+'">Edit</button><button type="button" class="danger small-button" data-pm-delete-milestone="'+esc(m.id)+'">Delete</button></div></div>').join("")||'<p class="empty-state">No milestones yet.</p>';
      document.querySelectorAll("[data-pm-edit-milestone]").forEach(b=>b.onclick=()=>editMilestone(b.dataset.pmEditMilestone,items));
      document.querySelectorAll("[data-pm-delete-milestone]").forEach(b=>b.onclick=()=>removeMilestone(b.dataset.pmDeleteMilestone));
    }catch(e){$("#pm-milestone-list").textContent=e.message;}
  }
  async function loadActivity(){
    if(!selected)return;
    try{
      const d=await api("/api/projects/"+encodeURIComponent(selected)+"/activity"), items=d.items||[];
      $("#pm-activity-list").innerHTML=items.map(a=>'<div class="work-item"><div class="work-item-heading"><b>'+esc(a.action.replace(/_/g," "))+'</b><small>'+esc(new Date(a.created_at).toLocaleString())+'</small></div><p>'+esc(a.detail||"")+'</p></div>').join("")||'<p class="empty-state">No activity recorded yet.</p>';
    }catch(e){$("#pm-activity-list").textContent=e.message;}
  }
  function resetMilestoneForm(){$("#pm-milestone-form").reset();$("#pm-milestone-id").value="";$("#pm-save-milestone").textContent="Add milestone";$("#pm-cancel-milestone").classList.add("hidden");}
  function editMilestone(id,items){const m=items.find(x=>x.id===id);if(!m)return;$("#pm-milestone-id").value=m.id;$("#pm-milestone-title").value=m.title;$("#pm-milestone-description").value=m.description;$("#pm-milestone-status").value=m.status;$("#pm-milestone-due").value=m.due_date||"";$("#pm-save-milestone").textContent="Save milestone";$("#pm-cancel-milestone").classList.remove("hidden");}
  async function removeMilestone(id){if(!confirm("Delete this milestone?"))return;try{await api("/api/projects/"+encodeURIComponent(selected)+"/milestones/"+encodeURIComponent(id),{method:"DELETE"});note("Milestone deleted");await refreshProjectExtras();}catch(e){note(e.message);}}
  async function refreshProjectExtras(){await Promise.all([loadMilestones(),loadActivity()]);}
  function editProject(id){const p=projects.find(x=>x.id===id);if(!p)return;$("#pm-project-id").value=p.id;$("#pm-name").value=p.name;$("#pm-description").value=p.description;$("#pm-status").value=p.status;$("#pm-priority").value=p.priority;$("#pm-due-date").value=p.due_date||"";$("#pm-form-title").textContent="Edit project";$("#pm-save-project").textContent="Save changes";$("#pm-cancel-edit").classList.remove("hidden");$("#pm-editor").scrollIntoView({behavior:"smooth",block:"start"});}
  function editItem(id){const i=workItems.find(x=>x.id===id);if(!i)return;$("#pm-item-id").value=i.id;$("#pm-item-title").value=i.title;$("#pm-item-description").value=i.description;$("#pm-item-status").value=i.status;$("#pm-item-priority").value=i.priority;$("#pm-item-due").value=i.due_date||"";$("#pm-item-dependency").value=i.dependency_id||"";$("#pm-item-milestone").value=i.milestone_id||"";$("#pm-save-item").textContent="Save work item";$("#pm-cancel-item").classList.remove("hidden");$("#pm-item-form").scrollIntoView({behavior:"smooth",block:"center"});}
  async function removeItem(id){const item=workItems.find(x=>x.id===id);if(!item||!confirm('Delete work item "'+item.title+'"?'))return;try{await api("/api/projects/"+encodeURIComponent(selected)+"/items/"+encodeURIComponent(id),{method:"DELETE"});note("Work item deleted");await loadProjects();}catch(e){note(e.message);}}
  $("#pm-project-form")?.addEventListener("submit",async e=>{e.preventDefault();const id=$("#pm-project-id").value;try{const p=await api(id?"/api/projects/"+encodeURIComponent(id):"/api/projects",{method:id?"PATCH":"POST",body:JSON.stringify(projectPayload())});selected=p.id;resetProjectForm();note(id?"Project updated":"Project created");await loadProjects();await selectProject(p.id);}catch(err){note(err.message);}});
  $("#pm-cancel-edit")?.addEventListener("click",resetProjectForm);
  $("#pm-item-form")?.addEventListener("submit",async e=>{e.preventDefault();if(!selected){note("Select a project first");return;}const id=$("#pm-item-id").value;try{await api("/api/projects/"+encodeURIComponent(selected)+"/items"+(id?"/"+encodeURIComponent(id):""),{method:id?"PATCH":"POST",body:JSON.stringify(itemPayload())});resetItemForm();note(id?"Work item updated":"Work item added");await loadProjects();}catch(err){note(err.message);}});
  $("#pm-cancel-item")?.addEventListener("click",resetItemForm);
  $("#pm-milestone-form")?.addEventListener("submit",async e=>{e.preventDefault();if(!selected){note("Select a project first");return;}const id=$("#pm-milestone-id").value;const payload={title:$("#pm-milestone-title").value.trim(),description:$("#pm-milestone-description").value,status:$("#pm-milestone-status").value,due_date:$("#pm-milestone-due").value};try{await api("/api/projects/"+encodeURIComponent(selected)+"/milestones"+(id?"/"+encodeURIComponent(id):""),{method:id?"PATCH":"POST",body:JSON.stringify(payload)});resetMilestoneForm();note(id?"Milestone updated":"Milestone added");await refreshProjectExtras();}catch(err){note(err.message);}});
  $("#pm-cancel-milestone")?.addEventListener("click",resetMilestoneForm);
  $("#pm-refresh-milestones")?.addEventListener("click",loadMilestones);
  $("#pm-refresh-activity")?.addEventListener("click",loadActivity);
  $("#pm-delete-project")?.addEventListener("click",async()=>{const p=projects.find(x=>x.id===selected);if(!p||!confirm('Delete project "'+p.name+'" and all its work items? This cannot be undone.'))return;try{await api("/api/projects/"+encodeURIComponent(selected),{method:"DELETE"});selected=null;$("#pm-workspace").classList.add("hidden");resetProjectForm();note("Project deleted");await loadProjects();}catch(e){note(e.message);}});
  $("#pm-export")?.addEventListener("click",async()=>{try{const data=await api("/api/projects/export");const blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="living-ai-projects-"+new Date().toISOString().slice(0,10)+".json";document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);note("Project backup exported");}catch(e){note(e.message);}});
  $("#pm-import-file")?.addEventListener("change",async e=>{const file=e.target.files?.[0];if(!file)return;if(file.size>10*1024*1024){note("Backup file must be smaller than 10 MB");e.target.value="";return;}if(!confirm("Import this backup as new project copies? Existing projects will not be overwritten.")){e.target.value="";return;}try{const data=JSON.parse(await file.text());const result=await api("/api/projects/import",{method:"POST",body:JSON.stringify(data)});note("Imported "+result.projects+" projects, "+result.milestones+" milestones and "+result.work_items+" work items");selected=null;$("#pm-workspace").classList.add("hidden");await loadProjects();}catch(err){note("Import failed: "+err.message);}finally{e.target.value="";}});
  $("#pm-refresh")?.addEventListener("click",loadProjects);
  $("#pm-search")?.addEventListener("input",renderProjects);
  $("#pm-status-filter")?.addEventListener("change",renderItems);
  $("#new-project-focus")?.addEventListener("click",()=>{resetProjectForm();$("#pm-editor").scrollIntoView({behavior:"smooth",block:"start"});$("#pm-name").focus();});

  async function loadMilestones(){
    if(!selected)return;
    try{const d=await api("/api/projects/"+encodeURIComponent(selected)+"/milestones");const ms=d.items||[];
      $("#pm-milestone-list").innerHTML=ms.map(m=>'<div class="work-item"><b>'+esc(m.title)+'</b> · '+esc(labels[m.status]||m.status)+'<p>'+esc(m.description||"")+'</p><small>'+dateText(m.due_date)+'</small><div class="button-row"><button type="button" class="secondary small-button" data-m-edit="'+esc(m.id)+'">Edit</button><button type="button" class="danger small-button" data-m-delete="'+esc(m.id)+'">Delete</button></div></div>').join("")||'<p class="empty-state">No milestones yet.</p>';
      document.querySelectorAll("[data-m-edit]").forEach(b=>b.onclick=()=>{const m=ms.find(x=>x.id===b.dataset.mEdit);if(!m)return;$("#pm-milestone-id").value=m.id;$("#pm-milestone-title").value=m.title;$("#pm-milestone-description").value=m.description;$("#pm-milestone-status").value=m.status;$("#pm-milestone-due").value=m.due_date||"";$("#pm-save-milestone").textContent="Save milestone";$("#pm-cancel-milestone").classList.remove("hidden");});
      document.querySelectorAll("[data-m-delete]").forEach(b=>b.onclick=async()=>{const m=ms.find(x=>x.id===b.dataset.mDelete);if(!m||!confirm("Delete milestone?"))return;try{await api("/api/projects/"+encodeURIComponent(selected)+"/milestones/"+encodeURIComponent(m.id),{method:"DELETE"});await loadMilestones();await loadActivity();}catch(e){note(e.message);}});
    }catch(e){$("#pm-milestone-list").textContent=e.message;}
  }
  async function loadActivity(){if(!selected)return;try{const d=await api("/api/projects/"+encodeURIComponent(selected)+"/activity");$("#pm-activity-list").innerHTML=(d.items||[]).map(a=>'<div class="work-item"><b>'+esc(a.action.replaceAll("_"," "))+'</b><p>'+esc(a.detail)+'</p><small>'+esc(a.created_at)+'</small></div>').join("")||'<p class="empty-state">No activity yet.</p>';}catch(e){$("#pm-activity-list").textContent=e.message;}}
  $("#pm-milestone-form")?.addEventListener("submit",async e=>{e.preventDefault();if(!selected){note("Select a project first");return;}const id=$("#pm-milestone-id").value;const payload={title:$("#pm-milestone-title").value.trim(),description:$("#pm-milestone-description").value,status:$("#pm-milestone-status").value,due_date:$("#pm-milestone-due").value};try{await api("/api/projects/"+encodeURIComponent(selected)+"/milestones"+(id?"/"+encodeURIComponent(id):""),{method:id?"PATCH":"POST",body:JSON.stringify(payload)});$("#pm-milestone-form").reset();$("#pm-milestone-id").value="";$("#pm-save-milestone").textContent="Add milestone";$("#pm-cancel-milestone").classList.add("hidden");await loadMilestones();await loadActivity();}catch(err){note(err.message);}});
  $("#pm-cancel-milestone")?.addEventListener("click",()=>{$("#pm-milestone-form").reset();$("#pm-milestone-id").value="";$("#pm-save-milestone").textContent="Add milestone";$("#pm-cancel-milestone").classList.add("hidden");});
  $("#pm-refresh-milestones")?.addEventListener("click",loadMilestones);$("#pm-refresh-activity")?.addEventListener("click",loadActivity);
  if(typeof go==="function"){const oldGo=go;go=function(v){oldGo(v);if(v==="projects")loadProjects();};}
  document.querySelectorAll('[data-view="projects"]').forEach(b=>b.addEventListener("click",loadProjects));
})();