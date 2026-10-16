import csv
import os

import matplotlib.pyplot as plt


# Input CSV file paths from subfolders.
PHASE2_SUMMARY = os.path.join("phase1-2", "results", "latency_summary.csv")
PHASE3_ALGO1_SUMMARY = os.path.join("phase3", "results", "latency_summary_least_connections.csv")
PHASE3_ALGO2_SUMMARY = os.path.join("phase3", "results", "latency_summary_least_response_time.csv")
COMPARISON_SUMMARY = os.path.join("comparison_results", "comparison_summary.csv")

OUTPUT_DIR = "comparison_results"

def read_summary_csv(filepath):
    """Read rates, average latencies, and P99 latencies from a CSV file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Required summary file was not found: {filepath}. "
            "Run both Phase 3 algorithm benchmarks and their analyses first."
        )

    summary = {}
    with open(filepath, "r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rate = int(row["target_rate_rps"])
            summary[rate] = {
                "average_latency_ms": float(row["average_latency_ms"]),
                "p99_latency_ms": float(row["p99_latency_ms"]),
            }

    return summary


def percentage_difference(value, baseline):
    """Return the percentage change relative to the Phase 2 baseline."""
    if baseline == 0:
        return 0.0
    return ((value - baseline) / baseline) * 100


def main():
    # Ensure the comparison output directory exists.
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Read summary results from each phase and load-balancing algorithm.
    phase2 = read_summary_csv(PHASE2_SUMMARY)
    least_connections = read_summary_csv(PHASE3_ALGO1_SUMMARY)
    least_response_time = read_summary_csv(PHASE3_ALGO2_SUMMARY)

    rates = sorted(
        set(phase2) & set(least_connections) & set(least_response_time)
    )
    if not rates:
        raise ValueError("The summary files have no common request rates.")

    # Part 8b comparison table: positive percentages mean higher latency
    # than Phase 2, while negative percentages mean lower latency.
    comparison_rows = []
    for rate in rates:
        phase2_values = phase2[rate]
        connections_values = least_connections[rate]
        response_time_values = least_response_time[rate]
        comparison_rows.append({
            "target_rate_rps": rate,
            "phase2_average_latency_ms": phase2_values["average_latency_ms"],
            "phase2_p99_latency_ms": phase2_values["p99_latency_ms"],
            "least_connections_average_latency_ms": connections_values["average_latency_ms"],
            "least_connections_p99_latency_ms": connections_values["p99_latency_ms"],
            "least_connections_average_change_percent": percentage_difference(
                connections_values["average_latency_ms"],
                phase2_values["average_latency_ms"],
            ),
            "least_connections_p99_change_percent": percentage_difference(
                connections_values["p99_latency_ms"],
                phase2_values["p99_latency_ms"],
            ),
            "least_response_time_average_latency_ms": response_time_values["average_latency_ms"],
            "least_response_time_p99_latency_ms": response_time_values["p99_latency_ms"],
            "least_response_time_average_change_percent": percentage_difference(
                response_time_values["average_latency_ms"],
                phase2_values["average_latency_ms"],
            ),
            "least_response_time_p99_change_percent": percentage_difference(
                response_time_values["p99_latency_ms"],
                phase2_values["p99_latency_ms"],
            ),
        })

    with open(COMPARISON_SUMMARY, "w", newline="") as file:
        fieldnames = list(comparison_rows[0])
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison_rows)

    # Figure 1: Average request execution latency comparison.
    plt.figure(figsize=(8, 5))

    plt.plot(
        rates,
        [phase2[rate]["average_latency_ms"] for rate in rates],
        marker="o",
        label="Phase 2: Single Server",
    )
    plt.plot(
        rates,
        [least_connections[rate]["average_latency_ms"] for rate in rates],
        marker="s",
        label="Phase 3: Cluster (Least Connections)",
    )
    plt.plot(
        rates,
        [least_response_time[rate]["average_latency_ms"] for rate in rates],
        marker="^",
        label="Phase 3: Cluster (Least Response Time)",
    )

    plt.xlabel("Keyword request rate (requests/second)")
    plt.ylabel("Request execution latency (ms)")
    plt.title("Comparative Average Request Execution Latency")
    plt.xticks(rates)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "combined_average_latency.png"), dpi=300)
    plt.close()

    # Figure 2: 99th-percentile (tail) latency comparison.
    plt.figure(figsize=(8, 5))
    plt.plot(
        rates,
        [phase2[rate]["p99_latency_ms"] for rate in rates],
        marker="o",
        label="Phase 2: Single Server",
    )
    plt.plot(
        rates,
        [least_connections[rate]["p99_latency_ms"] for rate in rates],
        marker="s",
        label="Phase 3: Cluster (Least Connections)",
    )
    plt.plot(
        rates,
        [least_response_time[rate]["p99_latency_ms"] for rate in rates],
        marker="^",
        label="Phase 3: Cluster (Least Response Time)",
    )

    plt.xlabel("Keyword request rate (requests/second)")
    plt.ylabel("Request execution latency (ms)")
    plt.title("Comparative 99th-Percentile (P99) Request Execution Latency")
    plt.xticks(rates)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        os.path.join(OUTPUT_DIR, "combined_p99_latency.png"), dpi=300)
    plt.close()

    print("\nComparison analysis complete.")
    print(f"Figures saved to {OUTPUT_DIR}/combined_average_latency.png and "f"{OUTPUT_DIR}/combined_p99_latency.png")
    print(f"Comparison table saved to {COMPARISON_SUMMARY}")

if __name__ == "__main__":
    main()
