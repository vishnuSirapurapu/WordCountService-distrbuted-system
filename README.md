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


# Phase 4 part 9: least connections, terminal 1
cd ".\phase3"
$env:ALGORITHM = "least_connections"
docker compose up -d --build redis server1 server2 server3 load_balancer
docker compose ps -a
docker compose run --rm client python benchmark.py --rates 50 --duration 40 --concurrency 20 --output results/fault_phase3_least_connections.csv

# Phase 4 part 9: least connections, terminal 2 (start right after the benchmark starts)
cd ".\phase3"
Start-Sleep 12
docker kill wordcount-server2
$killed = docker inspect -f '{{.State.FinishedAt}}' wordcount-server2
docker compose ps -a
Start-Sleep 12
docker start wordcount-server2
$restarted = docker inspect -f '{{.State.StartedAt}}' wordcount-server2
docker compose ps -a
# when terminal 1 has finished
docker compose logs -t --no-log-prefix load_balancer | Out-File -Encoding utf8 results/fault_phase3_least_connections_lb.log
python ..\phase4\analyze_results.py --fault --input results/fault_phase3_least_connections.csv --lb-log results/fault_phase3_least_connections_lb.log --killed-at $killed --restarted-at $restarted
docker compose logs --no-log-prefix load_balancer | Select-String "error" | Select-Object -First 10
docker compose down

# Phase 4 part 9: least response time, terminal 1
$env:ALGORITHM = "least_response_time"
docker compose up -d --build redis server1 server2 server3 load_balancer
docker compose ps -a
docker compose run --rm client python benchmark.py --rates 50 --duration 40 --concurrency 20 --output results/fault_phase3_least_response_time.csv

# Phase 4 part 9: least response time, terminal 2 (start right after the benchmark starts)
Start-Sleep 12
docker kill wordcount-server2
$killed = docker inspect -f '{{.State.FinishedAt}}' wordcount-server2
docker compose ps -a
Start-Sleep 12
docker start wordcount-server2
$restarted = docker inspect -f '{{.State.StartedAt}}' wordcount-server2
docker compose ps -a
# when terminal 1 has finished
docker compose logs -t --no-log-prefix load_balancer | Out-File -Encoding utf8 results/fault_phase3_least_response_time_lb.log
python ..\phase4\analyze_results.py --fault --input results/fault_phase3_least_response_time.csv --lb-log results/fault_phase3_least_response_time_lb.log --killed-at $killed --restarted-at $restarted
docker compose logs --no-log-prefix load_balancer | Select-String "error" | Select-Object -First 10
docker compose down

# Phase 4 part 10: the health monitoring is implemented in phase4\load_balancer.py

# Phase 4 part 11: least connections, terminal 1
cd "..\phase4"
$env:ALGORITHM = "least_connections"
docker compose up -d --build redis server1 server2 server3 load_balancer
docker compose ps -a
docker compose run --rm client python benchmark.py --rates 50 --duration 40 --concurrency 20 --output results/fault_phase4_least_connections.csv

# Phase 4 part 11: least connections, terminal 2 (start right after the benchmark starts)
cd "..\phase4"
Start-Sleep 12
docker kill wordcount-server2
$killed = docker inspect -f '{{.State.FinishedAt}}' wordcount-server2
docker compose ps -a
Start-Sleep 12
docker start wordcount-server2
$restarted = docker inspect -f '{{.State.StartedAt}}' wordcount-server2
docker compose ps -a
# when terminal 1 has finished
docker compose logs -t --no-log-prefix load_balancer | Out-File -Encoding utf8 results/fault_phase4_least_connections_lb.log
python ..\phase4\analyze_results.py --fault --input results/fault_phase4_least_connections.csv --lb-log results/fault_phase4_least_connections_lb.log --killed-at $killed --restarted-at $restarted
docker compose logs -t --no-log-prefix load_balancer | Select-String "HEALTH"
docker compose down

# Phase 4 part 11: least response time, terminal 1
$env:ALGORITHM = "least_response_time"
docker compose up -d --build redis server1 server2 server3 load_balancer
docker compose ps -a
docker compose run --rm client python benchmark.py --rates 50 --duration 40 --concurrency 20 --output results/fault_phase4_least_response_time.csv

# Phase 4 part 11: least response time, terminal 2 (start right after the benchmark starts)
Start-Sleep 12
docker kill wordcount-server2
$killed = docker inspect -f '{{.State.FinishedAt}}' wordcount-server2
docker compose ps -a
Start-Sleep 12
docker start wordcount-server2
$restarted = docker inspect -f '{{.State.StartedAt}}' wordcount-server2
docker compose ps -a
# when terminal 1 has finished
docker compose logs -t --no-log-prefix load_balancer | Out-File -Encoding utf8 results/fault_phase4_least_response_time_lb.log
python ..\phase4\analyze_results.py --fault --input results/fault_phase4_least_response_time.csv --lb-log results/fault_phase4_least_response_time_lb.log --killed-at $killed --restarted-at $restarted
docker compose logs -t --no-log-prefix load_balancer | Select-String "HEALTH"
docker compose down
```
