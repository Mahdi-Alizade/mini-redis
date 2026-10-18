"""Asyncio-based TCP Server for Mini-Redis with AOF persistence and AUTH support."""

import os
import asyncio
import logging
from typing import Optional

try:
    from src.commands import CommandHandler
    from src.datastore import DataStore
    from src.protocol import RESPParser, ProtocolError
    from src.aof import AOFManager
except ModuleNotFoundError:
    from commands import CommandHandler
    from datastore import DataStore
    from protocol import RESPParser, ProtocolError
    from aof import AOFManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("MiniRedisServer")


class RedisServer:
    """High-performance asynchronous Redis clone server with persistence and authentication."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        aof_file: str = "appendonly.aof",
        password: Optional[str] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.required_password = password or os.getenv("MINI_REDIS_PASSWORD")
        self.aof_manager = AOFManager(filename=aof_file)
        self.datastore = DataStore(aof_manager=self.aof_manager)
        self.command_handler = CommandHandler(self.datastore)
        self._server: Optional[asyncio.AbstractServer] = None

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer_name = writer.get_extra_info("peername")
        logger.info(f"Client connected from {peer_name}")

        is_authenticated = self.required_password is None
        buffer = bytearray()

        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    logger.info(f"Client {peer_name} disconnected")
                    break

                buffer.extend(data)

                while buffer:
                    try:
                        parsed, consumed = RESPParser.parse_one(bytes(buffer))
                    except ProtocolError as exc:
                        writer.write(RESPParser.serialize(exc))
                        await writer.drain()
                        buffer.clear()
                        break

                    if consumed == 0:
                        break

                    del buffer[:consumed]

                    if parsed is None:
                        continue

                    # Extract command name and arguments
                    parts = []
                    if isinstance(parsed, list):
                        parts = parsed
                    elif isinstance(parsed, str):
                        parts = [parsed]
                    else:
                        writer.write(RESPParser.serialize(Exception("ERR invalid command format")))
                        await writer.drain()
                        continue

                    if not parts:
                        continue

                    cmd_name = str(parts[0]).upper()

                    # Handle QUIT command directly
                    if cmd_name == "QUIT":
                        writer.write(RESPParser.serialize_simple_string("OK"))
                        await writer.drain()
                        return

                    # Handle AUTH command
                    if cmd_name == "AUTH":
                        if len(parts) != 2:
                            response = Exception("ERR wrong number of arguments for 'auth' command")
                        elif self.required_password is None:
                            response = Exception("ERR Client sent AUTH, but no password is set")
                        elif parts[1] == self.required_password:
                            is_authenticated = True
                            response = "OK"
                        else:
                            response = Exception("ERR invalid password")

                        writer.write(RESPParser.serialize(response))
                        await writer.drain()
                        continue

                    # Guard unauthenticated access
                    if not is_authenticated:
                        err_msg = Exception("NOAUTH Authentication required.")
                        writer.write(RESPParser.serialize(err_msg))
                        await writer.drain()
                        continue

                    # Execute normal database commands
                    response = self.command_handler.execute(parts)
                    writer.write(RESPParser.serialize(response))
                    await writer.drain()

        except asyncio.CancelledError:
            pass
        except ConnectionResetError:
            logger.info(f"Connection reset by client {peer_name}")
        except Exception as exc:
            logger.error(f"Error handling client {peer_name}: {exc}", exc_info=True)
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self) -> None:
        """Starts the TCP server and listens for incoming connections."""
        self._server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        logger.info(f"Mini-Redis server running on {self.host}:{self.port}")
        logger.info(f"AOF persistence active using '{self.aof_manager.filename}'")
        if self.required_password:
            logger.info("Security: Password authentication enabled")

        async with self._server:
            await self._server.serve_forever()

    def stop(self) -> None:
        """Gracefully close background workers and open files."""
        if self.aof_manager:
            logger.info("Closing AOF persistence file handle...")
            self.aof_manager.close()


def main() -> None:
    server = RedisServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Mini-Redis server shutting down cleanly...")
    finally:
        server.stop()


if __name__ == "__main__":
    main()