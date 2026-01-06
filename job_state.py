# job_state.py
from pathlib import Path
import json

STATE_DIR = Path("jobs")
STATE_DIR.mkdir(exist_ok=True)

def job_file(job_id):
    return STATE_DIR / f"{job_id}.json"

def init_job(job_id, filename):
    write_job(job_id, {
        "job_id": job_id,
        "filename": filename,
        "status": "queued",
        "progress": 0,
        "error": None
    })

def write_job(job_id, data):
    with open(job_file(job_id), "w") as f:
        json.dump(data, f)

def read_job(job_id):
    path = job_file(job_id)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)
