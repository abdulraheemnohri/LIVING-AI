import json,random
from collections import defaultdict,Counter
from pathlib import Path
class CharNGramModel:
    def __init__(self,order=4): self.order=max(1,min(int(order),8)); self.transitions=defaultdict(Counter); self.trained_chars=0
    def train_text(self,text):
        text=text.strip()
        if not text:return
        padded=" "*self.order+text
        for i in range(self.order,len(padded)): self.transitions[padded[i-self.order:i]][padded[i]]+=1
        self.trained_chars+=len(text)
    def generate(self,prompt="",max_chars=240,temperature=.7):
        if not self.transitions:return "Local model is not trained yet. Add text files and run the training pipeline."
        context=(" "*self.order+prompt)[-self.order:]; out=[]
        for _ in range(max(1,min(int(max_chars),12000))):
            counts=self.transitions.get(context)
            if not counts: context=" "*self.order; counts=self.transitions.get(context)
            if not counts: break
            chars,weights=zip(*counts.items())
            nxt=chars[max(range(len(weights)),key=lambda i:weights[i])] if temperature<.12 else random.choices(chars,weights=[max(.0001,w**(1/max(.05,min(temperature,2)))) for w in weights])[0]
            out.append(nxt); context=(context+nxt)[-self.order:]
        return (prompt+"".join(out)).strip()
    def save(self,path):
        p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({"format":1,"order":self.order,"trained_chars":self.trained_chars,"transitions":{k:dict(v) for k,v in self.transitions.items()}},ensure_ascii=False),encoding="utf-8")
    @classmethod
    def load(cls,path):
        d=json.loads(Path(path).read_text(encoding="utf-8"))
        if d.get("format")!=1: raise ValueError("Unsupported model format")
        m=cls(d["order"]);m.trained_chars=d.get("trained_chars",0);m.transitions=defaultdict(Counter,{k:Counter(v) for k,v in d["transitions"].items()});return m
