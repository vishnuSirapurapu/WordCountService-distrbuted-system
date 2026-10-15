# Execution Commands

**1. Start the containers**
```powershell
docker compose up -d --build
```

**2. Check container status**
```powershell
docker compose ps
```

**3. Run the client**
```powershell
docker compose exec client python client.py
```

**4. Run the latency benchmark**
```powershell
docker compose exec client python benchmark.py
```

**5. Analyze latency results**
```powershell
docker compose exec client python analyze_results.py
```

**6. Stop the containers**
```powershell
docker compose down
```