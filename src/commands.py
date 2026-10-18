"""Command dispatching and execution layer for Mini-Redis."""

from typing import Any, Callable, Dict, List

try:
    from src.datastore import DataStore
except ModuleNotFoundError:
    from datastore import DataStore


class CommandHandler:
    """Dispatches and executes Redis commands against the DataStore."""

    def __init__(self, datastore: DataStore) -> None:
        self.db = datastore
        self._commands: Dict[str, Callable[[List[str]], Any]] = {
            "PING": self._cmd_ping,
            "ECHO": self._cmd_echo,
            "SET": self._cmd_set,
            "GET": self._cmd_get,
            "DEL": self._cmd_del,
            "EXISTS": self._cmd_exists,
            "EXPIRE": self._cmd_expire,
            "TTL": self._cmd_ttl,
            "INCR": self._cmd_incr,
            "DECR": self._cmd_decr,
            "LPUSH": self._cmd_lpush,
            "RPUSH": self._cmd_rpush,
            "LRANGE": self._cmd_lrange,
            "SADD": self._cmd_sadd,
            "SMEMBERS": self._cmd_smembers,
            "HSET": self._cmd_hset,
            "HGET": self._cmd_hget,
            "HDEL": self._cmd_hdel,
            "HEXISTS": self._cmd_hexists,
            "HGETALL": self._cmd_hgetall,
            "BGREWRITEAOF": self._cmd_bgrewriteaof,
            "KEYS": self._cmd_keys,
            "FLUSHALL": self._cmd_flushall,
        }

    def execute(self, parts: List[str]) -> Any:
        """Executes a command represented by a list of strings."""
        if not parts:
            return Exception("ERR empty command")

        cmd_name = str(parts[0]).upper()
        args = parts[1:]

        handler = self._commands.get(cmd_name)
        if not handler:
            return Exception(f"unknown command `{cmd_name}`")

        try:
            return handler(args)
        except (ValueError, TypeError) as exc:
            return exc
        except Exception as exc:
            return Exception(f"ERR {str(exc)}")

    def _cmd_ping(self, args: List[str]) -> str:
        if not args:
            return "PONG"
        return args[0]

    def _cmd_echo(self, args: List[str]) -> str:
        if len(args) != 1:
            raise ValueError("wrong number of arguments for 'echo' command")
        return args[0]

    def _cmd_set(self, args: List[str]) -> str:
        if len(args) < 2:
            raise ValueError("wrong number of arguments for 'set' command")

        key = args[0]
        value = args[1]
        expire_seconds = None

        idx = 2
        while idx < len(args):
            opt = args[idx].upper()
            if opt == "EX" and idx + 1 < len(args):
                expire_seconds = float(args[idx + 1])
                idx = idx + 2
            elif opt == "PX" and idx + 1 < len(args):
                expire_seconds = float(args[idx + 1]) / 1000.0
                idx = idx + 2
            else:
                raise ValueError("syntax error")

        self.db.set(key, value, expire_seconds)
        return "OK"

    def _cmd_get(self, args: List[str]) -> Any:
        if len(args) != 1:
            raise ValueError("wrong number of arguments for 'get' command")
        return self.db.get(args[0])

    def _cmd_del(self, args: List[str]) -> int:
        if not args:
            raise ValueError("wrong number of arguments for 'del' command")
        return self.db.delete(*args)

    def _cmd_exists(self, args: List[str]) -> int:
        if not args:
            raise ValueError("wrong number of arguments for 'exists' command")
        return self.db.exists(*args)

    def _cmd_expire(self, args: List[str]) -> int:
        if len(args) != 2:
            raise ValueError("wrong number of arguments for 'expire' command")
        seconds = float(args[1])
        return self.db.expire(args[0], seconds)

    def _cmd_ttl(self, args: List[str]) -> int:
        if len(args) != 1:
            raise ValueError("wrong number of arguments for 'ttl' command")
        return self.db.ttl(args[0])

    def _cmd_incr(self, args: List[str]) -> int:
        if len(args) != 1:
            raise ValueError("wrong number of arguments for 'incr' command")
        return self.db.incr(args[0], delta=1)

    def _cmd_decr(self, args: List[str]) -> int:
        if len(args) != 1:
            raise ValueError("wrong number of arguments for 'decr' command")
        return self.db.incr(args[0], delta=-1)

    def _cmd_lpush(self, args: List[str]) -> int:
        if len(args) < 2:
            raise ValueError("wrong number of arguments for 'lpush' command")
        return self.db.lpush(args[0], *args[1:])

    def _cmd_rpush(self, args: List[str]) -> int:
        if len(args) < 2:
            raise ValueError("wrong number of arguments for 'rpush' command")
        return self.db.rpush(args[0], *args[1:])

    def _cmd_lrange(self, args: List[str]) -> List[Any]:
        if len(args) != 3:
            raise ValueError("wrong number of arguments for 'lrange' command")
        start = int(args[1])
        stop = int(args[2])
        return self.db.lrange(args[0], start, stop)

    def _cmd_sadd(self, args: List[str]) -> int:
        if len(args) < 2:
            raise ValueError("wrong number of arguments for 'sadd' command")
        return self.db.sadd(args[0], *args[1:])

    def _cmd_smembers(self, args: List[str]) -> List[Any]:
        if len(args) != 1:
            raise ValueError("wrong number of arguments for 'smembers' command")
        return self.db.smembers(args[0])

    def _cmd_hset(self, args: List[str]) -> int:
        if len(args) < 3:
            raise ValueError("wrong number of arguments for 'hset' command")
        key = args[0]
        field_values = args[1:]
        if len(field_values) % 2 != 0:
            raise ValueError("wrong number of arguments for 'hset' command")
        return self.db.hset(key, *field_values)

    def _cmd_hget(self, args: List[str]) -> Any:
        if len(args) != 2:
            raise ValueError("wrong number of arguments for 'hget' command")
        key = args[0]
        field = args[1]
        return self.db.hget(key, field)

    def _cmd_hdel(self, args: List[str]) -> int:
        if len(args) < 2:
            raise ValueError("wrong number of arguments for 'hdel' command")
        key = args[0]
        fields = args[1:]
        return self.db.hdel(key, *fields)

    def _cmd_hexists(self, args: List[str]) -> int:
        if len(args) != 2:
            raise ValueError("wrong number of arguments for 'hexists' command")
        key = args[0]
        field = args[1]
        return self.db.hexists(key, field)

    def _cmd_hgetall(self, args: List[str]) -> List[str]:
        if len(args) != 1:
            raise ValueError("wrong number of arguments for 'hgetall' command")
        key = args[0]
        return self.db.hgetall(key)

    def _cmd_bgrewriteaof(self, args: List[str]) -> str:
        success = self.db.rewrite_aof()
        if not success:
            raise Exception("ERR AOF rewrite failed or AOF is disabled")
        return "Background append only file rewriting started"

    def _cmd_keys(self, args: List[str]) -> List[str]:
        return self.db.keys()

    def _cmd_flushall(self, args: List[str]) -> str:
        self.db.flushall()
        return "OK"