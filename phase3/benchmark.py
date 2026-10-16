"""Run a concurrent, rate-controlled latency benchmark.

The same script can benchmark Phase 2's single server or Phase 3's
load-balancer endpoint by changing --host.
"""

import argparse
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import rpyc


REQUEST_RATES = (50, 70, 90, 110, 130)
DEFAULT_DURATION = 10
DEFAULT_CONCURRENCY = 20
DEFAULT_KEYWORD = "apple"
DEFAULT_DOCUMENT = "sample.txt"
DEFAULT_OUTPUT = "results/latency_results.csv"
SERVER_PORT = 18861


def send_request(request_id, host, keyword, document):
    """Send one request and measure client-observed round-trip latency."""
    started = time.perf_counter()
    connection = None
    try:
        connection = rpyc.connect(host, SERVER_PORT)
        result = connection.root.count_word(keyword, document)
        return {
            "request_id": request_id,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "success": 1,
            "result": result,
            "error": "",
        }
    except Exception as error:
        return {
            "request_id": request_id,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "success": 0,
            "result": "",
            "error": str(error),
        }
    finally:
        if connection is not None:
            connection.close()


def run_rate(host, rate, duration, concurrency, keyword, document):
    """Run one rate using bounded concurrent workers."""
    total_requests = rate * duration
    interval = 1.0 / rate
    results = []
    next_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {}
        for request_id in range(1, total_requests + 1):
            now = time.perf_counter()
            if now < next_start:
                time.sleep(next_start - now)

            future = executor.submit(
                send_request,
                request_id,
                host,
                keyword,
                document,
            )
            futures[future] = request_id
            next_start += interval

        for future in as_completed(futures):
            result = future.result()
            result["target_rate_rps"] = rate
            results.append(result)

    return sorted(results, key=lambda result: result["request_id"])


def write_results(output_path, results):
    output_directory = os.path.dirname(output_path)
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)

    fieldnames = [
        "target_rate_rps",
        "request_id",
        "latency_ms",
        "success",
        "result",
        "error",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Benchmark a word-count endpoint with concurrent requests."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("SERVER_HOST", "load_balancer"),
        help="Docker service or host name (default: %(default)s)",
    )
    parser.add_argument(
        "--rates",
        default=",".join(str(rate) for rate in REQUEST_RATES),
        help="comma-separated request rates (default: 50,70,90,110,130)",
    )
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--keyword", default=DEFAULT_KEYWORD)
    parser.add_argument("--document", default=DEFAULT_DOCUMENT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.duration < 1:
        parser.error("--duration must be at least 1")
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    try:
        args.rates = tuple(int(rate.strip()) for rate in args.rates.split(","))
    except ValueError:
        parser.error("--rates must be a comma-separated list of integers")
    if not args.rates or any(rate < 1 for rate in args.rates):
        parser.error("--rates must contain only positive integers")
    return args


def main():
    args = parse_args()
    all_results = []
    print(
        f"Benchmarking {args.host} with {args.concurrency} workers "
        f"for {args.duration}s at each rate: {args.rates}",
        flush=True,
    )

    for rate in args.rates:
        print(f"Running {rate} requests/second...", flush=True)
        rate_results = run_rate(
            args.host,
            rate,
            args.duration,
            args.concurrency,
            args.keyword,
            args.document,
        )
        all_results.extend(rate_results)
        successful = sum(row["success"] for row in rate_results)
        print(
            f"Completed {successful}/{len(rate_results)} requests at {rate} RPS",
            flush=True,
        )

    write_results(args.output, all_results)
    print(f"Raw per-request results saved to {args.output}", flush=True)


if __name__ == "__main__":
    main()
