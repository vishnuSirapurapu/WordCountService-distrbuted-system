import rpyc

# Docker Compose service name and RPyC server port.
SERVER_HOST = "load_balancer"
SERVER_PORT = 18861


def main():
    # Open a connection to the remote word-count server.
    connection = rpyc.connect(SERVER_HOST, SERVER_PORT)

    try:
        while True:
            # Ask the user which word to count and in which document.
            keyword = input("Enter a keyword (or 'exit' to quit): ").strip()

            if keyword.lower() == "exit":
                break

            document = input(
                "Enter document filename (e.g. sample.txt): "
            ).strip()

            try:
                # Call the server's remotely exposed method.
                result = connection.root.count_word(keyword, document)
                print(f"Occurrences of '{keyword}': {result}")

            except Exception as error:
                # Display server-side or communication errors.
                print(f"Request failed: {error}")

    finally:
        # Release the RPyC connection even if an error occurs.
        connection.close()


if __name__ == "__main__":
    main()