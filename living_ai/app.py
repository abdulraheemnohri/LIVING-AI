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
from .neural_training import train_small_transformer
from .knowledge import parse_document, split_text, fetch_public_page
from .evolution import create_proposal,list_proposals,evaluate,promote,rollback
from .planner_api import planner_prepare,planner_proposals,planner_submit,planner_record_evaluation,planner_learning_summary
ROOT=Path(__file__).resolve().parent.parent
def auth(req):
    token=os.getenv("LIVING_AI_ADMIN_TOKEN","").strip()
    if token and req.headers.get("authorization","")!=f"Bearer {token}":raise HTTPException(status_code=401,detail="Bearer token required")
class Chat(BaseModel): message:str=Field(min_length=1,max_length=20000)
class Memory(BaseModel): content:str=Field(min_length=1,max_length=100000);source:str="manual"
class FileIngest(BaseModel): filename:str=Field(min_length=1,max_length=255);content:str=Field(min_length=1,max_length=2_500_000)
class URLIngest(BaseModel): url:str=Field(min_length=8,max_length=2048)
class Proposal(BaseModel): title:str;changes:dict
class Train(BaseModel): input_dir:str="data/corpus"
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
async def status() -> dict[str, Any]:
    with connect() as c: n=c.execute("SELECT COUNT(*) n FROM memories").fetchone()["n"];p=c.execute("SELECT COUNT(*) n FROM proposals").fetchone()["n"]
    return {"status":"running","memories":n,"proposals":p,"original_model_trained":(ROOT/"models"/"char_ngram.json").exists(),"tiny_transformer_trained":(ROOT/"models"/"tiny_transformer"/"weights.pt").exists(),"settings":get_settings(),"data_dir":str(data_dir())}
@post("/api/chat")
async def chat(data:Chat) -> dict[str, Any]:
    try:return respond(data.message)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@get("/api/memories")
async def memories(q:str="",limit:int=20) -> dict[str, Any]:return {"items":search_memories(q,limit)}
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
@get("/api/evolution/proposals")
async def proposals() -> dict[str, Any]:return {"items":list_proposals()}
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
async def audit(limit:int=50) -> dict[str, Any]:
    with connect() as c:rows=c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?",(max(1,min(limit,200)),)).fetchall()
    return {"items":[{"id":r["id"],"action":r["action"],"detail":json.loads(r["detail_json"]),"created_at":r["created_at"]} for r in rows]}
@get("/api/settings")
async def settings() -> dict[str, Any]:return {"settings":get_settings(),"auto_promote":os.getenv("LIVING_AI_AUTO_PROMOTE","false").lower()=="true"}

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
async def model_status() -> dict[str, Any]:
    backend=os.getenv("LIVING_AI_MODEL_BACKEND","char_ngram").strip().lower()
    if backend not in {"char_ngram","tiny_transformer","from_scratch","native_transformer"}: backend="char_ngram"
    tiny_dir=Path(os.getenv("LIVING_AI_TINY_MODEL_DIR","models/tiny_transformer"))
    try:
        import torch
        torch_available=True
        torch_version=torch.__version__
    except ImportError:
        torch_available=False
        torch_version=None
    tiny=backend in {"tiny_transformer","from_scratch","native_transformer"}
    ready=(torch_available and (tiny_dir/"config.json").is_file() and (tiny_dir/"weights.pt").is_file()) if tiny else True
    return {"backend":backend,"model_id":"living-ai-from-scratch" if tiny else None,
            "device":os.getenv("LIVING_AI_TINY_DEVICE","cpu") if tiny else "cpu",
            "dependencies":{"torch":torch_available,"torch_version":torch_version},
            "tiny_checkpoint_exists":(tiny_dir/"weights.pt").is_file(),"ready":ready,
            "remote_provider_enabled":os.getenv("LIVING_AI_ALLOW_REMOTE_PROVIDER","false").lower()=="true"}

init_db()
app=Litestar(route_handlers=[index,health,status,chat,memories,add,remove,ingest,ingest_file,ingest_url,export_corpus,train,proposals,propose,eval_route,promote_route,rollback_route,audit,settings,train_scratch,model_status,planner_prepare,planner_proposals,planner_submit,planner_record_evaluation,planner_learning_summary],static_files_config=[StaticFilesConfig(path="/static",directories=[str(ROOT/"static")])],debug=False)
