"""In-memory Key-Value store with TTL, expiration, and Hash support."""

import time
from typing import Any, Dict, List, Optional, Set


class DataStore:
    """Core in-memory storage supporting strings, lists, sets, hashes, and key expiration."""

    def __init__(self, aof_manager=None) -> None:
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        self.aof = aof_manager

        if self.aof is not None:
            self._restore_from_aof()

    def _restore_from_aof(self) -> None:
        if not self.aof:
            return

        past_commands = self.aof.load_commands()
        for cmd in past_commands:
            if not cmd or not isinstance(cmd, list):
                continue

            op = str(cmd[0]).upper()
            args = cmd[1:]

            if op == "SET" and len(args) >= 2:
                exp = None
                if len(args) >= 4 and args[2].upper() == "EX":
                    try:
                        exp = float(args[3])
                    except (ValueError, IndexError):
                        exp = None
                self._internal_set(args[0], args[1], exp)

            elif op == "DEL" and len(args) >= 1:
                self._internal_del(*args)

            elif op == "LPUSH" and len(args) >= 2:
                self.lpush(args[0], *args[1:], log_aof=False)

            elif op == "RPUSH" and len(args) >= 2:
                self.rpush(args[0], *args[1:], log_aof=False)

            elif op == "SADD" and len(args) >= 2:
                self.sadd(args[0], *args[1:], log_aof=False)

            elif op == "HSET" and len(args) >= 3:
                # Replay HSET into dictionary
                key = args[0]
                pairs = args[1:]
                field_val_list = []
                idx = 0
                while idx < len(pairs) - 1:
                    field_val_list.append((pairs[idx], pairs[idx + 1]))
                    idx = idx + 2
                self._internal_hset(key, field_val_list)

            elif op == "HDEL" and len(args) >= 2:
                self._internal_hdel(args[0], *args[1:])

            elif op == "FLUSHALL":
                self._data.clear()
                self._expires.clear()

    def is_expired(self, key: str) -> bool:
        if key not in self._expires:
            return False

        current_ts = time.time()
        expire_ts = self._expires[key]

        if current_ts >= expire_ts:
            self.delete(key)
            return True
        return False

    def get(self, key: str) -> Optional[Any]:
        if self.is_expired(key):
            return None
        return self._data.get(key)

    def _internal_set(self, key: str, value: Any, expire_seconds: Optional[float] = None) -> bool:
        self._data[key] = value
        if expire_seconds is not None:
            self._expires[key] = time.time() + expire_seconds
        elif key in self._expires:
            del self._expires[key]
        return True

    def set(self, key: str, value: Any, expire_seconds: Optional[float] = None) -> bool:
        res = self._internal_set(key, value, expire_seconds)
        if self.aof:
            cmd = ["SET", str(key), str(value)]
            if expire_seconds is not None:
                cmd.extend(["EX", str(expire_seconds)])
            self.aof.append_command(cmd)
        return res

    def _internal_del(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count = count + 1
            if key in self._expires:
                del self._expires[key]
        return count

    def delete(self, *keys: str) -> int:
        count = self._internal_del(*keys)
        if count > 0 and self.aof:
            self.aof.append_command(["DEL", *keys])
        return count

    def exists(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if not self.is_expired(key) and key in self._data:
                count = count + 1
        return count

    def expire(self, key: str, seconds: float) -> int:
        if self.is_expired(key) or key not in self._data:
            return 0
        self._expires[key] = time.time() + seconds
        if self.aof:
            self.aof.append_command(["EXPIRE", str(key), str(seconds)])
        return 1

    def ttl(self, key: str) -> int:
        if self.is_expired(key) or key not in self._data:
            return -2
        if key not in self._expires:
            return -1
        remaining = int(self._expires[key] - time.time())
        return max(0, remaining)

    def incr(self, key: str, delta: int = 1) -> int:
        if self.is_expired(key):
            self.delete(key)

        val = self._data.get(key, 0)
        try:
            int_val = int(val)
        except (ValueError, TypeError):
            raise ValueError("ERR value is not an integer or out of range")

        new_val = int_val + delta
        self._data[key] = str(new_val)

        if self.aof:
            self.aof.append_command(["SET", str(key), str(new_val)])

        return new_val

    # List Operations
    def lpush(self, key: str, *values: Any, log_aof: bool = True) -> int:
        if self.is_expired(key):
            self.delete(key)

        lst = self._data.setdefault(key, [])
        if not isinstance(lst, list):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        for val in values:
            lst.insert(0, val)

        if log_aof and self.aof:
            self.aof.append_command(["LPUSH", str(key), *[str(v) for v in values]])

        return len(lst)

    def rpush(self, key: str, *values: Any, log_aof: bool = True) -> int:
        if self.is_expired(key):
            self.delete(key)

        lst = self._data.setdefault(key, [])
        if not isinstance(lst, list):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        lst.extend(values)

        if log_aof and self.aof:
            self.aof.append_command(["RPUSH", str(key), *[str(v) for v in values]])

        return len(lst)

    def lrange(self, key: str, start: int, stop: int) -> List[Any]:
        if self.is_expired(key):
            return []

        lst = self._data.get(key)
        if lst is None:
            return []
        if not isinstance(lst, list):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        if stop == -1:
            return lst[start:]
        return lst[start : stop + 1]

    # Set Operations
    def sadd(self, key: str, *members: Any, log_aof: bool = True) -> int:
        if self.is_expired(key):
            self.delete(key)

        s = self._data.setdefault(key, set())
        if not isinstance(s, set):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        initial_len = len(s)
        s.update(members)
        added_count = len(s) - initial_len

        if log_aof and self.aof and added_count > 0:
            self.aof.append_command(["SADD", str(key), *[str(m) for m in members]])

        return added_count

    def smembers(self, key: str) -> List[Any]:
        if self.is_expired(key):
            return []

        s = self._data.get(key)
        if s is None:
            return []
        if not isinstance(s, set):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return list(s)

    # Hash Operations
    def _internal_hset(self, key: str, field_values: List[tuple]) -> int:
        hash_dict = self._data.setdefault(key, {})
        if not isinstance(hash_dict, dict):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        added_fields = 0
        for fld, val in field_values:
            if fld not in hash_dict:
                added_fields = added_fields + 1
            hash_dict[fld] = str(val)

        return added_fields

    def hset(self, key: str, *field_values: str) -> int:
        if self.is_expired(key):
            self.delete(key)

        if len(field_values) % 2 != 0:
            raise ValueError("ERR wrong number of arguments for 'hset' command")

        pairs = []
        i = 0
        while i < len(field_values):
            pairs.append((field_values[i], field_values[i + 1]))
            i = i + 2

        count = self._internal_hset(key, pairs)

        if self.aof:
            cmd = ["HSET", str(key)]
            for f, v in pairs:
                cmd.append(str(f))
                cmd.append(str(v))
            self.aof.append_command(cmd)

        return count

    def hget(self, key: str, field: str) -> Optional[str]:
        if self.is_expired(key):
            return None

        hash_dict = self._data.get(key)
        if hash_dict is None:
            return None

        if not isinstance(hash_dict, dict):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        return hash_dict.get(field)

    def _internal_hdel(self, key: str, *fields: str) -> int:
        hash_dict = self._data.get(key)
        if hash_dict is None:
            return 0

        if not isinstance(hash_dict, dict):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        removed = 0
        for f in fields:
            if f in hash_dict:
                del hash_dict[f]
                removed = removed + 1

        if len(hash_dict) == 0:
            del self._data[key]

        return removed

    def hdel(self, key: str, *fields: str) -> int:
        if self.is_expired(key):
            return 0

        removed = self._internal_hdel(key, *fields)

        if removed > 0 and self.aof:
            self.aof.append_command(["HDEL", str(key), *fields])

        return removed

    def hexists(self, key: str, field: str) -> int:
        if self.is_expired(key):
            return 0

        hash_dict = self._data.get(key)
        if hash_dict is None:
            return 0

        if not isinstance(hash_dict, dict):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        return 1 if field in hash_dict else 0

    def hgetall(self, key: str) -> List[str]:
        if self.is_expired(key):
            return []

        hash_dict = self._data.get(key)
        if hash_dict is None:
            return []

        if not isinstance(hash_dict, dict):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        result_list = []
        for f, v in hash_dict.items():
            result_list.append(str(f))
            result_list.append(str(v))

        return result_list

    def keys(self) -> List[str]:
        active_keys = []
        for key in list(self._data.keys()):
            if not self.is_expired(key):
                active_keys.append(key)
        return active_keys

    def flushall(self) -> None:
        self._data.clear()
        self._expires.clear()
        if self.aof:
            self.aof.append_command(["FLUSHALL"])