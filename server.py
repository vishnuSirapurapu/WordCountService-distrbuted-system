import os
import re

import redis
import rpyc
from rpyc.utils.server import ThreadedServer


# Directory containing the text files available to the service.
DOCUMENT_DIR = "/app/documents"

# Docker Compose service name and default Redis port.
REDIS_HOST = "redis"
REDIS_PORT = 6379

# Port used for client-server communication through RPyC.
RPYC_PORT = 18861


class WordCountService(rpyc.Service):
    """Handle remote word-count requests and cache their results."""

    def on_connect(self, conn):
        # Create a Redis connection for this client connection.
        self.cache = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )

        # Check that Redis is reachable.
        self.cache.ping()
        print("Connected to Redis", flush=True)

    def exposed_count_word(self, keyword, document_ref):
        # RPyC exposes methods prefixed with 'exposed_' to remote clients.
        # Reject an empty keyword.
        if not keyword or not keyword.strip():
            raise ValueError("Keyword cannot be empty")

        # Restrict the reference to a filename, not an arbitrary path.
        filename = os.path.basename(document_ref)
        filepath = os.path.realpath(
            os.path.join(DOCUMENT_DIR, filename)
        )

        # Prevent paths outside the documents directory from being accessed.
        documents_root = os.path.realpath(DOCUMENT_DIR)
        if not filepath.startswith(documents_root + os.sep):
            raise ValueError("Invalid document reference")

        # Fail clearly if the requested document does not exist.
        if not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"Document not found: {filename}"
            )

        # Normalize the keyword so case differences share a cache entry.
        cache_key = (
            f"wordcount:{filename}:{keyword.strip().casefold()}"
        )

        # First look for a previously calculated result in Redis.
        cached_result = self.cache.get(cache_key)

        if cached_result is not None:
            print(f"Cache HIT: {cache_key}", flush=True)
            return int(cached_result)

        # If no cached value exists, calculate the result from the file.
        print(f"Cache MISS: {cache_key}", flush=True)

        with open(filepath, "r", encoding="utf-8") as document:
            text = document.read()

        # Count whole-word matches, ignoring capitalization.
        # re.escape prevents special characters in the keyword
        # from being interpreted as regular-expression operators.
        pattern = rf"\b{re.escape(keyword.strip())}\b"
        count = len(
            re.findall(pattern, text, flags=re.IGNORECASE)
        )

        # Save the calculated result for future identical requests.
        self.cache.set(cache_key, count)
        return count


if __name__ == "__main__":
    # Listen on all interfaces so other containers can connect.
    server = ThreadedServer(
        WordCountService,
        hostname="0.0.0.0",
        port=RPYC_PORT
    )

    print(
        f"Word Count server listening on port {RPYC_PORT}",
        flush=True
    )
    server.start()