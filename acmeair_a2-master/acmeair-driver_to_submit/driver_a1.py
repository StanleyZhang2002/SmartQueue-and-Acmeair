import sys
import csv
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
import argparse

from sdcclient import IbmAuthHelper, SdMonitorClient

GUID = '6638a8a0-2a5c-446b-8f6f-3a98be082e64'
APIKEY = 'VVzDMyBYPx2Lu5pEgdShygtKl59VS57A8A0X-MPJir7q'
URL = 'https://ca-tor.monitoring.cloud.ibm.com'
GROUPNAME = 'acmeair-group9' 

start = -600     # last 10 minutes
end = 0
sampling = 60   # 1 minute
filtered_group = f'kubernetes.namespace.name="{GROUPNAME}"'

value_metrics = [
    # System
    {"id": "cpu.quota.used.percent",    "aggregations": {"time": "timeAvg", "group": "avg"}},
    {"id": "memory.limit.used.percent", "aggregations": {"time": "timeAvg", "group": "avg"}},

    # JVM
    {"id": "jvm.heap.used",             "aggregations": {"time": "timeAvg", "group": "avg"}},
    {"id": "jvm.thread.count",          "aggregations": {"time": "timeAvg", "group": "avg"}},
    {"id": "jvm.gc.global.time",        "aggregations": {"time": "sum", "group": "avg"}},
    {"id": "jvm.gc.global.count",       "aggregations": {"time": "sum", "group": "avg"}},

    # Application
    {"id": "net.http.request.time",     "aggregations": {"time": "max",     "group": "avg"}},
    {"id": "net.request.count.in",      "aggregations": {"time": "sum", "group": "avg"}},

    # Reliability
    {"id": "kubernetes.pod.restart.count", "aggregations": {"time": "sum", "group": "avg"}},
]

# Names for the metrics above, used as a meaningful column header in CSV
value_names = [
    "cpu_pct",
    "mem_pct",
    "jvm_heap_used",
    "jvm_threads",
    "gc_time_sum",
    "gc_count_sum",
    "http_time_max",
    "req_in_sum",
    "pod_restarts",
]

def get_data_from_database():
    ibm_headers = IbmAuthHelper.get_headers(URL, APIKEY, GUID)
    sdclient = SdMonitorClient(sdc_url=URL, custom_headers=ibm_headers)

    metrics = [{"id": "kubernetes.deployment.name"}] + value_metrics
    ok, res = sdclient.get_data(metrics, start, end, sampling, filter=filtered_group)
    if not ok:
        print("Error: cannot get data from the database")
        sys.exit(1)
    
    return res

def process_data(res):
    """
    Process the raw data from the database into a more friendly format.
    Return a list of entries like:
    [{"t": timestamp, "service": service_name, "vals": {metric_name: value, ...}}, ...]
    """
    processed_data = []
    for entry in res.get("data", []):
        timestamp = entry["t"]
        data  = entry["d"]
        service_name = data[0] or "UNKNOWN"
        vals = {}
        for i, name in enumerate(value_names, start=1):
            vals[name] = data[i]
        processed_data.append({"t": timestamp, "service": service_name, "vals": vals})
    return processed_data


def add_processed_TPS_and_GC(rows):
    """
    Calculate the TPS per seconds rate and GC average pause turns the 
    per-minute total GC time into a per-event average to show how disruptive each GC is.
    We use formula as follows:
    TPS = req_in_sum / sampling
    gc_pause_avg = gc_time_sum / gc_count_sum
    """
    for row in rows:
        vals = row["vals"]
        if vals["req_in_sum"] is not None:
            vals["tps"] = float(vals["req_in_sum"]) / float(sampling)
        else:
            vals["tps"] = None

        if vals["gc_time_sum"] is not None and vals["gc_count_sum"]:
            vals["gc_pause_avg"] = float(vals["gc_time_sum"]) / max(1.0,float(vals["gc_count_sum"]))
        else:
            vals["gc_pause_avg"] = None
    return rows


def per_service_summary(rows):
    """
    Summarize the data per service, calculating averages or max or sum for each metric.
    (Calculate the data for per service for the whole time window, not per sampling interval.)
    Return a dictionary of dictionaries like:
    {service_name: {metric_name: aggregated_value, ...}, ...}
    """
    summary = {}
    for row in rows:
        service = row["service"]
        if service not in summary:
            summary[service] = {
                "cpu_sum": 0.0, "cpu_cnt": 0,
                "mem_sum": 0.0, "mem_cnt": 0,
                "lat_max": None,
                "tps_sum": 0.0, "tps_cnt": 0,
                "gc_events": 0.0,
                "restarts": 0.0,
            }
        
        service_in_summary = summary[service]

        x = row["vals"].get("cpu_pct")
        if x is not None:
            service_in_summary["cpu_sum"] += float(x)
            service_in_summary["cpu_cnt"] += 1

        x = row["vals"].get("mem_pct")
        if x is not None:
            service_in_summary["mem_sum"] += float(x)
            service_in_summary["mem_cnt"] += 1

        x = row["vals"].get("http_time_max")
        if x is not None:
            x = float(x)
            if service_in_summary["lat_max"] is None or x > service_in_summary["lat_max"]:
                service_in_summary["lat_max"] = x

        x = row["vals"].get("tps")
        if x is not None:
            service_in_summary["tps_sum"] += float(x)
            service_in_summary["tps_cnt"] += 1

        x = row["vals"].get("gc_count_sum")
        if x is not None:
            service_in_summary["gc_events"] += float(x)

        x = row["vals"].get("pod_restarts")
        if x is not None:
            service_in_summary["restarts"] += float(x)
    
    result_map = {}
    for service, vals in summary.items():
        result_map[service] = {
            "cpu_avg": (vals["cpu_sum"] / vals["cpu_cnt"]) if vals["cpu_cnt"] > 0 else None,
            "mem_avg": (vals["mem_sum"] / vals["mem_cnt"]) if vals["mem_cnt"] > 0 else None,
            "lat_max": vals["lat_max"],
            "tps_avg": (vals["tps_sum"] / vals["tps_cnt"]) if vals["tps_cnt"] > 0 else None,
            "gc_events": vals["gc_events"],
            "restarts": vals["restarts"],
        }

    return result_map


def take_avg(values):
    clear_list = [float(val) for val in values if val is not None]
    return sum(clear_list) / len(clear_list) if clear_list else None


def take_max(values):
    clear_list = [float(val) for val in values if val is not None]
    return max(clear_list) if clear_list else None


def higher_worse(value, low, high):
    """
    Normalize a value in range [0,1] and higher is worse.
    when value <= low, return 0.0 best
    when value >= high, return 1.0 worst
    Otherwise, return a linear interpolation to judge good or not.
    """
    if value is None or low is None or high is None or low >= high:
        return None
    value = float(value)
    if value <= low:
        return 0.0
    elif value >= high:
        return 1.0
    
    return (value - low) / float(high - low)


def higher_better(value, low, high):
    """
    Normalize a value in range [0,1] and higher is better.
    when value <= low, return 0.0 worst
    when value >= high, return 1.0 best
    Otherwise, return a linear interpolation to judge good or not.
    """
    if value is None or low is None or high is None or low >= high:
        return None
    value = float(value)
    if value <= low:
        return 0.0
    elif value >= high:
        return 1.0
    
    return (value - low) / float(high - low)
    

def different_scales(summary):
    """
    Given a summary dictionary as returned by per_service_summary(),
    return a new dictionary with the same keys and values are normalized.
    Return a dictionary of thresholds.
    """
    # all_latency_vals = [service["lat_max"]  for service in summary.values() if service["lat_max"]  is not None]
    # all_tps_vals = [service["tps_avg"]  for service in summary.values() if service["tps_avg"]  is not None]
    # all_gc_vals = [service["gc_events"]  for service in summary.values() if service["gc_events"]  is not None]

    # # Latency thresholds
    # if take_avg(all_latency_vals) is not None:
    #     latency_avg = take_avg(all_latency_vals)
    # else:
    #     latency_avg = 1.0
    
    # if take_max(all_latency_vals) is not None:
    #     latency_max = take_max(all_latency_vals)
    # else:
    #     latency_max = 2.0 * latency_avg
    
    # latency_normal = latency_avg * 1.2
    # latency_bad = max(latency_max, latency_avg * 2.0)

    # # TPS thresholds
    # if take_avg(all_tps_vals) is not None:
    #     tps_avg = take_avg(all_tps_vals)
    # else:
    #     tps_avg = 0.0
    
    # if take_max(all_tps_vals) is not None:
    #     tps_max = take_max(all_tps_vals)
    # else:
    #     tps_max = tps_avg * 1.2
    
    # tps_low = tps_avg * 0.8

    # tps_high = max(tps_max, tps_avg * 1.2)

    # # GC events thresholds
    # gc_bad_events = take_max(all_gc_vals) if take_max(all_gc_vals) is not None else 8.0

    # CPU thresholds
    CPU_GOOD = 35.0
    CPU_BAD  = 85.0

    # Memory thresholds
    MEMORY_GOOD = 50.0
    MEMORY_BAD  = 90.0

    return { "latency_low": 0, "latency_bad": 2.0e9,
             "tps_low": 5.0, "tps_high": 15.0,
             "gc_bad_events": max(8.0, 1.0),
             "gc_good_events": 0.0,
             "cpu_good": CPU_GOOD, "cpu_bad": CPU_BAD,
             "mem_good": MEMORY_GOOD, "mem_bad": MEMORY_BAD,
            }


def compute_harmfulness(summary, scales):
    """
    Given a summary dictionary as returned by per_service_summary(),
    and a scales dictionary as returned by different_scales(),
    return a new dictionary. The higher the value, the more harmful the service is.
    """

    harmfulness = {}
    for service, vals in summary.items():
        cpu = vals["cpu_avg"]
        mem = vals["mem_avg"]
        latency = vals["lat_max"]
        tps = vals["tps_avg"]
        gc_events = vals["gc_events"]

        if higher_worse(cpu, scales["cpu_good"], scales["cpu_bad"]) is not None:
            #print(f"Service:{service} CPU bad: {scales['cpu_bad']}, good: {scales['cpu_good']}, cpu: {cpu}")
            cpu_harmfulness = higher_worse(cpu, scales["cpu_good"], scales["cpu_bad"])
            #print(f"Service:{service} CPU harmfulness not None: {cpu_harmfulness}")
        else:
            cpu_harmfulness = 0.0
            #print(f"Service:{service} CPU harmfulness: {cpu_harmfulness}")
        
        if higher_worse(mem, scales["mem_good"], scales["mem_bad"]) is not None:
            mem_harmfulness = higher_worse(mem, scales["mem_good"], scales["mem_bad"])
        else:
            mem_harmfulness = 0.0

        if higher_worse(latency, scales["latency_low"], scales["latency_bad"]) is not None:
            latency_harmfulness = higher_worse(latency, scales["latency_low"], scales["latency_bad"])
        else:
            latency_harmfulness = 0.0
        
        # # Higher TPS is better, which means lower harmfulness.
        # if higher_better(tps, scales["tps_low"], scales["tps_high"]) is not None:
        #     tps_harmfulness = 1.0 - higher_better(tps, scales["tps_low"], scales["tps_high"])
        # else:
        #     tps_harmfulness = 1.0
        
        # if higher_worse(gc_events, scales["gc_good_events"], scales["gc_bad_events"]) is not None:
        #     gc_harmfulness = higher_worse(gc_events, scales["gc_good_events"], scales["gc_bad_events"])
        # else:
        #     gc_harmfulness = 0.0

        #f"Service:{service} :{latency_harmfulness}, {cpu_harmfulness}, {mem_harmfulness}")
        gc_harmfulness  = 1.0 if (gc_events is not None and gc_events >= scales["gc_bad_events"]) else 0.0

        # TPS harmfulness = 1.0 if below low; 0.0 if above/equal high; mid-range optional 0.5
        if tps is None:
            tps_harmfulness = 1.0  # missing TPS -> treat as harmful (or choose 0.0 if you prefer)
        elif tps <= scales["tps_low"]:
            tps_harmfulness = 1.0
        elif tps >= scales["tps_high"]:
            tps_harmfulness = 0.0
        else:
            tps_harmfulness = 0.5  # mid band (optional; set 0.0 or 1.0 if you want strictly binary)

        
        # This used for determine the scale down only when a service is low CPU usage and latency is good.
        if cpu is not None:
            idle_harmfulness = higher_better(scales["cpu_good"] - cpu, 0.0, scales["cpu_good"])
        else:
            idle_harmfulness = 0.0

        if latency_harmfulness >= 0.5:
            idle_harmfulness *= 0.3
        
        harmfulness[service] = {
            "cpu_harmfulness": cpu_harmfulness,
            "mem_harmfulness": mem_harmfulness,
            "latency_harmfulness": latency_harmfulness,
            "latency_ok": 1.0 - latency_harmfulness,
            "tps_ok": 1.0 - tps_harmfulness,
            "tps_harmfulness": tps_harmfulness,
            "gc_harmfulness": gc_harmfulness,
            "idle_harmfulness": idle_harmfulness,
            "restarts": vals["restarts"],
            "cpu": cpu,
            "mem": mem,
            "latency": latency,
            "tps": tps,
            "gc_events": gc_events,
        }
    return harmfulness


STRATEGY_WEIGHTS = {
    # Vertical CPU scaling deals with CPU pressure and latency
    "add_cpu": {"cpu_harmfulness": 0.55, "latency_harmfulness": 0.45},

    # Adding more memory helps with memory pressure and GC
    "add_mem": {"mem_harmfulness": 0.50, "gc_harmfulness": 0.30, "latency_harmfulness": 0.20},

    # Horizontal scaling helps with latency and TPS, minor effect on CPU
    "add_pods": {"latency_harmfulness": 0.50, "tps_harmfulness": 0.30, "cpu_harmfulness": 0.20},

    # Thread tuning helps with latency and tps. 
    "tune_threads": {"latency_harmfulness": 0.70, "tps_harmfulness": 0.30},

    # Scale down a service that is idle and not doing much. Lower CPU usage and good latency.
    "scale_down": {"idle_harmfulness": 0.50, "latency_ok": 0.50},

    # Do nothing strategy, used when a service is not harmful.
    "do_nothing":   {},
}


def weighted_sum(harmfulness, weights):
    total_weight = 0.0
    total_value = 0.0
    for key, weight in weights.items():
        total_value += harmfulness.get(key, 0.0) * weight
        total_weight += weight
    return total_value / total_weight if total_weight > 0.0 else 0.0


def analyze_strategies(harmfulness):
    """
    Given a harmfulness dictionary as returned by compute_harmfulness(),
    return a new dictionary. The higher the value, the more recommended the strategy is.
    But when tune the threads, we need to check when CPU has enough room otherwise tune the threads may make things worse.
    """
    strategy_scores = {}
    for service, harms in harmfulness.items():
        cpu_harmfulness = harms.get("cpu_harmfulness", 0.0)
        
        piority = []
        for strategy, weights in STRATEGY_WEIGHTS.items():
            score = weighted_sum(harms, weights)
            # When CPU is already high, we should not tune the threads which may make things worse.
            if strategy == "tune_threads":
                score *= (1.0 - min(cpu_harmfulness, 1.0))
                
            piority.append((strategy, score))
        piority.sort(key=lambda x: x[1], reverse=True)
        strategy_scores[service] = piority
    return strategy_scores


def print_scales(scales):
    print(" Different scales determined from the data under this 10 mins window:")
    print(f"CPU (%): good <= {scales['cpu_good']}, bad >= {scales['cpu_bad']}")
    print(f"Memory (%): good <= {scales['mem_good']}, bad >= {scales['mem_bad']}")
    print(f"Latency (ms): normal <= {scales['latency_low']}, bad >= {scales['latency_bad']}")
    print(f"TPS: low <= {scales['tps_low']}, high >= {scales['tps_high']}")
    print(f"GC events: good <= {scales['gc_good_events']}, bad >= {scales['gc_bad_events']}")


def print_the_best_strategy(summary, strategies):
    print("================= Recommended Strategies ================")
    for service in sorted(summary.keys()):
        print(f"Service: {service}")
        strategies_for_service = strategies.get(service, [])
        service_summary = summary.get(service, {})

        if service_summary["restarts"] and service_summary["restarts"] > 0:
            print(f"  Pod restarts observed: {service_summary['restarts']:.1f} times in last 10 mins, check the pod logs for possible crashes.")

        if not strategies_for_service:
            print(" DO NOTHING: no harmfulness data available.")
            continue

        best_strategy = strategies_for_service[0]
        print(f"  Best strategy to take for this service: {best_strategy[0]} (score: {best_strategy[1]:.3f})")
        print("  Other strategies in priority order:")
        for strategy, score in strategies_for_service[1:]:
            print(f"    {strategy:12s}: {score:.3f}")   


def write_csv_rows(rows, out_path, label):
    """
    Write raw data + derived TPS/GC to a CSV for plotting and report figures.

    Columns:
      timestamp, iso_time, service, label,
      cpu_pct, mem_pct, jvm_heap_used, jvm_threads,
      gc_time_sum, gc_count_sum, http_time_max, req_in_sum, pod_restarts,
      tps, gc_pause_avg
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    cols = [
        "timestamp","iso_time","service","label",
        "cpu_pct","mem_pct","jvm_heap_used","jvm_threads",
        "gc_time_sum","gc_count_sum","http_time_max","req_in_sum","pod_restarts",
        "tps","gc_pause_avg"
    ]
    with open(out_path, "w", newline="") as f:
        write_file = csv.writer(f)
        write_file.writerow(cols)
        for r in rows:
            timestamp  = r["t"]
            iso = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            vals   = r["vals"]
            write_file.writerow([
                timestamp, iso, r["service"], label,
                vals.get("cpu_pct"), vals.get("mem_pct"), vals.get("jvm_heap_used"), vals.get("jvm_threads"),
                vals.get("gc_time_sum"), vals.get("gc_count_sum"), vals.get("http_time_max"), vals.get("req_in_sum"), vals.get("pod_restarts"),
                vals.get("tps"), vals.get("gc_pause_avg")
            ])



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="unspecified", help="a tag for this window, e.g., low|medium|high")
    parser.add_argument("--out",   default="datasets/dataset.csv", help="CSV path for raw+derived samples")
    args = parser.parse_args()
    data = process_data(get_data_from_database())
    data = add_processed_TPS_and_GC(data)
    write_csv_rows(data, args.out, args.label)
    #print(f"[OK] wrote samples → {args.out}")
    summary = per_service_summary(data)
    scales = different_scales(summary)
    #print("Scales:", scales)
    harmfulness = compute_harmfulness(summary, scales)
    strategies = analyze_strategies(harmfulness)
    print_scales(scales)
    print_the_best_strategy(summary, strategies)
    #print(strategies)
    #print(summary)
    # lat_vals = [s["lat_max"]  for s in summary.values() if s["lat_max"]  is not None]
    # print(lat_vals)