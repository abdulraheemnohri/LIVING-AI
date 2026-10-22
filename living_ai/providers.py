import json,os,urllib.request,urllib.error
def remote_chat(message):
    if os.getenv("LIVING_AI_ALLOW_REMOTE_PROVIDER","false").lower()!="true":return None
    base=os.getenv("LIVING_AI_PROVIDER_URL","").strip().rstrip("/")
    model=os.getenv("LIVING_AI_PROVIDER_MODEL","").strip()
    key=os.getenv("LIVING_AI_PROVIDER_API_KEY","").strip()
    if not base or not model:return None
    body=json.dumps({"model":model,"messages":[{"role":"user","content":message}],"temperature":0.7}).encode()
    headers={"Content-Type":"application/json"}
    if key:headers["Authorization"]="Bearer "+key
    req=urllib.request.Request(base+"/chat/completions",data=body,headers=headers,method="POST")
    try:
        with urllib.request.urlopen(req,timeout=45) as r:d=json.loads(r.read().decode())
        return d["choices"][0]["message"]["content"]
    except (urllib.error.URLError,TimeoutError,KeyError,ValueError,IndexError):
        return None
