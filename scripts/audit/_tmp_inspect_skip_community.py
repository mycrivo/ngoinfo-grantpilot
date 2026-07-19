import json
from pathlib import Path

p = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_SKIP_46fdb1b1.json")
d = json.loads(p.read_text(encoding="utf-8"))
found = []


def walk(o, path=""):
    if isinstance(o, dict):
        lab = str(o.get("label") or o.get("section_key") or "")
        if "community" in lab.lower() or "involved people" in lab.lower():
            content = o.get("content") if isinstance(o.get("content"), dict) else {}
            found.append(
                {
                    "path": path,
                    "label": o.get("label"),
                    "status": o.get("status"),
                    "structured_bind_status": content.get("structured_bind_status"),
                    "text_snip": (content.get("text") or "")[:500],
                    "evidence_used": content.get("evidence_used"),
                    "claims": content.get("claims"),
                }
            )
        for k, v in o.items():
            walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, f"{path}[{i}]")


for key in ("draft", "draft_after_gate3", "export_preview", "draft_json"):
    if key in d:
        walk(d[key], key)

# also top-level draft-like blobs
walk(d, "root")

out = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_SKIP_COMMUNITY_INSPECT.json")
text = p.read_text(encoding="utf-8")
payload = {
    "found_count": len(found),
    "found": found[:20],
    "insufficient_data_count": text.count("insufficient_data"),
    "has_southbank": "Southbank" in text,
    "has_track3_marker": "TRACK3_P2" in text,
    "community_checks": d.get("community_checks"),
}
out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps({"found_count": len(found), "community_checks": d.get("community_checks"), "insufficient_data_count": payload["insufficient_data_count"]}, indent=2))
