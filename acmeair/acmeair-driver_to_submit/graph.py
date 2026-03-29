
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
from datetime import datetime


def unique_outpath_for_graph(stem, out_dir, suffix: str = ".png"):
    """
    Create a unique output path follow this pattern:
    <out_dir>/<stem>__summary_<YYYYMMDD-HHMMSS>.png
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    time_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return out_dir / f"{stem}__summary_{time_stamp}{suffix}"


def plot_csv(csv_path, out_dir, metrics):
    csv_path = Path(csv_path)
    out_dir = Path(out_dir)

    # Load
    df = pd.read_csv(csv_path, parse_dates=["iso_time"])

    # Sort by time
    if "iso_time" in df.columns:
        df = df.sort_values("iso_time")
        x_col = "iso_time"
        x_label = "Time (UTC)"
    else:
        # if iso_time missing
        df = df.sort_values("timestamp")
        x_col = "timestamp"
        x_label = "Timestamp"

    # Figure title 
    label = "unlabeled"
    if "label" in df.columns and not df["label"].isna().all():
        label = str(df["label"].iloc[0])

    title = f"{csv_path.stem}  |  label={label}"

    # Services
    services = sorted(df["service"].astype(str).unique())

    # subplot grid (2 x 3)
    fig, axes = plt.subplots(2, 3, figsize=(20, 10), sharex=True)
    axes = axes.flatten()

    plotted_any = False
    for i, metric in enumerate(metrics[:6]):  
        ax = axes[i]
        if metric not in df.columns:
            ax.set_title(f"{metric} (missing)")
            ax.axis("off")
            continue

        # Plot one line per service
        for service in services:
            svc_df = df[df["service"] == service]
            ax.plot(svc_df[x_col], svc_df[metric], label=service)

        ax.set_title(metric)
        ax.set_xlabel(x_label)
        ax.set_ylabel(metric)
        ax.grid(True)
        plotted_any = True

        # Put the legend only on the first subplot to avoid messy graphs
        if i == 0:
            ax.legend(fontsize=8, ncol=2, loc="best")

    # Hide any unused axes if <6 metrics were present
    for j in range(len(metrics), 6):
        axes[j].axis("off")

    # Main title + layout
    fig.suptitle(title, y=1.02, fontsize=14)
    plt.tight_layout()

    # Save to a unique path
    out_path = unique_outpath_for_graph(csv_path.stem, out_dir)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    if not plotted_any:
        print("[WARNING] None of the requested metrics were in the CSV; saved an empty layout.")
    print(f"[OK] Figure saved -> {out_path}")


if __name__ == "__main__":
    # Metrics to plot
    metrics = ["cpu_pct", "mem_pct", "gc_count_sum", "http_time_max", "req_in_sum", "tps"]
    parser = argparse.ArgumentParser(description="Plot AcmeAir metrics from one CSV into a single 6 panel figure.")
    parser.add_argument("csv", help="Path to a single CSV (any small/medium/large, adapt/noadapt).")
    parser.add_argument("--out-dir", default="figures", help="Directory to save the figure (default: figures/).")
    args = parser.parse_args()
    plot_csv(args.csv, out_dir=args.out_dir, metrics=metrics)