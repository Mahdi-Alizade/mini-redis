# ⚡ Mini-Redis

An asynchronous, lightweight in-memory key-value database built from scratch in Python, implementing the Redis Serialization Protocol (RESP2).

Compatible with the official `redis-cli` and custom Redis clients.

---

## 🚀 Features

- **Event-Driven Architecture**: Non-blocking network I/O powered by Python's native `asyncio`.
- **RESP2 Compliant**: Complete parser and serializer handling Simple Strings, Errors, Integers, Bulk Strings, and Arrays.
- **Key Expiration & TTL**: Supports active and lazy expiration for temporary keys (`EX` and `PX` options).
- **Core Redis Commands**:
  - **Strings & Keys**: `SET`, `GET`, `DEL`, `EXISTS`, `EXPIRE`, `TTL`, `INCR`, `DECR`, `KEYS`, `FLUSHALL`
  - **Lists**: `LPUSH`, `RPUSH`, `LRANGE`
  - **Sets**: `SADD`, `SMEMBERS`
  - **System**: `PING`, `ECHO`
- **Zero External Runtime Dependencies**: Standard library only.

---

## 📁 Project Structure

```text
mini-redis/
├── .gitignore
├── requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   ├── protocol.py       # RESP parser and serializer
│   ├── datastore.py      # In-memory storage engine and TTL logic
│   ├── commands.py       # Redis command dispatch table
│   ├── server.py         # Asyncio TCP socket server
│   └── client.py         # Interactive CLI client
└── tests/
    └── test_server.py    # Automated test suite


🛠️ Quick Start
1. Clone & Setup Virtual Environment

git clone [https://github.com/](https://github.com/)<your-username>/mini-redis.git
cd mini-redis

# Create & activate venv
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

# Install test dependencies
pip install -r requirements.txt


2. Start the Server

python -m src.server

3. Connect & Run Commands
You can connect using the built-in CLI:

python -m src.client


Or connect via the official redis-cli:

redis-cli -p 6379


Example Usage

127.0.0.1:6379> PING
"PONG"

127.0.0.1:6379> SET user:1 "Mahdi"
"OK"

127.0.0.1:6379> GET user:1
"Mahdi"

127.0.0.1:6379> SET session_token "abc123xyz" EX 10
"OK"

127.0.0.1:6379> TTL session_token
(integer) 8

127.0.0.1:6379> LPUSH tasks "build" "test" "deploy"
(integer) 3

127.0.0.1:6379> LRANGE tasks 0 -1
1) "deploy"
2) "test"
3) "build"


🧪 Running Tests
Run the test suite using pytest:

pytest -v


📄 License
This project is licensed under the MIT License.

