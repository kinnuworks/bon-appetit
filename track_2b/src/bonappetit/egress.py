"""Fail loudly if this container can reach the internet. Used by `make airgap`."""
import socket
import sys

TARGETS = [("1.1.1.1", 443), ("9.9.9.9", 53), ("huggingface.co", 443), ("api.openai.com", 443)]


def main() -> int:
    leaks = []
    for host, port in TARGETS:
        try:
            with socket.create_connection((host, port), timeout=3):
                leaks.append(f"{host}:{port}")
        except OSError:
            pass
    if leaks:
        print("EGRESS TEST FAILED, reachable:", ", ".join(leaks))
        return 1
    print(f"egress test passed: 0 of {len(TARGETS)} outside hosts reachable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
