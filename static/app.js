const $=s=>document.querySelector(s);let token=sessionStorage.getItem("living-ai-token")||"";const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));async function api(path,opt={}){opt.headers={...(opt.headers||{}),"Content-Type":"application/json",...(token?{Authorization:"Bearer "+token}:{})};let r=await fetch(path,opt),d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||r.statusText);return d}function note(t){$("#notice").textContent=t;setTimeout(()=>$("#notice").textContent="",4000)}function go(v){document.querySelectorAll(".view").forEach(x=>x.classList.add("hidden"));$("#"+v).classList.remove("hidden");$("#title").textContent=v[0].toUpperCase()+v.slice(1);document.querySelectorAll("[data-view]").forEach(b=>b.classList.toggle("active",b.dataset.view===v));if(v==="memory")loadMemory();if(v==="evolution")loadProposals();if(v==="audit")loadAudit()}document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>go(b.dataset.view));async function status(){try{let d=await api("/api/status");$("#memories").textContent=d.memories;$("#proposals").textContent=d.proposals;$("#model").textContent=d.original_model_trained?"Trained":"Not trained";$("#status").textContent=JSON.stringify(d,null,2)}catch(e){note(e.message)}}$("#refresh").onclick=status;function bubble(role,text){let n=document.createElement("div");n.className="bubble "+role;n.innerHTML="<b>"+role+"</b><p>"+esc(text)+"</p>";$("#chatlog").append(n);$("#chatlog").scrollTop=$("#chatlog").scrollHeight}$("#chatform").onsubmit=async e=>{e.preventDefault();let m=$("#message").value.trim();if(!m)return;$("#message").value="";bubble("user",m);try{let d=await api("/api/chat",{method:"POST",body:JSON.stringify({message:m})});bubble("ai",d.answer+"\n["+d.backend+"]")}catch(x){bubble("ai",x.message)}};$("#memform").onsubmit=async e=>{e.preventDefault();try{await api("/api/memories",{method:"POST",body:JSON.stringify({content:$("#memcontent").value,source:$("#memsource").value})});$("#memcontent").value="";note("Saved");loadMemory();status()}catch(x){note(x.message)}};$("#searchform").onsubmit=e=>{e.preventDefault();loadMemory($("#query").value)};async function loadMemory(q=""){try{let d=await api("/api/memories?q="+encodeURIComponent(q));$("#memlist").innerHTML=d.items.map(m=>'<div class="item"><small>#'+m.id+" · "+esc(m.source)+"</small><p>"+esc(m.content)+"</p><button data-del='"+m.id+"'>Delete</button></div>").join("")||"No memories";document.querySelectorAll("[data-del]").forEach(b=>b.onclick=async()=>{try{await api("/api/memories/"+b.dataset.del,{method:"DELETE"});loadMemory(q);status()}catch(e){note(e.message)}})}catch(e){note(e.message)}}$("#train").onclick=async()=>{try{let d=await api("/api/training/train",{method:"POST",body:JSON.stringify({input_dir:"data/corpus"})});$("#trainresult").textContent=JSON.stringify(d,null,2);note("Model trained");status()}catch(e){$("#trainresult").textContent=e.message}};$("#proposalform").onsubmit=async e=>{e.preventDefault();let k=$("#pkey").value,v=Number($("#pvalue").value);if(k!=="temperature")v=Math.round(v);try{let p=await api("/api/evolution/proposals",{method:"POST",body:JSON.stringify({title:$("#ptitle").value,changes:{[k]:v}})});await api("/api/evolution/proposals/"+p.id+"/evaluate",{method:"POST",body:"{}"});note("Proposal evaluated");loadProposals();status()}catch(x){note(x.message)}};async function loadProposals(){try{let d=await api("/api/evolution/proposals");$("#plist").innerHTML=d.items.map(p=>'<div class="item"><b>#'+p.id+" "+esc(p.title)+"</b><p>"+esc(JSON.stringify(p.changes))+" · "+esc(p.status)+"</p>"+(p.status==="evaluated"?'<button data-promote="'+p.id+'">Promote</button>':"")+"</div>").join("")||"No proposals";document.querySelectorAll("[data-promote]").forEach(b=>b.onclick=async()=>{try{await api("/api/evolution/proposals/"+b.dataset.promote+"/promote",{method:"POST",body:"{}"});note("Promoted with snapshot");loadProposals();status()}catch(e){note(e.message)}})}catch(e){note(e.message)}}$("#rollback").onclick=async()=>{if(!confirm("Rollback latest settings snapshot?"))return;try{await api("/api/evolution/rollback",{method:"POST",body:"{}"});note("Rolled back");status()}catch(e){note(e.message)}};async function loadAudit(){try{let d=await api("/api/audit");$("#auditlist").innerHTML=d.items.map(a=>'<div class="item"><small>'+esc(a.created_at)+"</small><p><b>"+esc(a.action)+"</b><br>"+esc(JSON.stringify(a.detail))+"</p></div>").join("")||"No audit events"}catch(e){note(e.message)}}
function loadModelStatus(){api("/api/model/status").then(d=>{$("#modelstatus").textContent=JSON.stringify(d,null,2)}).catch(e=>{$("#modelstatus").textContent=e.message})}
$("#tokenform").onsubmit=e=>{e.preventDefault();token=$("#admintoken").value.trim();if(token)sessionStorage.setItem("living-ai-token",token);else sessionStorage.removeItem("living-ai-token");note(token?"Token saved for this tab":"Token cleared");$("#admintoken").value=""};
$("#cleartoken").onclick=()=>{token="";sessionStorage.removeItem("living-ai-token");$("#admintoken").value="";note("Token cleared for this tab")};
$("#refreshmodel").onclick=loadModelStatus;
const originalGo=go;
go=function(v){originalGo(v);if(v==="settings")loadModelStatus()};
status();

$("#scratchform").onsubmit=async e=>{e.preventDefault();const out=$("#scratchresult");out.textContent="Training started; keep this page open. CPU training can take time.";try{const d=await api("/api/training/train-from-scratch",{method:"POST",body:JSON.stringify({input_dir:"data/corpus",output_dir:"models/tiny_transformer",steps:Number($("#scratchsteps").value),batch_size:Number($("#scratchbatch").value),width:Number($("#scratchwidth").value),heads:4,layers:2,block_size:Number($("#scratchblock").value),seed:42})});out.textContent=JSON.stringify(d,null,2);note("From-scratch training finished");status()}catch(err){out.textContent=err.message;note("Training failed")}};

async function importLocalFiles(){
 const input=$("#knowledgefiles"),out=$("#fileimportresult");out.textContent="";
 const files=Array.from(input.files||[]);if(!files.length){out.textContent="Choose at least one file.";return}
 const results=[];
 for(const file of files){
  try{
   if(file.size>2_000_000)throw Error("File is over 2 MB");
   const content=await file.text();
   const data=await api("/api/knowledge/ingest-file",{method:"POST",body:JSON.stringify({filename:file.name,content})});
   results.push({file:file.name,ok:true,chunks:data.chunks,characters:data.characters});
  }catch(e){results.push({file:file.name,ok:false,error:e.message})}
  out.textContent=JSON.stringify(results,null,2);
 }
 note("File import finished");status();
}
if($("#fileimportform"))$("#fileimportform").onsubmit=async e=>{e.preventDefault();await importLocalFiles()};
if($("#urlimportform"))$("#urlimportform").onsubmit=async e=>{e.preventDefault();const out=$("#urlimportresult");out.textContent="Fetching public webpage…";try{const d=await api("/api/knowledge/ingest-url",{method:"POST",body:JSON.stringify({url:$("#knowledgeurl").value.trim()})});out.textContent=JSON.stringify({ingested:d.ingested,url:d.url,chunks:d.chunks,characters:d.characters},null,2);note("Webpage imported into local memory");status()}catch(err){out.textContent=err.message;note("Website import failed")}};

if($("#exportcorpus"))$("#exportcorpus").onclick=async()=>{const out=$("#exportcorpusresult");out.textContent="Exporting saved memories…";try{const d=await api("/api/knowledge/export-corpus",{method:"POST",body:"{}"});out.textContent=JSON.stringify(d,null,2);note("Training corpus updated")}catch(e){out.textContent=e.message;note("Export failed")}};

async function loadEvaluations(q=""){
 try{
  const [summary,history]=await Promise.all([api("/api/evaluations/summary"),api("/api/evaluations?q="+encodeURIComponent(q)+"&limit=20")]);
  $("#evalcount").textContent=summary.evaluations;
  $("#evalaverage").textContent=summary.average_score===null?"—":(summary.average_score*100).toFixed(1)+"%";
  $("#evalpositive").textContent=summary.positive_evaluations;
  $("#evallist").innerHTML=history.items.map(x=>'<div class="item"><b>'+esc(x.goal)+'</b><p><small>Score '+(Number(x.score)*100).toFixed(0)+'% · '+esc(new Date(x.created_at*1000).toLocaleString())+'</small></p><p>'+esc(x.outcome)+'</p><p>'+esc(x.feedback||"")+'</p><small>'+esc((x.tags||[]).join(", "))+'</small></div>').join("")||"No evaluations found.";
 }catch(e){$("#evallist").textContent=e.message;note(e.message)}
}
if($("#evalform")) $("#evalform").onsubmit=async e=>{
 e.preventDefault();
 try{
  const d=await api("/api/evaluations",{method:"POST",body:JSON.stringify({goal:$("#evalgoal").value,score:Number($("#evalscore").value),outcome:$("#evaloutcome").value,feedback:$("#evalfeedback").value,plan_summary:$("#evalsummary").value,tags:$("#evaltags").value.split(",").map(x=>x.trim()).filter(Boolean).slice(0,20)})});
  $("#evalresult").textContent=JSON.stringify(d,null,2);$("#evalform").reset();$("#evalscore").value="0.8";note("Evaluation saved locally");loadEvaluations();
 }catch(e){$("#evalresult").textContent=e.message;note("Could not save evaluation")}
};
if($("#evalsearchform")) $("#evalsearchform").onsubmit=e=>{e.preventDefault();loadEvaluations($("#evalquery").value)};
const previousEvaluationGo=go;
go=function(v){previousEvaluationGo(v);if(v==="evaluation")loadEvaluations()};
