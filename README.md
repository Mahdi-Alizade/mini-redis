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