markdown

# Mini-Redis

A lightweight, asynchronous, in-memory key-value database implemented in pure Python from scratch. The server speaks the Redis Serialization Protocol (RESP2) over a non-blocking TCP socket server powered by Python's native `asyncio` — and is fully compatible with the official `redis-cli` tool.

---

## Overview

Mini-Redis is a from-scratch implementation of a Redis-compatible server. It provides:

1. An asynchronous TCP socket server (port 6379) handling multiple concurrent connections via `asyncio`.
2. A full RESP2 protocol parser and serializer.
3. Native support for Strings, Lists, and Sets.
4. TTL and key expiration with both active and lazy strategies.
5. A zero-dependency runtime — only the Python standard library is used in production code.
6. A built-in interactive Python client for testing and exploration.

---

## Features

- **Pure Python, zero external runtime dependencies**
- **`asyncio` event loop** — non-blocking, concurrent connection handling
- **Full RESP2 parser/serializer** — Simple Strings, Errors, Integers, Bulk Strings, Arrays
- **Key expiration** — supports both `EX` (seconds) and `PX` (milliseconds) flags; active + lazy expiration
- **Built-in interactive client** — spawn a CLI session without `redis-cli`
- **100% test coverage** — `pytest` suite plus a GitHub Actions CI workflow
- **Compatible with `redis-cli`** — send commands from the official Redis client

---

## Tech Stack

- Python 3.11+
- `asyncio` — native async I/O
- `pytest` — testing
- Zero external runtime dependencies

---

## Installation

### Prerequisites

- Python 3.11+
- Git

### Steps

```bash
git clone https://github.com/<username>/mini-redis.git
cd mini-redis
Create and activate a virtual environment:

bash

python -m venv venv
Windows (PowerShell):
powershell

.\venv\Scripts\Activate.ps1
Linux / macOS:
bash

source venv/bin/activate
Install development dependencies (for pytest only):

bash

pip install pytest
No runtime dependencies are required.

Configuration
The server runs with sensible defaults and requires no configuration files or environment variables.

| Setting | Default | | --------------------- | ----------- | | Host | 127.0.0.1 | | Port | 6379 |

You can change the port by passing it as a command-line argument (see Usage).

Usage
Start the server
bash

python -m src.server
To bind a specific port:

bash

python -m src.server 7000
Connect with redis-cli
bash

redis-cli -p 6379
Connect with the built-in client
bash

python -m src.client
This launches an interactive prompt where you can type RESP commands directly.

Supported Commands
Key / Value
| Command | Description | | ------------------- | ------------------------------ | | SET key value | Store a string value | | GET key | Retrieve a string value | | DEL key [key ...] | Delete one or more keys | | EXISTS key [key ...] | Check if keys exist | | KEYS pattern | List keys matching a glob pattern | | FLUSHALL | Delete all keys |

Arithmetic
| Command | Description | | ------- | ----------------------- | | INCR key | Increment integer value by 1 | | DECR key | Decrement integer value by 1 |

TTL Management
| Command | Description | | --------------- | --------------------------------- | | EXPIRE key seconds | Set time-to-live in seconds | | TTL key | Get remaining time-to-live in seconds |

Lists
| Command | Description | | ------------------ | --------------------------------- | | LPUSH key value [value ...] | Prepend values to list | | RPUSH key value [value ...] | Append values to list | | LRANGE key start stop | Get a range of list elements |

Sets
| Command | Description | | ---------------------- | --------------------------------- | | SADD key member [member ...] | Add members to a set | | SMEMBERS key | Get all members of a set |

Server / Utility
| Command | Description | | ------------- | -------------------------- | | PING | Server liveness check | | ECHO message | Echo the input message | | QUIT | Close the connection |

CLI / API
Server
text

python -m src.server [port]
| Argument | Description | | -------------- | ----------------------- | | port | Port to bind to default: 6379 |

Client
text

python -m src.client [host] [port]
| Argument | Description | | -------------- | -------------------------------- | | host | Server host default: 127.0.0.1 | | port | Server port default: 6379 |

Project Structure
text

├── src/
│   ├── protocol.py      # RESP parser and serializer
│   ├── datastore.py     # In-memory storage engine + expiration logic
│   ├── commands.py      # Command dispatch and execution handler
│   ├── server.py        # Asyncio TCP socket server
│   └── client.py        # Interactive command-line client
├── tests/
│   └── test_server.py   # pytest test suite
└── README.md
Architecture
text

redis-cli / built-in client
          |
          v
  +---------------------+
  |  asyncio TCP Server |
  +---------------------+
          |
          v
  +---------------------+
  |   RESP Parser       |
  |   (protocol.py)     |
  +---------------------+
          |
          v
  +---------------------+
  |  Command Dispatcher |
  |  (commands.py)      |
  +---------------------+
          |
          v
  +---------------------+
  |   Datastore         |
  |  (datastore.py)     |
  +---------------------+
Each layer is decoupled for easy testing and modification.

Testing
Run the full test suite:

bash

pytest tests/ -v
The suite covers:

RESP protocol parsing and serialization
All implemented commands
TTL and expiration behaviors (active + lazy)
Concurrent connection handling
Edge cases and error handling
Coverage: 100%

Deployment
Mini-Redis is designed for educational purposes and lightweight local use. To run it persistently on a server:

Install Python 3.11+
Clone the repository
Start the server with python -m src.server
Optionally wrap it in systemd, supervisord, or a Docker container
No standalone configuration or service installation required.

Contributing
Contributions are welcome.

Fork the repository
Create a feature branch:
bash

git checkout -b feature/my-feature
Commit your changes
Push the branch
Open a pull request
Ensure all tests pass and coverage stays at 100%.

License
Released under the MIT License.

