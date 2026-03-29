import time
import random

# ---------- global state ----------

state = None  # will be initialized by init_env()


def init_env(init_workers=2, dt=0.1):
    """
    Initialize the simulation environment and global state. 
    Will do adjustments later as needed.
    """
    global state
    state = {
        "time": 0.0,
        "dt": dt,
        "queue": [],
        "workers": [None] * init_workers,
        "wait_threshold": 1.0,
        "util_high": 0.8,
        "util_low": 0.4,
        "cooldown": 5.0,
        "max_workers": init_workers + 3,
        "min_workers": 1,
        "alpha": 0.2,
        "policy": "FIFO", # Default as "FIFO", can be changed to "SPT"
        "last_action_time": -1e9,
        "lambda_hat": 0.0,
        "last_arrivals": 0,
        "next_job_id": 0,
        "finished_jobs": [],
        "violation_count": 0,
        "actions_log": [],
    }


# ---------- job arrival (called by Django view) ----------

def sample_service_time():
    if random.random() < 0.8:
        return random.uniform(0.1, 0.8)
    else:
        return random.uniform(2.0, 5.0)


def enqueue_job(service_time=None):
    """Called by /enqueue HTTP endpoint."""
    global state
    if service_time is None:
        service_time = sample_service_time()

    job_id = state["next_job_id"]
    state["next_job_id"] += 1

    job = {
        "id": job_id,
        "arrival_time": time.time(),         # real clock
        "service_time": service_time,
        "remaining_time": service_time,
        "start_service_time": None,
        "finish_time": None,
    }
    state["queue"].append(job)
    state["last_arrivals"] += 1
    return job_id
