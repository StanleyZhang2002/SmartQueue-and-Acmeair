import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv("datasets_a1/dataset_large_20251010-192118.csv", parse_dates=["iso_time"])

# Metrics to plot
metrics = ["cpu_pct", "mem_pct", "gc_count_sum", "http_time_max", "req_in_sum", "tps"]


# Get unique services
services = df['service'].unique()

# Create figure with 6 subplots (2 rows x 3 columns)
fig, axes = plt.subplots(2, 3, figsize=(20, 10))
axes = axes.flatten()

for i, metric in enumerate(metrics):
    ax = axes[i]
    for service in services:
        service_data = df[df['service'] == service]
        ax.plot(service_data['timestamp'], service_data[metric], label=service)
    ax.set_title(metric)
    ax.set_xlabel("Timestamp")
    ax.set_ylabel(metric)
    ax.legend(fontsize=8)
    ax.grid(True)

plt.tight_layout()
plt.show()