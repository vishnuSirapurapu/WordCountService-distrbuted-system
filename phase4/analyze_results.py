"""Summarize benchmark CSV data and create average/P99 latency figures."""

import argparse
import csv
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

import matplotlib.pyplot as plt


def percentile(values, percentile_value):
    """Calculate a percentile using linear interpolation."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def read_latencies(input_path):
    grouped = defaultdict(list)
    with open(input_path, "r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if row["success"] != "1":
                continue
            grouped[int(row["target_rate_rps"])].append(
                float(row["latency_ms"])
            )
    return grouped


def write_summary(output_path, summary):
    output_directory = os.path.dirname(output_path)
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)
    fieldnames = [
        "target_rate_rps",
        "request_count",
        "average_latency_ms",
        "p99_latency_ms",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)


def create_plot(summary, value_key, title, output_path):
    rates = [row["target_rate_rps"] for row in summary]
    values = [row[value_key] for row in summary]
    plt.figure(figsize=(8, 5))
    plt.plot(rates, values, marker="o")
    plt.xlabel("Keyword request rate (requests/second)")
    plt.ylabel("Request execution latency (ms)")
    plt.title(title)
    plt.xticks(rates)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


SETTLE = 3  # seconds after a kill/restart that the balancer needs to notice it


def to_epoch(text):
    """Convert a Docker timestamp (2026-10-20T08:55:12.123456789Z) to seconds."""
    base, _, fraction = text.strip().rstrip("Z").partition(".")
    moment = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    return moment.replace(tzinfo=timezone.utc).timestamp() + float("0." + fraction[:6])


def read_routed(path):
    """Return (time, server) for every request the balancer routed."""
    routed = []
    with open(path, encoding="utf-8", errors="ignore") as file:
        for line in file:
            match = re.search(r"(\d{4}-\d\d-\d\dT[\d:.]+Z) .*backend=(\S+) active=", line)
            if match:
                routed.append((to_epoch(match.group(1)), match.group(2)))
    return sorted(routed)


def analyze_fault(args):
    """Phase 4: requests per server and failed requests before the failure,
    while the server is down, and after it is restarted."""
    with open(args.input, newline="", encoding="utf-8") as file:
        rows = sorted(csv.DictReader(file), key=lambda row: int(row["request_id"]))
    outcomes = [row["success"] == "1" for row in rows]
    # The benchmark requests are the last routed lines of the log (this skips
    # the idle connection client.py opens at start-up), so request k started
    # when the balancer routed line k.
    routed = read_routed(args.lb_log)[-len(outcomes):]
    killed = to_epoch(args.killed_at)
    restarted = to_epoch(args.restarted_at)
    servers = sorted({server for _, server in routed})

    phases = [
        ("before failure", routed[0][0], killed),
        ("server down", killed, restarted),
        ("after restart", restarted, routed[-1][0] + 1),
    ]
    for name, start, stop in phases:
        first = start if name == "before failure" else start + SETTLE
        counts = Counter(s for t, s in routed if first <= t < stop)
        total = max(sum(counts.values()), 1)
        failed = sum(
            1 for (t, _), ok in zip(routed, outcomes)
            if start <= t < stop and not ok
        )
        shares = "  ".join(
            f"{s}: {counts[s]} ({100 * counts[s] / total:.0f}%)" for s in servers
        )
        print(f"{name:15s} {shares}  | failed requests: {failed}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="results/latency_results.csv")
    parser.add_argument("--output", default="results/latency_summary.csv")
    # Phase 4: analyze a run in which a server is killed and restarted.
    parser.add_argument("--fault", action="store_true")
    parser.add_argument("--lb-log")
    parser.add_argument("--killed-at")
    parser.add_argument("--restarted-at")
    args = parser.parse_args()
    if not os.path.isfile(args.input):
        parser.error(f"input CSV does not exist: {args.input}")
    if args.fault and not (args.lb_log and args.killed_at and args.restarted_at):
        parser.error("--fault needs --lb-log, --killed-at and --restarted-at")
    return args


def main():
    args = parse_args()
    if args.fault:
        analyze_fault(args)
        return
    grouped = read_latencies(args.input)
    if not grouped:
        raise ValueError("The input CSV contains no successful requests.")

    summary = []
    for rate in sorted(grouped):
        latencies = grouped[rate]
        summary.append({
            "target_rate_rps": rate,
            "request_count": len(latencies),
            "average_latency_ms": sum(latencies) / len(latencies),
            "p99_latency_ms": percentile(latencies, 99),
        })

    write_summary(args.output, summary)
    output_directory = os.path.dirname(args.output) or "."
    stem = os.path.splitext(os.path.basename(args.output))[0]
    create_plot(
        summary,
        "average_latency_ms",
        "Average Request Execution Latency",
        os.path.join(output_directory, f"{stem}_average.png"),
    )
    create_plot(
        summary,
        "p99_latency_ms",
        "99th-Percentile Request Execution Latency",
        os.path.join(output_directory, f"{stem}_p99.png"),
    )
    print(f"Summary saved to {args.output}", flush=True)


if __name__ == "__main__":
    main()