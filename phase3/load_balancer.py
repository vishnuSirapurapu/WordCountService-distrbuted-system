"""TCP load balancer for the Phase 3 word-count replicas."""

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


def select_server():
    """Select the least-loaded server and rotate equal-score ties."""
    if ALGORITHM == "least_connections":
        scores = {
            host: active_connections[host]
            for host, _ in SERVERS
        }
    else:
        scores = {
            host: average_response_times[host] * (active_connections[host] + 1)
            for host, _ in SERVERS
        }

    best_score = min(scores.values())
    candidates = [
        server for server in SERVERS if scores[server[0]] == best_score
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

    target_host, target_port = select_server()
    tie_break_index += 1
    active_connections[target_host] += 1
    started = time.perf_counter()

    print(
        f"[LoadBalancer] algorithm={ALGORITHM} "
        f"backend={target_host} "
        f"active={active_connections[target_host]}",
        flush=True,
    )

    try:
        server_reader, server_writer = await asyncio.open_connection(
            target_host,
            target_port,
        )
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
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
