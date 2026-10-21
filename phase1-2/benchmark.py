import os
import csv
import time
import rpyc


# The server hostname is the Docker Compose service name.
SERVER_HOST = "server"
SERVER_PORT = 18861

# Use the sample document and keyword for every request.
KEYWORD = "lorem"
DOCUMENT = "sample.txt"

# Five target request rates used in the experiment.
REQUEST_RATES = [50, 70, 90, 110, 130]

# Each rate is tested for ten seconds.
TEST_DURATION_SECONDS = 10


def run_experiment(connection, request_rate):
    """Measure individual request-response latency in milliseconds."""
    latencies_ms = []

    # Time between scheduled request starts.
    interval = 1.0 / request_rate

    start_time = time.perf_counter()
    end_time = start_time + TEST_DURATION_SECONDS
    next_request_time = start_time

    # Schedule requests only within the fixed test window.
    while next_request_time < end_time:
        now = time.perf_counter()

        # Wait until the next scheduled request time.
        if now < next_request_time:
            time.sleep(next_request_time - now)

        # Do not start a request after the test window has ended.
        if time.perf_counter() >= end_time:
            break

        # Measure from immediately before the RPC call until response.
        request_start = time.perf_counter()
        connection.root.count_word(KEYWORD, DOCUMENT)
        request_end = time.perf_counter()

        # Convert seconds to milliseconds.
        latencies_ms.append(
            (request_end - request_start) * 1000
        )

        # Schedule the next request.
        next_request_time += interval

    return latencies_ms


def main():
    all_results = []

    # Establish one connection for the benchmark run.
    connection = rpyc.connect(SERVER_HOST, SERVER_PORT)

    try:
        for rate in REQUEST_RATES:
            print(f"Testing {rate} requests per second...")

            latencies = run_experiment(connection, rate)

            # Store each individual latency with its target rate.
            for latency in latencies:
                all_results.append({
                    "target_rate_rps": rate,
                    "latency_ms": latency
                })

            # This is the request count divided by the nominal
            # ten-second duration, not an independent wall-clock
            # measurement of achieved throughput.
            reported_rate = len(latencies) / TEST_DURATION_SECONDS

            print(
                f"Target rate: {rate} requests/sec | "
                f"Requests completed: {len(latencies)} | "
                f"Reported rate: {reported_rate:.2f} requests/sec"
            )

    finally:
        # Close the connection when all five tests are finished.
        connection.close()

    os.makedirs("results", exist_ok=True)

    # Save raw measurements so the analysis can be repeated later.
    with open("results/latency_results.csv", "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["target_rate_rps", "latency_ms"]
        )
        writer.writeheader()
        writer.writerows(all_results)

    print("Individual latency measurements saved to results/latency_results.csv")


if __name__ == "__main__":
    main()