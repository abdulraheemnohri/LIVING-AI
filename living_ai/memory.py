from .db import connect,utcnow,audit
def add_memory(content,source="manual"):
    content=content.strip()
    if not content: raise ValueError("Memory cannot be empty")
    if len(content)>100000: raise ValueError("Memory exceeds 100,000 characters")
    with connect() as c:
        c.execute("INSERT INTO memories(content,source,created_at) VALUES(?,?,?)",(content,source[:300],utcnow()))
        row=c.execute("SELECT * FROM memories WHERE id=last_insert_rowid()").fetchone()
    audit("memory.add",{"id":row["id"],"source":source})
    return dict(row)
def search_memories(query="",limit=10):
    limit=max(1,min(int(limit),100))
    with connect() as c:
        if query.strip():
            terms=[x for x in query.lower().split() if len(x)>1][:8]
            if terms:
                where=" OR ".join("lower(content) LIKE ?" for _ in terms)
                rows=c.execute(f"SELECT * FROM memories WHERE {where} ORDER BY id DESC LIMIT ?",[*[f"%{x}%" for x in terms],limit]).fetchall()
            else: rows=c.execute("SELECT * FROM memories ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
        else: rows=c.execute("SELECT * FROM memories ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    return [dict(r) for r in rows]
def delete_memory(memory_id):
    with connect() as c: cur=c.execute("DELETE FROM memories WHERE id=?",(memory_id,))
    if cur.rowcount: audit("memory.delete",{"id":memory_id})
    return cur.rowcount>0
