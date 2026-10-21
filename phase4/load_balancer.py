"""TCP load balancer for the word-count replicas (Phase 3 + Phase 4 fault tolerance)."""

import asyncio
import os
import time


SERVERS = (
    ("server1", 18861),
    ("server2", 18861),
    ("server3", 18861),
)
ALLOWED_ALGORITHMS = {"least_connections", "least_response_time"}
ALGORITHM = os.getenv("ALGORITHM", "least_connections").strip().lower()

if ALGORITHM not in ALLOWED_ALGORITHMS:
    raise ValueError(
        f"Unsupported ALGORITHM={ALGORITHM!r}; "
        f"choose one of {sorted(ALLOWED_ALGORITHMS)}"
    )

active_connections = {host: 0 for host, _ in SERVERS}
average_response_times = {host: 0.001 for host, _ in SERVERS}
tie_break_index = 0

# --- Phase 4: health monitoring ------------------------------------------
HEALTH_INTERVAL = 1.0   # seconds between health checks
HEALTH_TIMEOUT = 0.5    # a health check / connect attempt fails after this
FAIL_THRESHOLD = 2      # consecutive failed checks before a server is DOWN
RECOVER_THRESHOLD = 2   # consecutive successful checks before it is UP again

healthy = {host: True for host, _ in SERVERS}
fail_streak = {host: 0 for host, _ in SERVERS}
ok_streak = {host: 0 for host, _ in SERVERS}


def healthy_summary():
    up = [host for host, _ in SERVERS if healthy[host]]
    return f"{len(up)}/{len(SERVERS)} healthy ({','.join(up) or 'none'})"


def mark_down(host, reason):
    ok_streak[host] = 0
    if healthy[host]:
        healthy[host] = False
        print(f"[LoadBalancer] HEALTH {host} DOWN reason={reason} "
              f"-> {healthy_summary()}", flush=True)


def mark_up(host):
    fail_streak[host] = 0
    if not healthy[host]:
        healthy[host] = True
        print(f"[LoadBalancer] HEALTH {host} UP -> {healthy_summary()}",
              flush=True)


async def probe(host, port):
    """Health check: can a TCP connection to the replica be opened?"""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), HEALTH_TIMEOUT)
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    return True


async def health_monitor():
    """Periodically check every replica and update its health status."""
    while True:
        results = await asyncio.gather(*(probe(h, p) for h, p in SERVERS))
        for (host, _), alive in zip(SERVERS, results):
            if alive:
                fail_streak[host] = 0
                ok_streak[host] += 1
                if not healthy[host] and ok_streak[host] >= RECOVER_THRESHOLD:
                    mark_up(host)
            else:
                ok_streak[host] = 0
                fail_streak[host] += 1
                if healthy[host] and fail_streak[host] >= FAIL_THRESHOLD:
                    mark_down(host, "health-check")
        await asyncio.sleep(HEALTH_INTERVAL)


def select_server(exclude=()):
    """Select the least-loaded healthy server and rotate equal-score ties."""
    pool = [
        server for server in SERVERS
        if healthy[server[0]] and server[0] not in exclude
    ]
    if not pool:
        return None

    if ALGORITHM == "least_connections":
        scores = {
            host: active_connections[host]
            for host, _ in pool
        }
    else:
        scores = {
            host: average_response_times[host] * (active_connections[host] + 1)
            for host, _ in pool
        }

    best_score = min(scores.values())
    candidates = [
        server for server in pool if scores[server[0]] == best_score
    ]
    selected = candidates[tie_break_index % len(candidates)]
    return selected


async def pipe(reader, writer):
    """Forward bytes until the source closes its half of the connection."""
    try:
        while data := await reader.read(4096):
            writer.write(data)
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def handle_client(client_reader, client_writer):
    """Proxy one client TCP connection to a dynamically selected replica."""
    global tie_break_index

    # Phase 4: connect to a healthy replica; if it cannot be reached, mark it
    # DOWN and transparently retry the request on another healthy replica.
    tried = set()
    while True:
        selected = select_server(tried)
        if selected is None:
            print("[LoadBalancer] no healthy backend available", flush=True)
            client_writer.close()
            return
        target_host, target_port = selected
        tie_break_index += 1
        active_connections[target_host] += 1
        try:
            server_reader, server_writer = await asyncio.wait_for(
                asyncio.open_connection(target_host, target_port),
                HEALTH_TIMEOUT,
            )
            break
        except (OSError, asyncio.TimeoutError) as error:
            active_connections[target_host] -= 1
            tried.add(target_host)
            print(f"[LoadBalancer] backend={target_host} "
                  f"connect_error={type(error).__name__} -> retrying",
                  flush=True)
            mark_down(target_host, "connect-failed")

    started = time.perf_counter()

    print(
        f"[LoadBalancer] algorithm={ALGORITHM} "
        f"backend={target_host} "
        f"active={active_connections[target_host]}",
        flush=True,
    )

    try:
        await asyncio.gather(
            pipe(client_reader, server_writer),
            pipe(server_reader, client_writer),
        )
    except Exception as error:
        print(
            f"[LoadBalancer] backend={target_host} error={error}",
            flush=True,
        )
    finally:
        elapsed = time.perf_counter() - started
        alpha = 0.2
        average_response_times[target_host] = (
            (1 - alpha) * average_response_times[target_host]
            + alpha * elapsed
        )
        active_connections[target_host] = max(
            0,
            active_connections[target_host] - 1,
        )


async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 18861)
    print(
        f"[LoadBalancer] listening on 18861; algorithm={ALGORITHM}; "
        f"backends={','.join(host for host, _ in SERVERS)}",
        flush=True,
    )
    monitor = asyncio.create_task(health_monitor())  # Phase 4
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())