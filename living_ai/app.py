import os,json,importlib.util
from pathlib import Path
from litestar import Litestar,get,post,delete,Request
from litestar.exceptions import HTTPException
from litestar.response import File
from litestar.static_files import StaticFilesConfig
from pydantic import BaseModel,Field
from .db import init_db,connect,get_settings,data_dir
from .memory import add_memory,search_memories,delete_memory
from .engine import respond
from .training import train_directory
from .neural_training import train_small_transformer
from .evolution import create_proposal,list_proposals,evaluate,promote,rollback
ROOT=Path(__file__).resolve().parent.parent
def auth(req):
    token=os.getenv("LIVING_AI_ADMIN_TOKEN","").strip()
    if token and req.headers.get("authorization","")!=f"Bearer {token}":raise HTTPException(status_code=401,detail="Bearer token required")
class Chat(BaseModel): message:str=Field(min_length=1,max_length=20000)
class Memory(BaseModel): content:str=Field(min_length=1,max_length=100000);source:str="manual"
class Proposal(BaseModel): title:str;changes:dict
class Train(BaseModel): input_dir:str="data/corpus"
class TrainScratch(BaseModel):
    input_dir:str="data/corpus"
    output_dir:str="models/tiny_transformer"
    steps:int=Field(default=500,ge=1,le=100000)
    batch_size:int=Field(default=4,ge=1,le=128)
    learning_rate:float=Field(default=0.0003,ge=0.000001,le=0.1)
    block_size:int=Field(default=64,ge=16,le=2048)
    width:int=Field(default=64,ge=32,le=1024)
    heads:int=Field(default=4,ge=1,le=16)
    layers:int=Field(default=2,ge=1,le=12)
    seed:int=42
@get("/")
async def index():return File(path=ROOT/"static"/"index.html",media_type="text/html")
@get("/api/health")
async def health():return {"ok":True,"name":"LIVING AI","version":"0.1.0"}
@get("/api/status")
async def status():
    with connect() as c: n=c.execute("SELECT COUNT(*) n FROM memories").fetchone()["n"];p=c.execute("SELECT COUNT(*) n FROM proposals").fetchone()["n"]
    return {"status":"running","memories":n,"proposals":p,"original_model_trained":(ROOT/"models"/"char_ngram.json").exists(),"tiny_transformer_trained":(ROOT/"models"/"tiny_transformer"/"weights.pt").exists(),"settings":get_settings(),"data_dir":str(data_dir())}
@post("/api/chat")
async def chat(data:Chat):
    try:return respond(data.message)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@get("/api/memories")
async def memories(q:str="",limit:int=20):return {"items":search_memories(q,limit)}
@post("/api/memories")
async def add(data:Memory,request:Request):
    auth(request)
    try:return add_memory(data.content,data.source)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@delete("/api/memories/{memory_id:int}")
async def remove(memory_id:int,request:Request):
    auth(request)
    if not delete_memory(memory_id):raise HTTPException(status_code=404,detail="Memory not found")
    return {"deleted":True,"id":memory_id}
@post("/api/knowledge/ingest")
async def ingest(data:Memory,request:Request):
    auth(request);return {"ingested":True,"memory":add_memory(data.content,data.source)}
@post("/api/training/train")
async def train(data:Train,request:Request):
    auth(request)
    try:return train_directory(data.input_dir)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@get("/api/evolution/proposals")
async def proposals():return {"items":list_proposals()}
@post("/api/evolution/proposals")
async def propose(data:Proposal,request:Request):
    auth(request)
    try:return create_proposal(data.title,data.changes)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@post("/api/evolution/proposals/{proposal_id:int}/evaluate")
async def eval_route(proposal_id:int,request:Request):
    auth(request)
    try:return evaluate(proposal_id)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@post("/api/evolution/proposals/{proposal_id:int}/promote")
async def promote_route(proposal_id:int,request:Request):
    auth(request)
    try:return promote(proposal_id)
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@post("/api/evolution/rollback")
async def rollback_route(request:Request):
    auth(request)
    try:return rollback()
    except ValueError as e:raise HTTPException(status_code=400,detail=str(e))
@get("/api/audit")
async def audit(limit:int=50):
    with connect() as c:rows=c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?",(max(1,min(limit,200)),)).fetchall()
    return {"items":[{"id":r["id"],"action":r["action"],"detail":json.loads(r["detail_json"]),"created_at":r["created_at"]} for r in rows]}
@get("/api/settings")
async def settings():return {"settings":get_settings(),"auto_promote":os.getenv("LIVING_AI_AUTO_PROMOTE","false").lower()=="true"}

@post("/api/training/train-from-scratch")
async def train_scratch(data:TrainScratch,request:Request):
    auth(request)
    if data.width % data.heads: raise HTTPException(status_code=400,detail="width must be divisible by heads")
    try:
        return train_small_transformer(input_dir=data.input_dir,output_dir=data.output_dir,steps=data.steps,batch_size=data.batch_size,learning_rate=data.learning_rate,seed=data.seed,config_overrides={"block_size":data.block_size,"d_model":data.width,"n_heads":data.heads,"n_layers":data.layers})
    except (ValueError,RuntimeError) as e: raise HTTPException(status_code=400,detail=str(e))

@get("/api/model/status")
async def model_status():
    backend=os.getenv("LIVING_AI_MODEL_BACKEND","char_ngram").strip().lower()
    model_id=os.getenv("LIVING_AI_HF_MODEL_ID","HuggingFaceTB/SmolLM3-3B-Base").strip()
    try:
        deps={"torch":importlib.util.find_spec("torch") is not None,
              "transformers":importlib.util.find_spec("transformers") is not None}
    except (ImportError, ValueError):
        deps={"torch":False,"transformers":False}
    return {
        "backend":backend,
        "model_id":model_id if backend in {"transformers","smollm3","huggingface"} else None,
        "device":os.getenv("LIVING_AI_HF_DEVICE","cpu"),
        "dtype":os.getenv("LIVING_AI_HF_DTYPE","auto"),
        "local_only":os.getenv("LIVING_AI_HF_LOCAL_ONLY","false").lower()=="true",
        "dependencies":deps,
        "ready":all(deps.values()) if backend in {"transformers","smollm3","huggingface"} else True,
        "remote_provider_enabled":os.getenv("LIVING_AI_ALLOW_REMOTE_PROVIDER","false").lower()=="true",
    }
init_db()
app=Litestar(route_handlers=[index,health,status,chat,memories,add,remove,ingest,train,proposals,propose,eval_route,promote_route,rollback_route,audit,settings,train_scratch,model_status],static_files_config=[StaticFilesConfig(path="/static",directories=[str(ROOT/"static")])],debug=False)
