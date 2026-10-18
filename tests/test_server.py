"""Automated unit and integration test suite for Mini-Redis."""

import os
import sys
import time
import socket
import asyncio
import tempfile
import threading
import pytest

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.protocol import RESPParser, ProtocolError
from src.datastore import DataStore
from src.commands import CommandHandler
from src.aof import AOFManager
from src.server import RedisServer


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

    def test_hash_operations(self):
        added = self.store.hset("user:1", "name", "Mahdi", "age", "20")
        assert added == 2
        assert self.store.hget("user:1", "name") == "Mahdi"
        assert self.store.hget("user:1", "age") == "20"
        assert self.store.hget("user:1", "city") is None

        updated = self.store.hset("user:1", "age", "21")
        assert updated == 0
        assert self.store.hget("user:1", "age") == "21"

        assert self.store.hexists("user:1", "name") == 1
        assert self.store.hexists("user:1", "city") == 0

        removed = self.store.hdel("user:1", "age", "nonexistent")
        assert removed == 1
        assert self.store.hexists("user:1", "age") == 0

        all_entries = self.store.hgetall("user:1")
        assert all_entries == ["name", "Mahdi"]


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

    def test_hash_commands_flow(self):
        resp = self.handler.execute(["HSET", "profile", "job", "developer", "city", "Tehran"])
        assert resp == 2

        assert self.handler.execute(["HGET", "profile", "job"]) == "developer"
        assert self.handler.execute(["HGET", "profile", "salary"]) is None

        assert self.handler.execute(["HEXISTS", "profile", "city"]) == 1
        assert self.handler.execute(["HEXISTS", "profile", "country"]) == 0

        all_vals = self.handler.execute(["HGETALL", "profile"])
        assert "job" in all_vals
        assert "developer" in all_vals
        assert "city" in all_vals
        assert "Tehran" in all_vals

        del_count = self.handler.execute(["HDEL", "profile", "job"])
        assert del_count == 1
        assert self.handler.execute(["HGET", "profile", "job"]) is None

    def test_bgrewriteaof_command(self):
        temp_dir = tempfile.TemporaryDirectory()
        aof_path = os.path.join(temp_dir.name, "bgrewrite_cmd.aof")
        aof = AOFManager(filename=aof_path)
        store = DataStore(aof_manager=aof)
        handler = CommandHandler(store)

        resp = handler.execute(["BGREWRITEAOF"])
        assert "Background append only file rewriting started" in resp

        aof.close()
        temp_dir.cleanup()

    def test_unknown_command(self):
        resp = self.handler.execute(["FOOBAR"])
        assert isinstance(resp, Exception)
        assert "unknown command" in str(resp)


class TestAOFPersistence:
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.aof_file_path = os.path.join(self.temp_dir.name, "test_appendonly.aof")

    def teardown_method(self):
        self.temp_dir.cleanup()

    def test_aof_write_and_recovery(self):
        aof = AOFManager(filename=self.aof_file_path)
        store = DataStore(aof_manager=aof)

        store.set("server_name", "mini-redis-core")
        store.incr("visit_count", 5)
        store.lpush("jobs", "email", "sms")
        store.sadd("roles", "admin", "editor")
        store.hset("config", "timeout", "30", "debug", "true")

        aof.close()

        new_aof = AOFManager(filename=self.aof_file_path)
        recovered_store = DataStore(aof_manager=new_aof)

        assert recovered_store.get("server_name") == "mini-redis-core"
        assert recovered_store.get("visit_count") == "5"
        assert recovered_store.lrange("jobs", 0, -1) == ["sms", "email"]
        assert sorted(recovered_store.smembers("roles")) == ["admin", "editor"]
        assert recovered_store.hget("config", "timeout") == "30"
        assert recovered_store.hget("config", "debug") == "true"

        new_aof.close()

    def test_aof_delete_state_recovery(self):
        aof = AOFManager(filename=self.aof_file_path)
        store = DataStore(aof_manager=aof)

        store.set("temp_key", "data")
        store.delete("temp_key")
        store.hset("hdata", "f1", "v1")
        store.hdel("hdata", "f1")

        aof.close()

        new_aof = AOFManager(filename=self.aof_file_path)
        recovered_store = DataStore(aof_manager=new_aof)

        assert recovered_store.get("temp_key") is None
        assert recovered_store.hget("hdata", "f1") is None
        new_aof.close()

    def test_aof_rewrite_compaction_and_data_integrity(self):
        aof = AOFManager(filename=self.aof_file_path)
        store = DataStore(aof_manager=aof)

        # Generate a bloated history of writes
        for i in range(50):
            store.set("counter_key", str(i))
            store.set("transient_key", "will_be_deleted")
            store.delete("transient_key")

        store.hset("active_profile", "status", "online")
        store.rpush("log_queue", "event1", "event2")

        initial_size = os.path.getsize(self.aof_file_path)

        # Trigger rewrite
        rewrite_success = store.rewrite_aof()
        assert rewrite_success is True

        compacted_size = os.path.getsize(self.aof_file_path)

        # Compacted file should be substantially smaller
        assert compacted_size < initial_size

        aof.close()

        # Verify state restoration from compacted file
        fresh_aof = AOFManager(filename=self.aof_file_path)
        recovered = DataStore(aof_manager=fresh_aof)

        assert recovered.get("counter_key") == "49"
        assert recovered.get("transient_key") is None
        assert recovered.hget("active_profile", "status") == "online"
        assert recovered.lrange("log_queue", 0, -1) == ["event1", "event2"]

        fresh_aof.close()


class TestAuthentication:
    @classmethod
    def setup_class(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.aof_file = os.path.join(cls.temp_dir.name, "auth_test.aof")
        cls.test_port = 6389
        cls.test_password = "supersecretpass"
        cls.server = RedisServer(
            host="127.0.0.1",
            port=cls.test_port,
            aof_file=cls.aof_file,
            password=cls.test_password,
        )

        def run_srv():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cls.server.start())

        cls.thread = threading.Thread(target=run_srv, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def teardown_class(cls):
        cls.server.stop()
        cls.temp_dir.cleanup()

    def _send_cmd(self, sock, parts):
        payload = RESPParser.serialize(parts)
        sock.sendall(payload)
        resp_data = sock.recv(4096)
        parsed, _ = RESPParser.parse_one(resp_data)
        return parsed

    def test_auth_enforcement_flow(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", self.test_port))

        res_noauth = self._send_cmd(s, ["SET", "k1", "v1"])
        assert isinstance(res_noauth, Exception)
        assert "NOAUTH" in str(res_noauth)

        res_wrong = self._send_cmd(s, ["AUTH", "wrongpass"])
        assert isinstance(res_wrong, Exception)
        assert "invalid password" in str(res_wrong)

        res_ok = self._send_cmd(s, ["AUTH", self.test_password])
        assert res_ok == "OK"

        res_set = self._send_cmd(s, ["SET", "k1", "v1"])
        assert res_set == "OK"

        res_get = self._send_cmd(s, ["GET", "k1"])
        assert res_get == "v1"

        s.close()