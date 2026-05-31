from app.reports.worker.orm_bootstrap import ensure_orm_models_registered

ensure_orm_models_registered()

from app.reports.worker.job_runner import run_forever

if __name__ == "__main__":
    run_forever()
