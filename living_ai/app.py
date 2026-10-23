import os,json
from pathlib import Path
from typing import Any
from litestar import Litestar,get,post,delete,Request
from litestar.exceptions import HTTPException
from litestar.response import Response
from litestar.static_files import StaticFilesConfig
from pydantic import BaseModel,Field
from .db import init_db,connect,get_settings,data_dir
from .memory import add_memory,search_memories,delete_memory
from .engine import respond
from .training import train_directory
from .training_lab import list_datasets, ingest_dataset, prepare_teacher_corpus, training_history, approve_teacher_candidate, stage_for_training
from .neural_training import train_small_transformer
from .knowledge import parse_document, split_text, fetch_public_page
from .evolution import create_proposal,list_proposals,evaluate,promote,rollback
from .planner_api import planner_prepare,planner_proposals,planner_submit,planner_record_evaluation,planner_learning_summary
from .worker_api import worker_status,worker_resume,worker_pause,worker_enable,worker_disable,worker_configure,worker_tick,worker_approve_goal,worker_recommendations
from .evaluation_api import evaluation_run,evaluation_runs
from .promotion_gate import evaluation_gate_check,evaluation_gate_history
from .dataset_lab import dataset_add_example,dataset_list_examples,dataset_review_example,dataset_export
from .task_api import tasks_list,tasks_submit,task_detail,task_events,tasks_run_once,task_retry,task_approve
from .project_api import list_projects,create_project,update_project,delete_project,list_work_items,create_work_item,update_work_item,delete_work_item
from .project_extensions import list_milestones,create_milestone,update_milestone,delete_milestone,project_activity
import hmac
ROOT=Path(__file__).resolve().parent.parent
def auth(req):
    """Fail closed: state-changing admin routes are unavailable until a token is configured."""
    password=os.getenv("LIVING_AI_ADMIN_PASSWORD","").strip()
    if not password:
        raise HTTPException(status_code=503,detail="Admin routes are locked: configure LIVING_AI_ADMIN_PASSWORD and restart")
    if not hmac.compare_digest(req.headers.get("x-admin-password",""), password):
        raise HTTPException(status_code=401,detail="Valid admin password required")
class Chat(BaseModel): message:str=Field(min_length=1,max_length=20000)
class Memory(BaseModel): content:str=Field(min_length=1,max_length=100000);source:str="manual"
class FileIngest(BaseModel): filename:str=Field(min_length=1,max_length=255);content:str=Field(min_length=1,max_length=2_500_000)
class URLIngest(BaseModel): url:str=Field(min_length=8,max_length=2048)
class Proposal(BaseModel): title:str;changes:dict
class Train(BaseModel): input_dir:str="data/corpus"
class DatasetUpload(BaseModel):
    filename:str=Field(min_length=1,max_length=255)
    content:str=Field(min_length=1,max_length=2_000_000)
    source:str=Field(default="manual-upload",max_length=100)
class TeacherPrepare(BaseModel):
    text:str=Field(min_length=1,max_length=12000)
    count:int=Field(default=3,ge=1,le=8)
class TrainScratch(BaseModel):
    input_dir:str="data/corpus"
    output_dir:str="models/tiny_transformer"
    steps:int=Field(default=500,ge=1,le=5000)
    batch_size:int=Field(default=4,ge=1,le=8)
    learning_rate:float=Field(default=0.0003,ge=0.000001,le=0.1)
    block_size:int=Field(default=64,ge=16,le=256)
    width:int=Field(default=64,ge=32,le=256)
    heads:int=Field(default=4,ge=1,le=8)
    layers:int=Field(default=2,ge=1,le=4)
    seed:int=42
@get("/")
async def index() -> Response:
    html=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
    return Response(content=html, media_type="text/html; charset=utf-8", headers={"Content-Disposition": "inline"})
@get("/api/health")
async def health() -> dict[str, Any]:return {"ok":True,"name":"LIVING AI","version":"0.4.0"}
@get("/api/status")
async def status(request: Request) -> dict[str, Any]:
    auth(request)
    with connect() as c: n=c.execute("SELECT COUNT(*) n FROM memories").fetchone()["n"];p=c.execute("SELECT COUNT(*) n FROM proposals").fetchone()["n"]
    return {"status":"running","memories":n,"proposals":p,"original_model_trained":(ROOT/"models"/"char_ngram.json").exists(),"tiny_transformer_trained":(ROOT/"models"/"tiny_transformer"/"weights.pt").exists(),"settings":get_settings(),"data_dir":str(data_dir())}
@post("/api/chat")
async def chat(data:Chat) -> dict[str, Any]:
    try:return respond(data.message)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@get("/api/memories")
async def memories(request: Request, q:str="",limit:int=20) -> dict[str, Any]:
    auth(request)
    return {"items":search_memories(q,limit)}
@post("/api/memories")
async def add(data:Memory,request:Request) -> dict[str, Any]:
    auth(request)
    try:return add_memory(data.content,data.source)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@delete("/api/memories/{memory_id:int}", status_code=200)
async def remove(memory_id:int,request:Request) -> dict[str, Any]:
    auth(request)
    if not delete_memory(memory_id):raise HTTPException(status_code=404,detail="Memory not found")
    return {"deleted":True,"id":memory_id}
@post("/api/knowledge/ingest")
async def ingest(data:Memory,request:Request) -> dict[str, Any]:
    auth(request);return {"ingested":True,"memory":add_memory(data.content,data.source)}
@post("/api/knowledge/ingest-file")
async def ingest_file(data:FileIngest,request:Request) -> dict[str, Any]:
    auth(request)
    try:
        text=parse_document(data.filename,data.content)
        chunks=split_text(text)
        if len(chunks)>100: raise ValueError("File creates too many chunks; split the file or use a smaller file")
        saved=[add_memory(chunk,f"file:{Path(data.filename).name}#part-{index}") for index,chunk in enumerate(chunks,1)]
        return {"ingested":True,"filename":Path(data.filename).name,"chunks":len(saved),"characters":len(text),"items":saved}
    except ValueError as e: raise HTTPException(status_code=400,detail=str(e))
@post("/api/knowledge/ingest-url", sync_to_thread=True)
def ingest_url(data:URLIngest,request:Request) -> dict[str, Any]:
    auth(request)
    try:
        text,url=fetch_public_page(data.url)
        chunks=split_text(text)
        if len(chunks)>100: raise ValueError("Page creates too many chunks; use a more focused URL")
        saved=[add_memory(chunk,f"url:{url}#part-{index}") for index,chunk in enumerate(chunks,1)]
        return {"ingested":True,"url":url,"chunks":len(saved),"characters":len(text),"items":saved}
    except ValueError as e: raise HTTPException(status_code=400,detail=str(e))
@post("/api/knowledge/export-corpus")
async def export_corpus(request:Request) -> dict[str, Any]:
    auth(request)
    target=data_dir()/"corpus"/"imported_memory_corpus.txt"
    target.parent.mkdir(parents=True,exist_ok=True)
    with connect() as db:
        rows=db.execute("SELECT source,content FROM memories ORDER BY id ASC").fetchall()
    parts=[]
    total=0
    for row in rows:
        piece=f"Source: {row['source']}\n{row['content']}\n\n"
        size=len(piece.encode("utf-8"))
        if total+size>5_000_000: break
        parts.append(piece);total+=size
    if not parts: raise HTTPException(status_code=400,detail="No saved memories to export")
    temp=target.with_suffix(".txt.tmp")
    temp.write_text("".join(parts),encoding="utf-8")
    temp.replace(target)
    return {"exported":True,"path":str(target),"documents":len(parts),"bytes":total,"note":"Review licensing and quality before training."}
@post("/api/training/train")
async def train(data:Train,request:Request) -> dict[str, Any]:
    auth(request)
    try:return train_directory(data.input_dir)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))

@get("/api/training/datasets")
async def training_datasets(request: Request) -> dict[str, Any]:
    auth(request)
    return {"items": list_datasets()}

@post("/api/training/datasets")
async def upload_training_dataset(data: DatasetUpload, request: Request) -> dict[str, Any]:
    auth(request)
    try:
        return ingest_dataset(data.filename, data.content, data.source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@post("/api/training/teacher-prepare")
async def teacher_prepare(data: TeacherPrepare, request: Request) -> dict[str, Any]:
    auth(request)
    try:
        return prepare_teacher_corpus(data.text, data.count)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@post("/api/training/teacher-approve/{candidate_id:str}")
async def teacher_approve(candidate_id: str, request: Request) -> dict[str, Any]:
    auth(request)
    try:
        return approve_teacher_candidate(candidate_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@post("/api/training/stage/{kind:str}/{item_id:str}")
async def stage_training_item(kind: str, item_id: str, request: Request) -> dict[str, Any]:
    auth(request)
    try:
        return stage_for_training(item_id, kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@get("/api/training/history")
async def training_runs(request: Request) -> dict[str, Any]:
    auth(request)
    return {"items": training_history()}

@get("/api/evolution/proposals")
async def proposals(request: Request) -> dict[str, Any]:
    auth(request)
    return {"items":list_proposals()}
@post("/api/evolution/proposals")
async def propose(data:Proposal,request:Request) -> dict[str, Any]:
    auth(request)
    try:return create_proposal(data.title,data.changes)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@post("/api/evolution/proposals/{proposal_id:int}/evaluate")
async def eval_route(proposal_id:int,request:Request) -> dict[str, Any]:
    auth(request)
    try:return evaluate(proposal_id)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@post("/api/evolution/proposals/{proposal_id:int}/promote")
async def promote_route(proposal_id:int,request:Request) -> dict[str, Any]:
    auth(request)
    try:return promote(proposal_id)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@post("/api/evolution/rollback")
async def rollback_route(request:Request) -> dict[str, Any]:
    auth(request)
    try:return rollback()
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@get("/api/audit")
async def audit(request: Request, limit:int=50) -> dict[str, Any]:
    auth(request)
    with connect() as c:rows=c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?",(max(1,min(limit,200)),)).fetchall()
    return {"items":[{"id":r["id"],"action":r["action"],"detail":json.loads(r["detail_json"]),"created_at":r["created_at"]} for r in rows]}
@get("/api/settings")
async def settings(request: Request) -> dict[str, Any]:
    auth(request)
    return {"settings":get_settings(),"auto_promote":os.getenv("LIVING_AI_AUTO_PROMOTE","false").lower()=="true"}

@post("/api/training/train-from-scratch", sync_to_thread=True)
def train_scratch(data:TrainScratch,request:Request) -> dict[str, Any]:
    auth(request)
    if data.width % data.heads: raise HTTPException(status_code=400,detail="width must be divisible by heads")
    allowed_input=(data_dir()/"corpus").resolve()
    output_path=Path(data.output_dir).expanduser().resolve()
    allowed_output=(ROOT/"models"/"tiny_transformer").resolve()
    input_path=allowed_input
    if output_path != allowed_output:
        raise HTTPException(status_code=400,detail="Training output is fixed to models/tiny_transformer")
    try:
        return train_small_transformer(input_dir=str(input_path),output_dir=str(output_path),steps=data.steps,batch_size=data.batch_size,learning_rate=data.learning_rate,seed=data.seed,config_overrides={"block_size":data.block_size,"d_model":data.width,"n_heads":data.heads,"n_layers":data.layers})
    except (ValueError,RuntimeError) as e: raise HTTPException(status_code=400,detail=str(e))
@get("/api/model/status")
async def model_status(request: Request) -> dict[str, Any]:
    auth(request)
    backend=os.getenv("LIVING_AI_MODEL_BACKEND","char_ngram").strip().lower()
    allowed={"char_ngram","tiny_transformer","from_scratch","native_transformer","litert_lm","hybrid"}
    if backend not in allowed: backend="char_ngram"
    tiny_dir=Path(os.getenv("LIVING_AI_TINY_MODEL_DIR","models/tiny_transformer"))
    litert_path=Path(os.getenv("LIVING_AI_LITERTLM_MODEL_PATH","models/litert/gemma-4-E2B-it.litertlm")).expanduser()
    try:
        import torch
        torch_available=True
        torch_version=torch.__version__
    except ImportError:
        torch_available=False
        torch_version=None
    try:
        import litert_lm
        litert_available=True
    except ImportError:
        litert_available=False
    tiny=backend in {"tiny_transformer","from_scratch","native_transformer"}
    litert_model_exists=litert_path.is_file()
    if tiny:
        ready=torch_available and (tiny_dir/"config.json").is_file() and (tiny_dir/"weights.pt").is_file()
    elif backend=="litert_lm":
        ready=litert_available and litert_model_exists
    else:
        ready=True
    return {
        "backend":backend,
        "model_id":"living-ai-from-scratch" if tiny else (str(litert_path) if backend in {"litert_lm","hybrid"} else None),
        "device":os.getenv("LIVING_AI_LITERTLM_BACKEND","cpu") if backend in {"litert_lm","hybrid"} else (os.getenv("LIVING_AI_TINY_DEVICE","cpu") if tiny else "cpu"),
        "dependencies":{"torch":torch_available,"torch_version":torch_version,"litert_lm":litert_available},
        "tiny_checkpoint_exists":(tiny_dir/"weights.pt").is_file(),
        "litert_model_exists":litert_model_exists,
        "ready":ready,
        "remote_provider_enabled":os.getenv("LIVING_AI_ALLOW_REMOTE_PROVIDER","false").lower()=="true"
    }

init_db()
app=Litestar(route_handlers=[index,health,status,chat,memories,add,remove,ingest,ingest_file,ingest_url,export_corpus,train,training_datasets,upload_training_dataset,teacher_prepare,teacher_approve,stage_training_item,training_runs,proposals,propose,eval_route,promote_route,rollback_route,audit,settings,train_scratch,model_status,planner_prepare,planner_proposals,planner_submit,planner_record_evaluation,planner_learning_summary,worker_status,worker_resume,worker_pause,worker_enable,worker_disable,worker_configure,worker_tick,worker_approve_goal,worker_recommendations,evaluation_run,evaluation_runs,evaluation_gate_check,evaluation_gate_history,dataset_add_example,dataset_list_examples,dataset_review_example,dataset_export,tasks_list,tasks_submit,task_detail,task_events,tasks_run_once,task_retry,task_approve,list_projects,create_project,update_project,delete_project,list_work_items,create_work_item,update_work_item,delete_work_item,list_milestones,create_milestone,update_milestone,delete_milestone,project_activity],static_files_config=[StaticFilesConfig(path="/static",directories=[str(ROOT/"static")])],debug=False)
