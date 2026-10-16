Run the following PowerShell commands from the repository root; run the two
8a command blocks in separate terminals.

```powershell
# Phase 2
Copy-Item ".\phase3\benchmark.py" ".\phase1-2\benchmark_concurrent.py"
Set-Location ".\phase1-2"
docker compose down
docker compose up -d --build
docker compose exec client python benchmark_concurrent.py --host server --output results/latency_results.csv
docker compose exec client python analyze_results.py
docker compose down

# Phase 3: least connections
Set-Location "..\phase3"
$env:ALGORITHM = "least_connections"
docker compose down
docker compose up -d --build
docker compose exec client python benchmark.py --output results/latency_results.csv
docker compose exec client python analyze_results.py --output results/latency_summary_least_connections.csv
docker compose down

# Phase 3: least response time
$env:ALGORITHM = "least_response_time"
docker compose down
docker compose up -d --build
docker compose exec client python benchmark.py --output results/latency_results.csv
docker compose exec client python analyze_results.py --output results/latency_summary_least_response_time.csv
docker compose down

# Phase 3 part 8a: show request distribution
$env:ALGORITHM = "least_connections"
docker compose up -d --build
docker compose exec client python benchmark.py --rates 50 --duration 10 --concurrency 20
docker compose down

# 8a logs: run in a second terminal while the benchmark is running
Set-Location ".\phase3"
docker compose logs -f --tail=0 load_balancer

# 8b Comparison
Set-Location ".."
python plot_comparison.py
```
