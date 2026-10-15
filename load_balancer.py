import asyncio
import os
import time

# List of server service names
SERVERS = [
    ("server1", 18861),
    ("server2", 18861),
    ("server3", 18861)
]

# Set algorithm
# Options: "least_connections" or "least_response_time"
ALGORITHM = os.getenv("LB_ALGORITHM", "least_connections")

# Metrics tracking
active_connections = {s[0]: 0 for s in SERVERS}
avg_response_times = {s[0]: 0.001 for s in SERVERS}

def select_server():
    """Selects a server (host, port) based on the active dynamic load-balancing algorithm."""

    if ALGORITHM == "least_connections":
        # Route to server with fewest active socket connections
        target = min(SERVERS, key=lambda s: active_connections[s[0]])
    elif ALGORITHM == "least_response_time":
        # Route based on combined latency metric and active connections
        target = min( 
            SERVERS,
            key=lambda s: avg_response_times[s[0]] * (active_connections[s[0]] + 1),
        )
    else:
        target = SERVERS[0]
    return target

async def pipe(reader, writer):
    """Bridge a TCP byte stream between client and server sockets."""
    
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle_client(client_reader, client_writer):
    """Handle an incoming client connection and proxy it to a backend server."""
    
    target_host, target_port = select_server()
    active_connections[target_host] += 1
    start_time = time.perf_counter()

    print(
        f"[LoadBalancer] [{ALGORITHM}] Routing client request -> {target_host} "
        f"(Active conns: {active_connections[target_host]})",
        flush=True,
    )

    try:
        server_reader, server_writer = await asyncio.open_connection(
            target_host,
            target_port,
        )
    except Exception as error:
        print(
            f"[LoadBalancer] Failed to connect to backend {target_host}: {error}",
            flush=True,
        )
        active_connections[target_host] = max(
            0,
            active_connections[target_host] - 1,
        )
        client_writer.close()
        await client_writer.wait_closed()
        return

    # Forward raw TCP traffic bidirectionally.
    try:
        await asyncio.gather(
            pipe(client_reader, server_writer),
            pipe(server_reader, client_writer),
            return_exceptions=True,
        )
    finally:
        # Measure response time and update metrics.
        elapsed = time.perf_counter() - start_time
        alpha = 0.2
        avg_response_times[target_host] = (
            (1 - alpha) * avg_response_times[target_host] + alpha * elapsed
        )
        active_connections[target_host] = max(
            0,
            active_connections[target_host] - 1,
        )


async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 18861)
    print(
        f"[LoadBalancer] Proxy listening on port 18861 using algorithm: "
        f"'{ALGORITHM}'...",
        flush=True,
    )

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())