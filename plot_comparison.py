import csv
import os

import matplotlib.pyplot as plt


# Input CSV file paths from subfolders.
PHASE2_SUMMARY = os.path.join("phase1-2", "results", "latency_summary.csv")
PHASE3_ALGO1_SUMMARY = os.path.join("phase3", "results", "latency_summary_least_connections.csv")
PHASE3_ALGO2_SUMMARY = os.path.join("phase3", "results", "latency_summary_least_response_time.csv")

OUTPUT_DIR = "comparison_results"

def read_summary_csv(filepath):
    """Read rates, average latencies, and P99 latencies from a CSV file."""
    rates = []
    averages = []
    p99_values = []

    if not os.path.exists(filepath):
        print(f"Warning: File not found -> {filepath}")
        return rates, averages, p99_values

    with open(filepath, "r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rates.append(int(row["target_rate_rps"]))
            averages.append(float(row["average_latency_ms"]))
            p99_values.append(float(row["p99_latency_ms"]))

    return rates, averages, p99_values


def main():
    # Ensure the comparison output directory exists.
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Read summary results from each phase and load-balancing algorithm.
    r2, avg2, p99_2 = read_summary_csv(PHASE2_SUMMARY)
    r3_a1, avg3_a1, p99_3_a1 = read_summary_csv(PHASE3_ALGO1_SUMMARY)
    r3_a2, avg3_a2, p99_3_a2 = read_summary_csv(PHASE3_ALGO2_SUMMARY)

    # Determine common x-axis ticks based on available data.
    all_rates = sorted(set(r2 + r3_a1 + r3_a2))

    # Figure 1: Average request execution latency comparison.
    plt.figure(figsize=(8, 5))

    if r2:
        plt.plot(r2, avg2, marker="o", label="Phase 2: Single Server")
    if r3_a1:
        plt.plot(r3_a1, avg3_a1, marker="s", label="Phase 3: Cluster (Least Connections)")
    if r3_a2:
        plt.plot(r3_a2, avg3_a2, marker="^", label="Phase 3: Cluster (Least Response Time)")

    plt.xlabel("Keyword request rate (requests/second)")
    plt.ylabel("Request execution latency (ms)")
    plt.title("Comparative Average Request Execution Latency")
    if all_rates:
        plt.xticks(all_rates)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "combined_average_latency.png"), dpi=300)
    plt.close()

    # Figure 2: 99th-percentile (tail) latency comparison.
    plt.figure(figsize=(8, 5))
    if r2:
        plt.plot(r2, p99_2, marker="o", label="Phase 2: Single Server")
    if r3_a1:
        plt.plot(r3_a1, p99_3_a1, marker="s", label="Phase 3: Cluster (Least Connections)")
    if r3_a2:
        plt.plot(r3_a2, p99_3_a2, marker="^", label="Phase 3: Cluster (Least Response Time)")

    plt.xlabel("Keyword request rate (requests/second)")
    plt.ylabel("Request execution latency (ms)")
    plt.title("Comparative 99th-Percentile (P99) Request Execution Latency")
    if all_rates:
        plt.xticks(all_rates)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        os.path.join(OUTPUT_DIR, "combined_p99_latency.png"), dpi=300)
    plt.close()

    print("\nComparison analysis complete.")
    print(f"Figures saved to {OUTPUT_DIR}/combined_average_latency.png and "f"{OUTPUT_DIR}/combined_p99_latency.png")

if __name__ == "__main__":
    main()
