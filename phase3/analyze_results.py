import os
import csv
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np


RESULTS_DIR = "results"

# Detect active algorithm
ALGORITHM = os.environ.get("ALGORITHM", "least_connections").strip().lower()

INPUT_FILE = os.path.join(RESULTS_DIR, "latency_results.csv")
SUMMARY_FILE = os.path.join(RESULTS_DIR, "latency_summary.csv")
ALGO_SUMMARY_FILE = os.path.join(RESULTS_DIR, f"latency_summary_{ALGORITHM}.csv")


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Group individual latency measurements by target request rate.
    grouped_latencies = defaultdict(list)

    with open(INPUT_FILE, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rate = int(row["target_rate_rps"])
            latency = float(row["latency_ms"])
            grouped_latencies[rate].append(latency)

    rates = sorted(grouped_latencies.keys())
    summary = []

    # Calculate the average and P99 latency for each rate.
    for rate in rates:
        latencies = grouped_latencies[rate]

        average_latency = sum(latencies) / len(latencies)
        p99_latency = float(np.percentile(latencies, 99))

        summary.append({
            "target_rate_rps": rate,
            "request_count": len(latencies),
            "average_latency_ms": average_latency,
            "p99_latency_ms": p99_latency,
        })

        print(
            f"{rate} requests/sec | "
            f"Count: {len(latencies)} | "
            f"Average: {average_latency:.4f} ms | "
            f"P99: {p99_latency:.4f} ms"
        )

    # Save to latency_summary.csv and the algo-specific CSV automatically
    for filepath in [SUMMARY_FILE, ALGO_SUMMARY_FILE]:
        with open(filepath, "w", newline="") as file:
            fieldnames = [
                "target_rate_rps",
                "request_count",
                "average_latency_ms",
                "p99_latency_ms",
            ]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary)

    averages = [item["average_latency_ms"] for item in summary]
    p99_values = [item["p99_latency_ms"] for item in summary]

    # Figure 1: average request execution latency.
    plt.figure(figsize=(8, 5))
    plt.plot(rates, averages, marker="o")
    plt.xlabel("Keyword request rate (requests/second)")
    plt.ylabel("Request execution latency (ms)")
    plt.title("Average Request Execution Latency")
    plt.xticks(rates)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("results/average_latency.png", dpi=300)
    plt.close()

    # Figure 2: 99th-percentile (tail) latency.
    plt.figure(figsize=(8, 5))
    plt.plot(rates, p99_values, marker="o")
    plt.xlabel("Keyword request rate (requests/second)")
    plt.ylabel("Request execution latency (ms)")
    plt.title("99th-Percentile (P99) Request Execution Latency")
    plt.xticks(rates)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("results/p99_latency.png", dpi=300)
    plt.close()

    print("\nAnalysis complete.")
    print(f"Summary saved to {SUMMARY_FILE} and {ALGO_SUMMARY_FILE}")


if __name__ == "__main__":
    main()