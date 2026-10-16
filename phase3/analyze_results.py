"""Summarize benchmark CSV data and create average/P99 latency figures."""

import argparse
import csv
import os
from collections import defaultdict

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


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="results/latency_results.csv")
    parser.add_argument("--output", default="results/latency_summary.csv")
    args = parser.parse_args()
    if not os.path.isfile(args.input):
        parser.error(f"input CSV does not exist: {args.input}")
    return args


def main():
    args = parse_args()
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
