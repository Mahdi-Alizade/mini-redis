"""Simple interactive TCP client to test Mini-Redis."""

import socket
import sys

try:
    from src.protocol import RESPParser
except ModuleNotFoundError:
    from protocol import RESPParser


def run_client(host: str = "127.0.0.1", port: int = 6379) -> None:
    print(f"Connecting to Mini-Redis at {host}:{port}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        print("Connected! Type commands (e.g. 'SET a 10', 'GET a', 'PING', 'QUIT' to exit):\n")
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {host}:{port}. Is the server running?")
        sys.exit(1)

    while True:
        try:
            line = input(f"{host}:{port}> ").strip()
            if not line:
                continue
            if line.upper() in ("QUIT", "EXIT"):
                print("Goodbye!")
                break

            parts = line.split()
            # Send command as RESP Array
            payload = RESPParser.serialize(parts)
            s.sendall(payload)

            # Read response
            response_data = s.recv(4096)
            parsed, _ = RESPParser.parse_one(response_data)

            if isinstance(parsed, Exception):
                print(f"(error) {parsed}")
            elif parsed is None:
                print("(nil)")
            elif isinstance(parsed, list):
                if not parsed:
                    print("(empty list or set)")
                for idx, item in enumerate(parsed, 1):
                    print(f"{idx}) \"{item}\"")
            elif isinstance(parsed, int):
                print(f"(integer) {parsed}")
            else:
                print(f"\"{parsed}\"")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as err:
            print(f"Connection error: {err}")
            break

    s.close()


if __name__ == "__main__":
    run_client()