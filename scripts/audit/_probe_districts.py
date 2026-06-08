import json
import os

from scripts.audit import _common as C

C.bootstrap_db_env()
import app.models  # noqa
from sqlalchemy import create_engine, text as sql

e = create_engine(os.environ["DATABASE_URL"])
rid = "3347590c-5b4f-4443-8a3d-a5ae455932e2"
with e.connect() as c:
    kb = c.execute(sql("SELECT knowledge_bank_json FROM donor_reports WHERE id=CAST(:r AS uuid)"),
                   {"r": rid}).mappings().first()["knowledge_bank_json"]
    docs = c.execute(sql("SELECT original_filename, extracted_json FROM uploaded_documents WHERE donor_report_id=CAST(:r AS uuid)"),
                     {"r": rid}).mappings().all()

kbs = json.dumps(kb)
for term in ["Machinga", "Mangochi", "Lilongwe", "Malawi"]:
    print(f"KB contains {term!r}:", term in kbs)
    for d in docs:
        ej = json.dumps(d["extracted_json"] or {})
        print(f"   extracted[{d['original_filename'][:34]}] {term!r}:", term in ej)
