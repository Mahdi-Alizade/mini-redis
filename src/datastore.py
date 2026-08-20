"""In-memory Key-Value store with TTL and expiration mechanisms."""

import time
from typing import Any, Dict, List, Optional, Set


class DataStore:
    """Core in-memory storage supporting string values, lists, sets, and key expiration."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}

    def is_expired(self, key: str) -> bool:
        """Checks if a key is expired. If expired, deletes it lazily."""
        if key not in self._expires:
            return False

        if time.time() >= self._expires[key]:
            self.delete(key)
            return True
        return False

    def get(self, key: str) -> Optional[Any]:
        """Retrieves value if key exists and has not expired."""
        if self.is_expired(key):
            return None
        return self._data.get(key)

    def set(self, key: str, value: Any, expire_seconds: Optional[float] = None) -> bool:
        """Sets key to value with an optional TTL in seconds."""
        self._data[key] = value
        if expire_seconds is not None:
            self._expires[key] = time.time() + expire_seconds
        elif key in self._expires:
            del self._expires[key]
        return True

    def delete(self, *keys: str) -> int:
        """Deletes one or more keys. Returns number of keys removed."""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
            if key in self._expires:
                del self._expires[key]
        return count

    def exists(self, *keys: str) -> int:
        """Counts how many of the specified keys exist."""
        count = 0
        for key in keys:
            if not self.is_expired(key) and key in self._data:
                count += 1
        return count

    def expire(self, key: str, seconds: float) -> int:
        """Sets a timeout on key in seconds. Returns 1 on success, 0 if key not found."""
        if self.is_expired(key) or key not in self._data:
            return 0
        self._expires[key] = time.time() + seconds
        return 1

    def ttl(self, key: str) -> int:
        """
        Returns TTL in seconds:
        - -2 if key does not exist or expired
        - -1 if key exists but has no associated expire
        - remaining seconds otherwise
        """
        if self.is_expired(key) or key not in self._data:
            return -2
        if key not in self._expires:
            return -1
        remaining = int(self._expires[key] - time.time())
        return max(0, remaining)

    def incr(self, key: str, delta: int = 1) -> int:
        """Increments integer value of a key by delta."""
        if self.is_expired(key):
            self.delete(key)

        val = self._data.get(key, 0)
        try:
            int_val = int(val)
        except (ValueError, TypeError):
            raise ValueError("ERR value is not an integer or out of range")

        new_val = int_val + delta
        self._data[key] = str(new_val)
        return new_val

    # List Operations
    def lpush(self, key: str, *values: Any) -> int:
        """Prepends one or multiple values to a list."""
        if self.is_expired(key):
            self.delete(key)

        lst = self._data.setdefault(key, [])
        if not isinstance(lst, list):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        for val in values:
            lst.insert(0, val)
        return len(lst)

    def rpush(self, key: str, *values: Any) -> int:
        """Appends one or multiple values to a list."""
        if self.is_expired(key):
            self.delete(key)

        lst = self._data.setdefault(key, [])
        if not isinstance(lst, list):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        lst.extend(values)
        return len(lst)

    def lrange(self, key: str, start: int, stop: int) -> List[Any]:
        """Returns range of elements from a list."""
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
    def sadd(self, key: str, *members: Any) -> int:
        """Adds one or more members to a set."""
        if self.is_expired(key):
            self.delete(key)

        s = self._data.setdefault(key, set())
        if not isinstance(s, set):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        initial_len = len(s)
        s.update(members)
        return len(s) - initial_len

    def smembers(self, key: str) -> List[Any]:
        """Returns all the members of the set value stored at key."""
        if self.is_expired(key):
            return []

        s = self._data.get(key)
        if s is None:
            return []
        if not isinstance(s, set):
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return list(s)

    def keys(self) -> List[str]:
        """Returns all non-expired keys in the store."""
        active_keys = []
        for key in list(self._data.keys()):
            if not self.is_expired(key):
                active_keys.append(key)
        return active_keys

    def flushall(self) -> None:
        """Removes all keys from the database."""
        self._data.clear()
        self._expires.clear()