"""Asyncio-based TCP Server for Mini-Redis."""

import asyncio
import logging
from typing import Optional

try:
    from src.commands import CommandHandler
    from src.datastore import DataStore
    from src.protocol import RESPParser, ProtocolError
except ModuleNotFoundError:
    from commands import CommandHandler
    from datastore import DataStore
    from protocol import RESPParser, ProtocolError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("MiniRedisServer")


class RedisServer:
    """High-performance asynchronous Redis clone server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379) -> None:
        self.host = host
        self.port = port
        self.datastore = DataStore()
        self.command_handler = CommandHandler(self.datastore)
        self._server: Optional[asyncio.AbstractServer] = None

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer_name = writer.get_extra_info("peername")
        logger.info(f"Client connected from {peer_name}")

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

                    if isinstance(parsed, list):
                        response = self.command_handler.execute(parsed)
                    elif isinstance(parsed, str):
                        response = self.command_handler.execute([parsed])
                    else:
                        response = Exception("ERR invalid command format")

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

        async with self._server:
            await self._server.serve_forever()


def main() -> None:
    server = RedisServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Mini-Redis server shutting down cleanly...")


if __name__ == "__main__":
    main()