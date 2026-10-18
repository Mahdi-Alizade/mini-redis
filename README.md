<div align="center">

# ⚡ Mini-Redis

**A robust, asynchronous in-memory key-value store and Redis clone built from scratch in Python.**

[![CI](https://github.com/MahdiAlizadeh/mini-redis/actions/workflows/ci.yml/badge.svg)](https://github.com/MahdiAlizadeh/mini-redis/actions)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Redis CLI Compatible](https://img.shields.io/badge/RESP2-Compatible-red)

</div>

---

## 🎯 Overview

Mini-Redis is an educational yet production-minded clone of Redis. Built using Python's native non-blocking `asyncio` event loop, it completely implements the **Redis Serialization Protocol (RESP2)**.

It includes real-time disk persistence (**Append-Only File - AOF**) with **Atomic Log Compaction (`BGREWRITEAOF`)**, granular **Key Expiration (TTL)**, rich data structures (**Strings, Lists, Sets, and Hashes**), and connection authorization guards via `AUTH`.

You can interact with it using either the **official `redis-cli`** or the included built-in interactive Python client.

---

## ✨ Features

- **⚡ Asynchronous TCP Engine**: Non-blocking network I/O capable of handling multiple concurrent clients without thread thrashing.
- **💾 AOF Persistence & Compaction**: Write-ahead transaction logging ensuring zero data loss across server restarts, paired with safe log compaction (`BGREWRITEAOF`) that eliminates redundant historical operations.
- **🔐 Connection Security**: Optional password-based access control via `AUTH` command and environment variable configuration.
- **📡 RESP2 Streaming Parser**: Pure byte-stream parsing supporting Simple Strings, Errors, Integers, Bulk Strings, and Arrays.
- **⏳ Active & Lazy TTL**: Key eviction mechanics supporting both `EX` (seconds) and `PX` (milliseconds) duration flags.
- **🧩 4 Core Data Structures**: Full handling for Strings, Lists, Sets, and Hash Dictionaries.
- **🛡️ Zero Runtime Dependencies**: Relies exclusively on standard library modules.

---

## 📋 Command Matrix

| Category | Commands | Description |
| :--- | :--- | :--- |
| **Strings & Numbers** | `SET`, `GET`, `INCR`, `DECR` | Value manipulation with optional `EX`/`PX` expiration |
| **Hashes** | `HSET`, `HGET`, `HDEL`, `HEXISTS`, `HGETALL` | Nested key-value dictionary structures |
| **Lists** | `LPUSH`, `RPUSH`, `LRANGE` | Bidirectional queue and linked-list operations |
| **Sets** | `SADD`, `SMEMBERS` | Unique, unordered collection manipulation |
| **Persistence** | `BGREWRITEAOF` | Asynchronously compacts append-only log to minimal state snapshot |
| **Keys & Lifecycle** | `DEL`, `EXISTS`, `EXPIRE`, `TTL`, `KEYS`, `FLUSHALL` | Store introspection and key eviction |
| **Connection & Security** | `AUTH`, `PING`, `ECHO`, `QUIT` | Session authorization and diagnostic probes |

---

## 🏗️ Architecture & AOF Compaction

When write traffic grows, the append-only log accumulates obsolete commands (e.g., deleted keys or intermediate `INCR` steps). Mini-Redis solves log bloat via **Atomic Compaction**:

1. Takes an in-memory snapshot of active keys and remaining TTL values.
2. Writes the minimal reconstruction commands into an isolated temp file (`appendonly.aof.tmp`).
3. Safely swaps the temp file with the active log using an atomic filesystem operation (`os.replace`).

```text
                     +---------------------------+
                     |  Client (redis-cli / App) |
                     +-------------+-------------+
                                   | (Raw RESP2 TCP Stream)
                                   v
                     +---------------------------+
                     |       src/server.py       |
                     |  - Asyncio TCP Server     |
                     |  - Connection Auth Guard  |
                     +-------------+-------------+
                                   |
                                   v
                     +---------------------------+
                     |       src/protocol.py     |
                     |  (Streaming RESP Parser)  |
                     +-------------+-------------+
                                   |
                                   v
                     +---------------------------+
                     |       src/commands.py     |
                     |  (Command Dispatch Table) |
                     +-------------+-------------+
                                   |
                       +-----------+-----------+
                       |                       |
                       v                       v
         +---------------------------+   +---------------------------+
         |      src/datastore.py     |   |        src/aof.py         |
         |  - RAM Hash-Maps          |   |  - Append-Only File Log   |
         |  - Expiration (TTL) Heap  |   |  - BGREWRITEAOF Engine    |
         |  - State Snapshot Engine  |   |  - Atomic OS Log Swapper  |
         +---------------------------+   +---------------------------+
🚀 Quick Start
1. Installation
Bash
# Clone the repository
git clone [https://github.com/MahdiAlizadeh/mini-redis.git](https://github.com/MahdiAlizadeh/mini-redis.git)
cd mini-redis

# Create and activate virtual environment (Windows)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dev/test dependencies
pip install -r requirements.txt
2. Configure & Run Server
Run with default settings (no password required):

Bash
python -m src.server
Or enable authentication by setting the environment variable:

PowerShell
$env:MINI_REDIS_PASSWORD = "your_secure_password"
python -m src.server
3. Connect & Interact
Connect via the built-in interactive CLI:

Bash
python -m src.client
Or connect via the official Redis CLI:

Bash
redis-cli -p 6379
💻 Interactive Session Example
Plaintext
127.0.0.1:6379> AUTH your_secure_password
"OK"

127.0.0.1:6379> SET user:1001 "Mahdi" EX 60
"OK"

127.0.0.1:6379> TTL user:1001
(integer) 58

127.0.0.1:6379> HSET user:profile name "Mahdi" role "Admin" visits 1
(integer) 3

127.0.0.1:6379> HGETALL user:profile
1) "name"
2) "Mahdi"
3) "role"
4) "Admin"
5) "visits"
6) "1"

127.0.0.1:6379> BGREWRITEAOF
"Background append only file rewriting started"
🧪 Testing
The test suite validates socket event loops, AOF write and recovery sequences, AOF rewrite file size reduction, authentication gates, and all data structure operations:

Bash
pytest -v
📄 License
Distributed under the MIT License. See LICENSE for more information.