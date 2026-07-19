import json
from pathlib import Path

p = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_ANSWERED_b007f125.json")
text = p.read_text(encoding="utf-8")
d = json.loads(text)
markers = [
    "TRACK3_P2_ANSWERED_COMMUNITY_PARTICIPATION",
    "TRACK3_P2_ANSWERED_PARTNER_COLLAB",
    "gap:community_involvement:indicator:community_participation_examples",
    "gap:community_involvement:indicator:partner_or_local_collaboration_examples",
    "Southbank Community Trust",
    "Residents co-designed three evening workshops",
]
hits = {m: text.count(m) for m in markers}
print(json.dumps({"hits": hits, "community_checks": d.get("community_checks"), "cost": d.get("cost"), "duration_seconds": d.get("duration_seconds"), "verdict": d.get("verdict")}, indent=2))
