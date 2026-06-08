"""R8 worker-death demonstration (side-effect-free).

Reproduces the in-flight-job-on-dead-worker coverage gap using the reaper's
own decision function on constructed jobs. Does NOT scale the shared Railway
worker (would disrupt concurrent audit jobs); the mechanism is identical:
- claim_next_job only claims QUEUED -> a stuck RUNNING job never auto-resumes
- reaper runs only inside a live worker; mark_job_failed is terminal (no requeue)
- no lease/heartbeat/updated_at on report_jobs
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

import app.models  # noqa
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.worker.orphan_reaper import (
    compute_stale_threshold_seconds,
    should_reap_job,
)

now = datetime.now(timezone.utc)


def job(stage, started_delta_s, status=ReportJobStatus.RUNNING.value, stages=None):
    j = ReportJob()
    j.id = uuid.uuid4()
    j.donor_report_id = uuid.uuid4()
    j.stage = stage
    j.status = status
    j.finished_at = None
    j.started_at = now - timedelta(seconds=started_delta_s)
    j.agent_trace_json = {"stages": stages or {}}
    return j


cases = []

# (1) Worker died mid-extract 3h ago, no stage completed -> should be reaped.
j1 = job(ReportJobStage.EXTRACT.value, 3 * 3600)
cases.append(("dead_worker_extract_3h", j1, 3, 8))

# (2) Healthy in-progress extract started 60s ago -> must NOT be reaped.
j2 = job(ReportJobStage.EXTRACT.value, 60)
cases.append(("healthy_extract_60s", j2, 3, 8))

# (3) Stuck running synthesise 3h, no completed stages -> reaped.
j3 = job(ReportJobStage.SYNTHESISE.value, 3 * 3600)
cases.append(("dead_worker_synth_3h", j3, 3, 8))

out = []
for name, j, docs, secs in cases:
    thr = compute_stale_threshold_seconds(j, doc_count=docs, section_count=secs)
    silence = (now - j.started_at).total_seconds()
    reap = should_reap_job(j, now=now, doc_count=docs, section_count=secs)
    row = {"case": name, "stage": j.stage, "silence_s": round(silence),
           "threshold_s": round(thr), "should_reap": reap}
    out.append(row)
    print(json.dumps(row))

print("\nclaim_next_job filters status==QUEUED only -> a RUNNING job is never re-claimed (no auto-resume).")
print("mark_job_failed is terminal; reaper has NO re-queue path -> in-flight run is lost on worker death.")
print("report_jobs has no lease/heartbeat/updated_at column.")
print("3600s wall-clock backstop is a ThreadPoolExecutor timeout that dies with the worker process.")
