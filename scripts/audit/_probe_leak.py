import json
import os
import re

from docx import Document

from scripts.audit import _common as C

C.bootstrap_db_env()
import app.models  # noqa
from sqlalchemy import create_engine, text as sql

rid = "3347590c-5b4f-4443-8a3d-a5ae455932e2"
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    kb = c.execute(sql("SELECT knowledge_bank_json FROM donor_reports WHERE id=CAST(:r AS uuid)"),
                   {"r": rid}).mappings().first()["knowledge_bank_json"]

facts = kb.get("facts") or {}
gap_answers = kb.get("gap_answers") or {}
kb_text = json.dumps(facts) + " " + json.dumps(gap_answers)


def nums(s: str) -> set[str]:
    out = set()
    for m in re.findall(r"\d[\d,]*(?:\.\d+)?", s):
        out.add(m.replace(",", ""))
    return out


kb_nums = nums(kb_text)
doc = Document(r"docs/artefacts/me_module/audits/dynamic_run/export_3347590c.docx")
text = "\n".join(p.text for p in doc.paragraphs)
doc_nums = nums(text)

unbacked = sorted([n for n in doc_nums if n not in kb_nums and len(n) >= 2],
                  key=lambda x: -len(x))
print("doc_numbers:", len(doc_nums), "kb_numbers:", len(kb_nums))
print("TRULY UNBACKED (normalized, len>=2):", len(unbacked))
for n in unbacked:
    # show surrounding context in doc
    idx = text.replace(",", "").find(n)
    ctx = ""
    if idx >= 0:
        raw = text.replace(",", "")
        ctx = raw[max(0, idx - 50):idx + len(n) + 30].replace("\n", " ")
    print(f"   {n}  ...{ctx}...")
