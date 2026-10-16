Run the following PowerShell commands from the repository root; run the two
8a command blocks in separate terminals.

```powershell
# Phase 2
cd ".\phase1-2"
docker compose down
docker compose up -d --build
docker compose exec client python benchmark.py
docker compose exec client python analyze_results.py
docker compose down

# Phase 3: least connections
cd "..\phase3"
$env:ALGORITHM = "least_connections"
docker compose down
docker compose up -d --build
docker compose exec client python benchmark.py
docker compose exec client python analyze_results.py --output results/latency_summary_least_connections.csv
docker compose down

# Phase 3: least response time
$env:ALGORITHM = "least_response_time"
docker compose down
docker compose up -d --build
docker compose exec client python benchmark.py
docker compose exec client python analyze_results.py --output results/latency_summary_least_response_time.csv
docker compose down

# Phase 3 part 8a: show request distribution
$env:ALGORITHM = "least_connections"
docker compose up -d --build
docker compose exec client python benchmark.py --rates 50 --duration 10 --concurrency 20
docker compose down

# 8a logs: run in a second terminal while the benchmark is running
cd ".\phase3"
docker compose logs -f --tail=0 load_balancer

# 8b Comparison
cd ".."
python plot_comparison.py
```
