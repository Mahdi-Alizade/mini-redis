"""Automated unit and integration test suite for Mini-Redis."""

import os
import sys
import time
import pytest

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.protocol import RESPParser, ProtocolError
from src.datastore import DataStore
from src.commands import CommandHandler


class TestRESPParser:
    def test_simple_string(self):
        assert RESPParser.serialize_simple_string("PONG") == b"+PONG\r\n"
        val, consumed = RESPParser.parse_one(b"+OK\r\n")
        assert val == "OK"
        assert consumed == 5

    def test_integer(self):
        assert RESPParser.serialize_integer(42) == b":42\r\n"
        val, consumed = RESPParser.parse_one(b":100\r\n")
        assert val == 100
        assert consumed == 6

    def test_bulk_string(self):
        assert RESPParser.serialize_bulk_string("hello") == b"$5\r\nhello\r\n"
        assert RESPParser.serialize_bulk_string(None) == b"$-1\r\n"
        val, consumed = RESPParser.parse_one(b"$4\r\nPING\r\n")
        assert val == "PING"
        assert consumed == 10

    def test_array(self):
        encoded = RESPParser.serialize_array(["SET", "key", "val"])
        assert encoded == b"*3\r\n$3\r\nSET\r\n$3\r\nkey\r\n$3\r\nval\r\n"
        val, consumed = RESPParser.parse_one(encoded)
        assert val == ["SET", "key", "val"]
        assert consumed == len(encoded)

    def test_partial_buffer(self):
        val, consumed = RESPParser.parse_one(b"*2\r\n$3\r\nGET\r\n")
        assert val is None
        assert consumed == 0


class TestDataStore:
    def setup_method(self):
        self.store = DataStore()

    def test_set_and_get(self):
        self.store.set("foo", "bar")
        assert self.store.get("foo") == "bar"
        assert self.store.get("nonexistent") is None

    def test_ttl_and_expiration(self):
        self.store.set("ephemeral", "value", expire_seconds=0.1)
        assert self.store.get("ephemeral") == "value"
        assert self.store.ttl("ephemeral") >= 0
        time.sleep(0.15)
        assert self.store.get("ephemeral") is None
        assert self.store.ttl("ephemeral") == -2

    def test_incr_decr(self):
        assert self.store.incr("counter", 1) == 1
        assert self.store.incr("counter", 5) == 6
        assert self.store.incr("counter", -2) == 4

    def test_list_operations(self):
        assert self.store.lpush("mylist", "b", "a") == 2
        assert self.store.rpush("mylist", "c") == 3
        assert self.store.lrange("mylist", 0, -1) == ["a", "b", "c"]
        assert self.store.lrange("mylist", 0, 1) == ["a", "b"]

    def test_set_operations(self):
        assert self.store.sadd("myset", "apple", "banana") == 2
        assert self.store.sadd("myset", "apple") == 0
        members = self.store.smembers("myset")
        assert sorted(members) == ["apple", "banana"]


class TestCommandHandler:
    def setup_method(self):
        self.handler = CommandHandler(DataStore())

    def test_ping(self):
        assert self.handler.execute(["PING"]) == "PONG"
        assert self.handler.execute(["PING", "custom"]) == "custom"

    def test_set_get_flow(self):
        assert self.handler.execute(["SET", "user", "Alice"]) == "OK"
        assert self.handler.execute(["GET", "user"]) == "Alice"
        assert self.handler.execute(["EXISTS", "user"]) == 1
        assert self.handler.execute(["DEL", "user"]) == 1
        assert self.handler.execute(["GET", "user"]) is None

    def test_unknown_command(self):
        resp = self.handler.execute(["FOOBAR"])
        assert isinstance(resp, Exception)
        assert "unknown command" in str(resp)