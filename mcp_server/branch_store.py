"""Branch store for ToT option trees. The only thing the agent may write, and it is a separate SQLite file.
Rows are never deleted: pruning sets status='pruned' so the whole tree can be shown in the report."""
from __future__ import annotations
import sqlite3, json, pathlib

def _err(code, msg): return {"error": {"code": code, "message": msg}}

class BranchStore:
    def __init__(self, path=":memory:"):
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS branches(
            id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, claim_id TEXT, parent_id INTEGER, depth INTEGER,
            text TEXT, scores TEXT, total REAL, status TEXT)""")
    def add(self, run_id, claim_id, parent_id, text, scores=None, total=0.0, status="open"):
        if not isinstance(text, str) or not text.strip(): return _err("empty_text", "option text is empty")
        if not run_id or not claim_id: return _err("bad_ids", "run_id and claim_id are required")
        scores = scores or {}
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 for v in list(scores.values()) + [total]):
            return _err("bad_score", "scores and total must be numbers between 0 and 1")
        depth = 0
        if parent_id is not None:
            row = self.db.execute("SELECT depth FROM branches WHERE id=? AND run_id=? AND claim_id=?", (parent_id, run_id, claim_id)).fetchone()
            if not row: return _err("unknown_parent", f"parent {parent_id} not found for this run and claim")
            depth = row[0] + 1
        cur = self.db.execute("INSERT INTO branches(run_id,claim_id,parent_id,depth,text,scores,total,status) VALUES(?,?,?,?,?,?,?,?)",
                              (run_id, claim_id, parent_id, depth, text, json.dumps(scores), float(total), status))
        self.db.commit()
        return {"id": cur.lastrowid, "depth": depth}
    def get(self, run_id, claim_id):
        rows = self.db.execute("SELECT id,parent_id,depth,text,scores,total,status FROM branches WHERE run_id=? AND claim_id=? ORDER BY depth,id",
                               (run_id, claim_id)).fetchall()
        return {"branches": [dict(id=r[0], parent_id=r[1], depth=r[2], text=r[3], scores=json.loads(r[4]), total=r[5], status=r[6]) for r in rows]}
    def set_status(self, branch_id, status):
        cur = self.db.execute("UPDATE branches SET status=? WHERE id=?", (status, branch_id)); self.db.commit()
        return {"ok": True} if cur.rowcount else _err("unknown_branch", f"branch {branch_id} not found")
    def prune(self, branch_id): return self.set_status(branch_id, "pruned")
