import json,os,time
from pathlib import Path
from .db import connect,utcnow,get_settings,set_settings,audit,data_dir
ALLOWED={"temperature":lambda v:isinstance(v,(int,float)) and 0<=v<=1,"max_reply_chars":lambda v:isinstance(v,int) and 128<=v<=12000,"retrieval_limit":lambda v:isinstance(v,int) and 1<=v<=10}
def validate(changes):
    if not changes or set(changes)-set(ALLOWED): raise ValueError("Only temperature, max_reply_chars, and retrieval_limit are allowed")
    for k,v in changes.items():
        if not ALLOWED[k](v): raise ValueError(f"Invalid value for {k}")
def create_proposal(title,changes):
    validate(changes);now=utcnow()
    with connect() as c:
        cur=c.execute("INSERT INTO proposals(title,changes_json,status,created_at,updated_at) VALUES(?,?,?,?,?)",(title[:200],json.dumps(changes),"proposed",now,now))
        row=c.execute("SELECT * FROM proposals WHERE id=?",(cur.lastrowid,)).fetchone()
    audit("evolution.propose",{"id":row["id"],"changes":changes});return row_dict(row)
def row_dict(r): return {"id":r["id"],"title":r["title"],"changes":json.loads(r["changes_json"]),"status":r["status"],"evaluation":json.loads(r["evaluation_json"]) if r["evaluation_json"] else None,"created_at":r["created_at"],"updated_at":r["updated_at"]}
def get_proposal(pid):
    with connect() as c:r=c.execute("SELECT * FROM proposals WHERE id=?",(pid,)).fetchone()
    if not r:raise ValueError("Proposal not found")
    return r
def list_proposals():
    with connect() as c:rows=c.execute("SELECT * FROM proposals ORDER BY id DESC LIMIT 100").fetchall()
    return [row_dict(r) for r in rows]
def evaluate(pid):
    r=get_proposal(pid);changes=json.loads(r["changes_json"]);validate(changes)
    ev={"passed":True,"checks":["allowlist","value_ranges","reversible_settings_only"],"baseline":get_settings(),"candidate":{**get_settings(),**changes}}
    with connect() as c:c.execute("UPDATE proposals SET status='evaluated',evaluation_json=?,updated_at=? WHERE id=?",(json.dumps(ev),utcnow(),pid))
    audit("evolution.evaluate",{"id":pid,"passed":True})
    if os.getenv("LIVING_AI_AUTO_PROMOTE","false").lower()=="true":return promote(pid)
    return row_dict(get_proposal(pid))
def promote(pid):
    r=get_proposal(pid)
    if r["status"]!="evaluated":raise ValueError("Evaluate proposal before promotion")
    changes=json.loads(r["changes_json"]);validate(changes)
    d=data_dir()/"backups";d.mkdir(parents=True,exist_ok=True);snap=d/f"settings-{pid}-{int(time.time())}.json"
    snap.write_text(json.dumps({"settings":get_settings(),"proposal_id":pid},indent=2),encoding="utf-8")
    set_settings(changes)
    with connect() as c:c.execute("UPDATE proposals SET status='promoted',updated_at=? WHERE id=?",(utcnow(),pid))
    audit("evolution.promote",{"id":pid,"snapshot":str(snap)})
    return {"proposal":row_dict(get_proposal(pid)),"snapshot":str(snap)}
def rollback():
    paths=sorted((data_dir()/"backups").glob("settings-*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
    if not paths:raise ValueError("No settings snapshot")
    d=json.loads(paths[0].read_text(encoding="utf-8"));set_settings(d["settings"]);audit("evolution.rollback",{"snapshot":str(paths[0])})
    return {"rolled_back":True,"settings":get_settings()}
